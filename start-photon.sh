#!/bin/bash

source "src/logging.sh"
source "src/config.sh"
source "src/process.sh"

log_info "Environment variables:"
log_info "PUID=${PUID:-9011}"
log_info "PGID=${PGID:-9011}"
log_info "UPDATE_STRATEGY=$UPDATE_STRATEGY"
log_info "UPDATE_INTERVAL=$UPDATE_INTERVAL"
log_info "LOG_LEVEL=$LOG_LEVEL"
log_info "BASE_URL=$BASE_URL"
log_info "FORCE_UPDATE=$FORCE_UPDATE"
log_info "SKIP_MD5_CHECK=$SKIP_MD5_CHECK"
log_info "COUNTRY_CODE=${COUNTRY_CODE:-not set}"
log_info "FILE_URL=${FILE_URL}"

DATA_DIR="$PHOTON_DIR"

set -euo pipefail
trap 'handle_error $? $LINENO "$BASH_COMMAND" $(printf "::%s" ${FUNCNAME[@]:-})' ERR

setup_user() {
    local target_puid="${PUID:-9011}"
    local target_gid="${PGID:-9011}"

    log_info "Ensuring user and group IDs are set correctly..."
    log_info "Target PUID: ${target_puid}, Target PGID: ${target_gid}"

    local current_gid
    current_gid=$(getent group photon | cut -d: -f3)

    if [ "$current_gid" != "$target_gid" ]; then
        log_info "Updating photon group GID from ${current_gid} to ${target_gid}..."
        groupmod -o -g "$target_gid" photon
    fi

    local current_puid
    current_puid=$(getent passwd photon | cut -d: -f3)

    if [ "$current_puid" != "$target_puid" ]; then
        log_info "Updating photon user UID from ${current_puid} to ${target_puid}..."
        usermod -o -u "$target_puid" photon
    fi
}

handle_error() {
    local exit_code=$1
    local line_no=$2
    local last_command=$4
    local func_trace=$5
    log_error "Error $exit_code occurred on line $line_no: $last_command"
    log_error "Function trace: $func_trace"
    cleanup_and_exit
}

cleanup_and_exit() {
    log_info "Cleaning up temporary files..."
    stop_photon
    if [ -d "$TEMP_DIR" ]; then
        if ! rm -rf "${TEMP_DIR:?}"/*; then
            log_error "Failed to clean up temporary directory"
        fi
    fi
    rm -f /photon/photon.pid
    exit 1
}

check_disk_space() {
    local url=$1
    local available
    local full_url="${url}.tar.bz2"

    log_debug "Checking disk space for URL: $full_url"
    log_debug "URL components - Protocol: ${full_url%%://*}, Host: ${full_url#*://}, Path: ${full_url#*://*/}"
    
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
    log_info "Ensuring correct ownership and permissions for $dir..."

    local current_owner
    current_owner=$(stat -c '%u:%g' "$dir" 2>/dev/null || echo "notfound")
    log_debug "Current Owner is $current_owner"
    local target_owner
    target_owner="$(id -u photon):$(id -g photon)"

    if [ "$current_owner" != "$target_owner" ]; then
        log_info "Updating ownership of $dir to photon:photon (${target_owner})"
        if ! chown -R photon:photon "$dir"; then
            log_info "WARNING: Failed to chown $dir to photon:photon. This might be due to host volume restrictions. The application may encounter permission issues."
        else
            log_debug "Successfully changed ownership of $dir."
        fi
    else
        log_debug "Ownership of $dir is already correct."
    fi
}


check_remote_index() {
    local url=$1
    local full_url="${url}.tar.bz2"

    log_debug "Checking if remote index is newer than local"
    log_debug "Remote URL: $full_url"

    if [ "${FORCE_UPDATE}" = "TRUE" ]; then
        log_info "Force update requested, skipping timestamp check"
        return 0
    fi

    local remote_time
    local wget_output

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
    
    remote_epoch=$(date -d "$remote_time" +%s 2>/dev/null)
    
    if [ -d "$INDEX_DIR" ]; then
        local_epoch=$(stat -c %Y "$INDEX_DIR" 2>/dev/null)
        
        log_debug "Remote index timestamp: $remote_time (${remote_epoch})"
        log_debug "Local index timestamp: $(date -d "@$local_epoch" 2>/dev/null) (${local_epoch})"
        
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
    if ! gosu photon bash -c "cd '$dir' && md5sum -c <(echo \"\$(cut -d' ' -f1 '$(basename "$md5_file")')  $(basename "$file")\")"; then
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
    if ! pbzip2 -dc "$archive" | gosu photon tar x -C "$extract_dir"; then
        log_error "Failed to extract files"
        return 1
    fi
    log_info "Extraction completed successfully"
    return 0
}

move_index() {
    local source_dir=$1
    local target_dir=$2
    
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
    if [ -d "$ES_DATA_DIR" ]; then
        log_info "Removing old elasticsearch directory at $ES_DATA_DIR"
        rm -rf "$ES_DATA_DIR" || log_error "Failed to remove old elasticsearch index"
    fi
}

prepare_download_url() {
    local base_url="${BASE_URL%/}"
    local result_url
    
    if [[ -n "${COUNTRY_CODE:-}" ]]; then
        result_url="${base_url}/extracts/by-country-code/${COUNTRY_CODE}/photon-db-${COUNTRY_CODE}-latest"
    else
        result_url="${base_url}/photon-db-latest"
    fi
    
    echo "$result_url"
}

download_index() {
    local url
    url=$(prepare_download_url)
    log_debug "Download URL: $url"
    log_debug "Full tar.bz2 URL: ${url}.tar.bz2"
    log_debug "Full MD5 URL: ${url}.tar.bz2.md5"
    
    mkdir -p "$TEMP_DIR"
    log_debug "Created temp directory: $TEMP_DIR"
    chown photon:photon "$TEMP_DIR" 
    log_debug "Checking disk space for download"
    if ! check_disk_space "$url"; then
        log_error "Disk space check failed"
        cleanup_temp
        return 1
    fi
    local download_url
    if [[ -n "$FILE_URL" ]]; then
        download_url="$FILE_URL"
        log_info "FILE_URL is set to: $FILE_URL"
    else
        download_url="${url}.tar.bz2"
    fi
    if ! download_file "${download_url}" "$TEMP_DIR/photon-db.tar.bz2"; then
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
        log_debug "Starting MD5 verification"
        if ! verify_checksum "$TEMP_DIR/photon-db.tar.bz2" "$TEMP_DIR/photon-db.md5"; then
            cleanup_temp
            return 1
        fi
        log_info "MD5 verification successful"
        log_debug "MD5 verification completed"
    
        log_info "Extracting archive, this may take some time..."
    else
        log_info "Skipping MD5 verification as requested"
    fi
    
    log_info "Extracting archive to $TEMP_DIR"
    if ! extract_archive "$TEMP_DIR/photon-db.tar.bz2" "$TEMP_DIR"; then
        log_error "Failed to extract files"
        cleanup_temp
        return 1
    fi
    
    log_info "Extraction completed successfully"
    return 0
}

parallel_update() {
    log_info "Starting parallel update process"
    
    log_debug "Downloading new index while current service is running"
    if ! download_index; then
        log_error "Failed to download index"
        return 1
    fi
    
    log_info "Verifying downloaded index structure"
    if ! verify_structure "$TEMP_DIR"; then
        log_error "Downloaded index verification failed"
        cleanup_temp
        return 1
    fi

    
    log_info "Stopping Photon service before swapping indexes"
    if ! stop_photon; then
        log_error "Failed to stop Photon service cleanly"
        cleanup_temp
        return 1
    fi
    
    sleep 5
    
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
    
    set_permissions "$INDEX_DIR" 

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
    
    sleep 2
    
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
    
    set_permissions "$INDEX_DIR" 

    log_info "Verifying new index structure"
    if ! verify_structure "$DATA_DIR"; then 
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
        if verify_structure "$DATA_DIR"; then 
            log_info "Found existing valid opensearch index"
            set_permissions "$INDEX_DIR" 
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
    setup_user

    if ! setup_index; then
        exit 1
    fi

    local initial_force_update="${FORCE_UPDATE}"
    
    export FORCE_UPDATE="FALSE"
    
    if [ "$initial_force_update" = "TRUE" ]; then
        log_info "Performing forced update on startup"
        if ! force_update; then
            log_error "Forced update failed"
            exit 1
        fi
        log_info "Force update completed"
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
                url="$FILE_URL"
                log_info "FILE_URL is set to: $FILE_URL"
            else
                url="$(prepare_download_url)"
            fi

            if check_remote_index "$url"; then
                log_info "Performing scheduled index update"
                update_index
                if ! start_photon; then
                    log_error "Failed to restart Photon service after update"
                    exit 1
                fi
            fi
        done
    else
        log_info "Update strategy is disabled, skipping update loop"
    fi

    wait
}

main "$@"
