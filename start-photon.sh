#!/bin/bash

# Source modules
source "src/logging.sh"
source "src/config.sh"
source "src/process.sh"

# Log environment variables
log_info "Environment variables:"
log_info "UPDATE_STRATEGY=$UPDATE_STRATEGY"
log_info "UPDATE_INTERVAL=$UPDATE_INTERVAL"
log_info "LOG_LEVEL=$LOG_LEVEL"
log_info "BASE_URL=$BASE_URL"
log_info "FORCE_UPDATE=$FORCE_UPDATE"
log_info "SKIP_MD5_CHECK=$SKIP_MD5_CHECK"
log_info "COUNTRY_CODE=${COUNTRY_CODE:-not set}"

ES_UID="${ES_UID:-1000}"
ES_GID="${ES_GID:-1000}"

# Define DATA_DIR from config
DATA_DIR="$PHOTON_DIR"

# Error handling
set -euo pipefail
trap 'handle_error $? $LINENO "$BASH_COMMAND" $(printf "::%s" ${FUNCNAME[@]:-})' ERR


handle_error() {
    local exit_code=$1
    local line_no=$2
    local last_command=$4
    local func_trace=$5
    log_error "Error $exit_code occurred on line $line_no: $last_command"
    log_error "Function trace: $func_trace"
    cleanup_and_exit
}

# Cleanup function
cleanup_and_exit() {
    log_info "Cleaning up temporary files..."
    
    # Stop service if running
    stop_photon
    
    # Remove temporary files
    if [ -d "$TEMP_DIR" ]; then
        if ! rm -rf "${TEMP_DIR:?}"/*; then
            log_error "Failed to clean up temporary directory"
        fi
    fi
    
    # Remove PID file if it exists
    rm -f /photon/photon.pid
    
    exit 1
}

# Check available disk space against remote file size
check_disk_space() {
    local url=$1
    local available
    local full_url="${url}.tar.bz2"

    log_debug "Checking disk space for URL: $full_url"
    log_debug "URL components - Protocol: ${full_url%%://*}, Host: ${full_url#*://}, Path: ${full_url#*://*/}"
    
    # Get remote file size using wget spider
    log_debug "Executing wget spider command: wget --spider --server-response \"$full_url\""
    local wget_output
    wget_output=$(wget --spider --server-response "$full_url" 2>&1)
    local wget_status=$?
    log_debug "wget spider command output: $(echo "$wget_output" | head -20)"
    
    local remote_size
    if ! remote_size=$(echo "$wget_output" | grep "Content-Length" | awk '{print $2}' | tail -1); then
        log_error "Failed to execute wget spider command"
        log_debug "wget spider command failed with status: $wget_status"
        log_debug "Full wget output: $wget_output"
        return 1
    fi
    
    if [ -z "$remote_size" ]; then
        log_error "Failed to get remote file size"
        log_debug "No Content-Length found in wget output"
        return 1
    fi
    
    log_debug "Remote file size detected: $remote_size bytes"
    
    # Check available space in photon_data directory
    log_debug "Creating data directory structure at $DATA_DIR/photon_data"
    mkdir -p "$DATA_DIR/photon_data"
    log_debug "Directory created. Contents: $(ls -l $DATA_DIR/photon_data 2>/dev/null || echo '<none>')"
    available=$(df -B1 "$DATA_DIR/photon_data" | awk 'NR==2 {print $4}')
    log_debug "Available disk space: $available bytes"
    
    if [ "$available" -lt "$remote_size" ]; then
        log_error "Insufficient disk space. Required: ${remote_size}B , Available: ${available}B"
        return 1
    fi
    
    log_info "Sufficient disk space available. Required: ${remote_size}B, Available: ${available}B"
}

# Verify directory structure and index
verify_structure() {
    local dir=$1
    log_debug "Verifying directory structure at: $dir/photon_data"
    if [ ! -d "$dir/photon_data/node_1" ]; then
        log_error "Directory structure failed verification. Existing paths: $(find "$dir" -maxdepth 3 -type d | tr '\n' ' ')"
        log_error "Invalid structure: missing index directory"
        return 1
    fi
    
    
    return 0
}

set_permissions() {

    local dir=$1
    log_info "Ensuring correct ownership and permissions for $dir"
    log_debug "Current state for $dir: $(stat -c 'Perms: %a, Owner: %U (%u), Group: %G (%g), Name: %n' "$dir" 2>/dev/null || echo "Path $dir not found or stat error")"

    # Change ownership
    # The -R flag makes it recursive.
    if ! chown -R "$ES_UID:$ES_GID" "$dir"; then
        log_info "WARNING: Failed to chown $dir to $ES_UID:$ES_GID. This might be due to host volume restrictions. Opensearch may encounter permission issues if not run as root or if host permissions are incorrect."
    else
        log_debug "Successfully changed ownership of $dir to $ES_UID:$ES_GID."
    fi

    # Change permissions
    # 755 means: Owner (opensearch user): Read, Write, Execute (rwx)
    #            Group (opensearch group): Read, Execute (r-x)
    #            Others: Read, Execute (r-x)
    
    if ! chmod -R 755 "$dir"; then
        log_info "WARNING: Failed to chmod $dir to 755. This might be due to host volume restrictions."
    else
        log_debug "Successfully changed permissions of $dir to 755."
    fi

    log_info "Post-permission state for $dir: $(stat -c 'Perms: %a, Owner: %U (%u), Group: %G (%g), Name: %n' "$dir" 2>/dev/null || echo "Path $dir not found or stat error after changes")"
}


# Check if remote index is newer than local
check_remote_index() {
    local url=$1
    local full_url="${url}.tar.bz2"

    log_debug "Checking if remote index is newer than local"
    log_debug "Remote URL: $full_url"

    # If FORCE_UPDATE is TRUE, skip timestamp check
    if [ "${FORCE_UPDATE}" = "TRUE" ]; then
        log_info "Force update requested, skipping timestamp check"
        return 0
    fi

    local remote_time
    local wget_output

    # Get remote file timestamp using HEAD request
    log_debug "Executing: wget --spider -S \"$full_url\""
    if ! wget_output=$(wget --spider -S "$full_url" 2>&1); then
        log_error "Failed to check remote index timestamp"
        log_debug "Full wget output:\n$wget_output"
        return 2
    fi
    
    log_debug "Full wget spider response:\n$wget_output"
    
    remote_time=$(echo "$wget_output" | grep -i "Last-Modified:" | cut -d' ' -f4-)
    if [ -z "$remote_time" ]; then
        log_error "Failed to get remote index timestamp"
        log_debug "No Last-Modified header found in wget output"
        return 2
    fi
    
    log_debug "Remote timestamp: $remote_time"
    
    # Convert remote time to epoch
    remote_epoch=$(date -d "$remote_time" +%s 2>/dev/null)
    
    # Get local index timestamp if it exists
    if [ -d "$INDEX_DIR" ]; then
        local_epoch=$(stat -c %Y "$INDEX_DIR" 2>/dev/null)
        
        log_debug "Remote index timestamp: $remote_time (${remote_epoch})"
        log_debug "Local index timestamp: $(date -d "@$local_epoch" 2>/dev/null) (${local_epoch})"
        
        # Compare timestamps with 1 day tolerance
        local time_diff=$((remote_epoch - local_epoch))
        if [ "${time_diff#-}" -lt 86400 ]; then
            log_info "Local index is up to date (within 1 day tolerance)"
            return 1
        elif [ "$remote_epoch" -gt "$local_epoch" ]; then
            log_info "Remote index is newer than local index"
            return 0
        else
            log_info "Local index is up to date"
            return 1
        fi
    else
        log_info "No local index found"
        return 0
    fi
}

# Core utility functions
download_file() {
    local url=$1
    local output_file=$2
    
    log_info "Downloading from $url"
    if ! wget --progress=bar:force:noscroll:giga -O "$output_file" "$url"; then
        log_error "Failed to download file from $url"
        return 1
    fi
    log_info "Index file downloaded successfully"
    return 0
}

verify_checksum() {
    local file=$1
    local md5_file=$2
    local dir
    dir=$(dirname "$file")
    
    log_info "Verifying MD5 checksum"
    if ! (cd "$dir" && md5sum -c <(cut -d' ' -f1 "$(basename "$md5_file")" > temp.md5 && echo "$(cat temp.md5)  $(basename "$file")" && rm temp.md5)); then
        log_error "MD5 verification failed"
        return 1
    fi
    log_info "Checksum verification successful"
    return 0
}

extract_archive() {
    local archive=$1
    local extract_dir=$2
    
    log_debug "Creating extraction directory $extract_dir"
    mkdir -p "$extract_dir"
    
    log_info "Extracting $archive to $extract_dir"
    if ! pbzip2 -dc "$archive" | tar x -C "$extract_dir"; then
        log_error "Failed to extract files"
        return 1
    fi
    log_info: "Extraction completed successfully"
    return 0
}

stop_photon() {
    if [ -f /photon/photon.pid ]; then
        local pid
        pid=$(cat /photon/photon.pid)
        
        if ps -p "$pid" > /dev/null; then
            log_info "Stopping Photon service (PID: $pid)"
            if ! kill -15 "$pid"; then
                log_error "Failed to stop Photon service gracefully, attempting force kill"
                kill -9 "$pid" || true
            fi
            
            # Wait for process to stop
            local count=0
            while ps -p "$pid" > /dev/null && [ $count -lt 10 ]; do
                sleep 1
                ((count++))
            done
            
            if ps -p "$pid" > /dev/null; then
                log_error "Failed to stop Photon service"
                return 1
            fi
        else
            log_info "Photon service not running"
        fi
        rm -f /photon/photon.pid
    fi
    return 0
}

move_index() {
    local source_dir=$1
    local target_dir=$2
    
    # Find opensearch directory recursively
    log_info "Searching for opensearch directory in: $source_dir"
    local es_dir
    es_dir=$(find "$source_dir" -type d -name "node_1" | head -n 1)
    log_info "Found opensearch candidates: $(find "$source_dir" -type d -name "node_1" | tr '\n' ' ')"
    
    if [ -n "$es_dir" ]; then
        log_info "Found opensearch directory at $es_dir"
        log_debug "Moving opensearch from $es_dir to $target_dir"
        log_info "Current target directory state: $(ls -ld "$target_dir" 2>/dev/null || echo '<not exists>')"
        mkdir -p "$(dirname "$target_dir")"
        log_info "Parent directory prepared. New state: $(ls -ld "$(dirname "$target_dir")" 2>/dev/null || echo '<not exists>')"
        log_info "Executing mv command: mv $es_dir $target_dir"
        mv -v "$es_dir" "$target_dir" | while read -r line; do log_debug "mv: $line"; done
        log_debug "Move completed. Target directory now contains: $(ls -l "$target_dir" | wc -l) items"
        return 0
    else
        log_error "Could not find opensearch directory in extracted files"
        return 1
    fi
}

cleanup_temp() {
    log_info "Cleaning up temporary directory"
    log_debug "Pre-cleanup temporary directory contents: $(tree -a $TEMP_DIR 2>/dev/null || echo '<empty>')"
    log_debug "Executing: rm -rf ${TEMP_DIR:?}"
    rm -rfv "${TEMP_DIR:?}" | while read -r line; do log_debug "rm: $line"; done
    log_info "Final photon_data directory structure:\n$(tree -L 2 $PHOTON_DATA_DIR 2>/dev/null || echo '<empty>')"
}

cleanup_stale_es() {
    # Remove old elasticsearch index 
    if [ -d "$ES_DATA_DIR" ]; then
        log_info "Removing old elasticsearch directory at $ES_DATA_DIR"
        log_debug "Executing: rm -rf $ES_DATA_DIR"
        if ! rm -rf "$ES_DATA_DIR"; then
            log_error "Failed to remove old elasticsearch index"
        fi
    fi
}

# Prepare download URL based on country code or custom base URL
prepare_download_url() {
    # Ensure BASE_URL doesn't have trailing slash
    local base_url="${BASE_URL%/}"
    local result_url
    
    if [[ -n "${COUNTRY_CODE:-}" ]]; then
        result_url="${base_url}/extracts/by-country-code/${COUNTRY_CODE}/photon-db-${COUNTRY_CODE}-latest"
    else
        result_url="${base_url}/photon-db-latest"
    fi
    
    echo "$result_url"
}

# Download and verify index
download_index() {
    local url
    url=$(prepare_download_url)
    log_debug "Download URL: $url"
    log_debug "Full tar.bz2 URL: ${url}.tar.bz2"
    log_debug "Full MD5 URL: ${url}.tar.bz2.md5"
    
    mkdir -p "$TEMP_DIR"
    log_debug "Created temp directory: $TEMP_DIR"
    
    # Check disk space before downloading
    log_debug "Checking disk space for download"
    if ! check_disk_space "$url"; then
        log_error "Disk space check failed"
        cleanup_temp
        return 1
    fi
    
    # Download files
    local download_url="${url}.tar.bz2"
    log_info "Downloading index from ${download_url}"
    log_debug "Executing: wget --progress=bar:force:noscroll:giga -O \"$TEMP_DIR/photon-db.tar.bz2\" \"${download_url}\""
    
    if ! wget --progress=bar:force:noscroll:giga -O "$TEMP_DIR/photon-db.tar.bz2" "${download_url}" 2>&1; then
        log_error "Failed to download index file from ${download_url}"
        cleanup_temp
        return 1
    fi
    
    log_debug "Index download successful. File size: $(du -h "$TEMP_DIR/photon-db.tar.bz2" | awk '{print $1}')"
    
    if [ "${SKIP_MD5_CHECK}" != "TRUE" ]; then
        log_debug "Downloading MD5 from ${url}.tar.bz2.md5"
        log_debug "Executing: wget -O \"$TEMP_DIR/photon-db.md5\" \"${url}.tar.bz2.md5\""
        
        local md5_output
        md5_output=$(wget -O "$TEMP_DIR/photon-db.md5" "${url}.tar.bz2.md5" 2>&1)
        local md5_status=$?
        
        if [ $md5_status -ne 0 ]; then
            log_error "Failed to download MD5 file from ${url}.tar.bz2.md5"
            log_debug "wget exit status: $md5_status"
            log_debug "wget output: $(echo "$md5_output" | head -20)"
            cleanup_temp
            return 1
        fi
        
        log_debug "MD5 download successful. MD5 content: $(cat "$TEMP_DIR/photon-db.md5" | head -1)"
        
        # Verify checksum
        log_debug "Starting MD5 verification"
        if ! (cd "$TEMP_DIR" && md5sum -c <(awk '{print $1"  photon-db.tar.bz2"}' photon-db.md5)); then
            log_error "MD5 verification failed"
            cleanup_temp
            return 1
        fi
        log_info "MD5 verification successful"
        log_debug "MD5 verification completed"
    
        # Extract archive
        log_info "Extracting archive, this may take some time..."
    else
        log_info "Skipping MD5 verification as requested"
    fi
    
    log_info "Extracting archive to $TEMP_DIR"
    # Extract archive in place
    if ! pbzip2 -dc "$TEMP_DIR/photon-db.tar.bz2" | tar x -C "$TEMP_DIR"; then
        log_error "Failed to extract files"
        cleanup_temp
        return 1
    fi
    
    log_info "Extraction completed successfully"
    return 0
}

# Strategy-specific update functions
parallel_update() {
    log_info "Starting parallel update process"
    
    # Download and prepare new index while current one is running
    log_debug "Downloading new index while current service is running"
    if ! download_index; then
        log_error "Failed to download index"
        return 1
    fi
    
    # Verify the downloaded index
    log_info "Verifying downloaded index structure"
    if ! verify_structure "$TEMP_DIR"; then
        log_error "Downloaded index verification failed"
        cleanup_temp
        return 1
    fi

    
    # Stop service and swap indexes
    log_info "Stopping Photon service before swapping indexes"
    if ! stop_photon; then
        log_error "Failed to stop Photon service cleanly"
        cleanup_temp
        return 1
    fi
    
    # Wait a moment for process to fully stop
    sleep 5
    
    # Backup and swap
    if [ -d "$INDEX_DIR" ]; then
        log_debug "Backing up current index to $INDEX_DIR.old"
        if ! mv "$INDEX_DIR" "$INDEX_DIR.old"; then
            log_error "Failed to backup current index"
            cleanup_temp
            return 1
        fi
    fi
    
    log_debug "Moving new index from $TEMP_DIR to $INDEX_DIR"
    if ! move_index "$TEMP_DIR" "$INDEX_DIR"; then
        log_error "Failed to move index, attempting to restore backup"
        if [ -d "$INDEX_DIR.old" ]; then
            if ! mv "$INDEX_DIR.old" "$INDEX_DIR"; then
                log_error "Failed to restore backup index"
            fi
        fi
        cleanup_temp
        return 1
    fi
    
    set_permissions "$INDEX_DIR" # Set permissions on the final index directory

    # Clean up
    log_debug "Removing old index backup"


    rm -rf "$INDEX_DIR.old" 2>/dev/null || true


    cleanup_stale_es

    log_info "Parallel update completed successfully"

    cleanup_temp
    return 0
}

sequential_update() {
    log_info "Starting sequential update process"
    
    log_info "Stopping Photon service before update"
    if ! stop_photon; then
        log_error "Failed to stop Photon service cleanly"
        return 1
    fi
    
    # Wait a moment for process to fully stop
    sleep 2
    
    # Remove existing index
    if [ -d "$INDEX_DIR" ]; then
        log_info "Removing existing opensearch directory at $INDEX_DIR"
        log_debug "Executing: rm -rf $INDEX_DIR"
        if ! rm -rf "$INDEX_DIR"; then
            log_error "Failed to remove existing index"
            return 1
        fi
    fi

    cleanup_stale_es
    
    log_info "Downloading new index"
    if ! download_index; then
        log_error "Failed to download index"
        return 1
    fi
    
    log_info "Moving index from $TEMP_DIR to $INDEX_DIR"
    if ! move_index "$TEMP_DIR" "$INDEX_DIR"; then
        log_error "Failed to move index"
        cleanup_temp
        return 1
    fi
    
    set_permissions "$INDEX_DIR" # Set permissions on the final index directory

    log_info "Verifying new index structure"
    if ! verify_structure "$DATA_DIR"; then # verify_structure "$DATA_DIR" checks $INDEX_DIR
        log_error "Failed to verify new index structure"
        cleanup_temp
        return 1
    fi
    
    log_info "Sequential update completed successfully"
    cleanup_temp
    return 0
}

update_index() {
    case "$UPDATE_STRATEGY" in
        PARALLEL)
            parallel_update
            ;;
        SEQUENTIAL)
            sequential_update
            ;;
        DISABLED)
            log_info "Index updates are disabled"
            ;;
        *)
            log_error "Invalid UPDATE_STRATEGY: $UPDATE_STRATEGY"
            return 1
            ;;
    esac
}

force_update() {
    case "$UPDATE_STRATEGY" in
        PARALLEL)
            parallel_update
            ;;
        SEQUENTIAL)
            sequential_update
            ;;
        *)
            log_info "Defaulting to sequential update for forced updates"
            sequential_update
            ;;
    esac
}

start_photon() {
    # Check if already running
    if [ -f /photon/photon.pid ]; then
        local pid
        pid=$(cat /photon/photon.pid)
        if ps -p "$pid" > /dev/null; then
            log_info "Photon service already running with PID: $pid"
            return 0
        else
            log_info "Removing stale PID file"
            rm -f /photon/photon.pid
        fi
    fi

    if [ -d "$INDEX_DIR" ]; then
        set_permissions "$INDEX_DIR" # Ensure permissions before start
    else
        log_error "Cannot start Photon: Index directory $INDEX_DIR does not exist."
        return 1
    fi

    log_info "Starting Photon service"
    java -jar photon.jar -data-dir /photon &
    local new_pid=$!
    echo $new_pid > /photon/photon.pid
    
    log_info "Photon service started successfully with PID: $new_pid"
    return 0
}

interval_to_seconds() {
    local interval=$1
    local value=${interval%[smhd]}
    local unit=${interval##*[0-9]}
    
    case $unit in
        s) echo $((value)) ;;
        m) echo $((value * 60)) ;;
        h) echo $((value * 3600)) ;;
        d) echo $((value * 86400)) ;;
        *) echo $((value * 3600)) ;;  # Default to hours
    esac
}

setup_index() {
    mkdir -p "$DATA_DIR" "$TEMP_DIR"
    
    if [ -d "$INDEX_DIR" ]; then
        if verify_structure "$DATA_DIR"; then # verify_structure "$DATA_DIR" checks $INDEX_DIR
            log_info "Found existing valid opensearch index"
            set_permissions "$INDEX_DIR" # Ensure permissions on existing valid index
            return 0
        else
            log_error "Found invalid index structure, downloading fresh index"
            rm -rf "$INDEX_DIR"
        fi
    else
        log_info "No opensearch index found, performing initial download"
    fi
    
    if ! sequential_update; then
        log_error "Failed to setup initial index"
        return 1
    fi
    
    return 0
}

main() {
    if ! setup_index; then
        exit 1
    fi

    # Only run FORCE_UPDATE once during container startup
    if [ "${FORCE_UPDATE}" = "TRUE" ]; then
        log_info "Performing forced update on startup"
        if ! force_update; then
            log_error "Forced update failed"
            exit 1
        fi
        # Disable FORCE_UPDATE after first run
        FORCE_UPDATE="FALSE"
        log_info "FORCE_UPDATE disabled after initial run"
    fi

    if ! start_photon; then
        log_error "Failed to start Photon service"
        exit 1
    fi

    if [ "$UPDATE_STRATEGY" != "DISABLED" ]; then
        local update_seconds
        update_seconds=$(interval_to_seconds "$UPDATE_INTERVAL")
        log_info "Update strategy: $UPDATE_STRATEGY"
        log_info "Update interval: $UPDATE_INTERVAL (${update_seconds} seconds)"
        
        while true; do
            log_info "Sleeping for ${update_seconds} seconds until next update"
            sleep "$update_seconds"
            log_info "Checking for index updates"
            
            local url
            if [[ -n "$FILE_URL" ]]; then
                url=$FILE_URL
                log_info "FILE_URL is set to: $FILE_URL"
            else
                url=$(prepare_download_url)
            fi

            if check_remote_index "$url"; then
                log_info "Performing scheduled index update"
                update_index
                # Restart service after update
                if ! start_photon; then
                    log_error "Failed to restart Photon service after update"
                    exit 1
                fi
            fi
        done
    else
        log_info "Update strategy is disabled, skipping update loop"
    fi

    # Wait for Photon process to finish
    wait
}

main "$@"
