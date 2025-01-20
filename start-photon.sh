#!/bin/bash

# Configuration
DATA_DIR="/photon"
INDEX_DIR="/photon/photon_data/elasticsearch"
TEMP_DIR="/photon/photon_data/temp"
UPDATE_STRATEGY="${UPDATE_STRATEGY:-PARALLEL}"
UPDATE_INTERVAL="${UPDATE_INTERVAL:-24h}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { 
    if [[ "$LOG_LEVEL" != "ERROR" ]]; then
        echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*"
    fi
}
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2; }
log_debug() { 
    if [[ "$LOG_LEVEL" == "DEBUG" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*"
    fi
}

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

    # Get remote file size using wget spider
    local remote_size
    if ! remote_size=$(wget --spider --server-response "$url.tar.bz2" 2>&1 | grep "Content-Length" | awk '{print $2}' | tail -1); then
        log_error "Failed to execute wget spider command"
        return 1
    fi
    
    if [ -z "$remote_size" ]; then
        log_error "Failed to get remote file size"
        return 1
    fi
    
    # Check available space in photon_data directory
    mkdir -p "$DATA_DIR/photon_data"
    available=$(df -B1 "$DATA_DIR/photon_data" | awk 'NR==2 {print $4}')
    if [ "$available" -lt "$remote_size" ]; then
        log_error "Insufficient disk space. Required: ${remote_size}B , Available: ${available}B"
        return 1
    fi
    
    log_info "Sufficient disk space available. Required: ${remote_size}B, Available: ${available}B"
}

# Verify directory structure and index
verify_structure() {
    local dir=$1
    if [ ! -d "$dir/photon_data/elasticsearch" ]; then
        log_error "Invalid structure: missing elasticsearch directory"
        return 1
    fi
    
    # Ensure proper permissions
    chown -R 1000:1000 "$dir/photon_data/elasticsearch" 2>/dev/null || true
    chmod -R 755 "$dir/photon_data/elasticsearch" 2>/dev/null || true
    
    return 0
}

# Check if remote index is newer than local
check_remote_index() {
    local url=$1
    local remote_time

    # Get remote file timestamp using HEAD request
    remote_time=$(wget --spider -S "$url.tar.bz2" 2>&1 | grep "Last-Modified" | cut -d' ' -f4-)
    if [ -z "$remote_time" ]; then
        log_error "Failed to get remote index timestamp"
        return 2
    fi
    
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
    if ! wget --progress=dot:giga -O "$output_file" "$url"; then
        log_error "Failed to download file from $url"
        return 1
    fi
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
    return 0
}

extract_archive() {
    local archive=$1
    local extract_dir=$2
    
    log_debug "Creating extraction directory $extract_dir"
    mkdir -p "$extract_dir"
    
    log_debug "Extracting $archive to $extract_dir"
    if ! pbzip2 -dc "$archive" | tar x -C "$extract_dir"; then
        log_error "Failed to extract files"
        return 1
    fi
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
    
    # Find elasticsearch directory recursively
    local es_dir
    es_dir=$(find "$source_dir" -type d -name "elasticsearch" | head -n 1)
    
    if [ -n "$es_dir" ]; then
        log_info "Found elasticsearch directory at $es_dir"
        log_debug "Moving elasticsearch from $es_dir to $target_dir"
        mkdir -p "$(dirname "$target_dir")"
        mv "$es_dir" "$target_dir"
        return 0
    else
        log_error "Could not find elasticsearch directory in extracted files"
        return 1
    fi
}

cleanup_temp() {
    log_info "Cleaning up temporary directory"
    rm -rf "${TEMP_DIR:?}"/*
}

# Prepare download URL based on country code
prepare_download_url() {
    local base_url="https://download1.graphhopper.com/public/photon-db-latest"
    if [[ -n "${COUNTRY_CODE:-}" ]]; then
        echo "https://download1.graphhopper.com/public/extracts/by-country-code/${COUNTRY_CODE}/photon-db-${COUNTRY_CODE}-latest"
    else
        echo "$base_url"
    fi
}

# Download and verify index
download_index() {
    local url
    url=$(prepare_download_url)
    
    mkdir -p "$TEMP_DIR"
    
    # Check disk space before downloading
    check_disk_space "$url"
    
    # Download files
    if ! wget --progress=dot:giga -O "$TEMP_DIR/photon-db.tar.bz2" "${url}.tar.bz2"; then
        cleanup_temp
        return 1
    fi
    
    if ! wget -O "$TEMP_DIR/photon-db.md5" "${url}.tar.bz2.md5"; then
        cleanup_temp
        return 1
    fi
    
    # Verify checksum
    if ! (cd "$TEMP_DIR" && md5sum -c <(cut -d' ' -f1 photon-db.md5 > temp.md5 && echo "$(cat temp.md5)  photon-db.tar.bz2" && rm temp.md5)); then
        log_error "MD5 verification failed"
        cleanup_temp
        return 1
    fi
    
    # Extract archive in place
    if ! pbzip2 -dc "$TEMP_DIR/photon-db.tar.bz2" | tar x -C "$TEMP_DIR"; then
        log_error "Failed to extract files"
        cleanup_temp
        return 1
    fi
    
    return 0
}

# Strategy-specific update functions
parallel_update() {
    # Download and prepare new index while current one is running
    if ! download_index; then
        return 1
    fi
    
    # Verify the downloaded index
    if ! verify_structure "$TEMP_DIR"; then
        cleanup_temp
        return 1
    fi
    
    # Stop service and swap indexes
    stop_photon
    
    # Backup and swap
    mv "$INDEX_DIR" "$INDEX_DIR.old" 2>/dev/null || true
    if ! move_index "$TEMP_DIR" "$INDEX_DIR"; then
        # Restore backup on failure
        mv "$INDEX_DIR.old" "$INDEX_DIR" 2>/dev/null || true
        cleanup_temp
        return 1
    fi
    
    # Clean up
    rm -rf "$INDEX_DIR.old" 2>/dev/null || true
    cleanup_temp "$TEMP_DIR"
    
    # Start service
    start_photon
    return 0
}

sequential_update() {
    # Stop service first
    stop_photon
    
    # Remove existing index
    if [ -d "$INDEX_DIR" ]; then
        log_info "Removing existing elasticsearch directory at $INDEX_DIR"
        rm -rf "$INDEX_DIR"
    fi
    
    # Download new index
    if ! download_index; then
        return 1
    fi
    
    # Move to final location
    if ! move_index "$TEMP_DIR" "$INDEX_DIR"; then
        cleanup_temp
        return 1
    fi
    
    # Verify and clean up
    if ! verify_structure "$DATA_DIR"; then
        log_error "Failed to verify new index structure"
        cleanup_temp "$TEMP_DIR"
        return 1
    fi
    
    cleanup_temp "$TEMP_DIR"
    
    # Start service
    start_photon
    return 0
}

# Update index based on strategy
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

# Start Photon service
start_photon() {
    log_info "Starting Photon service"
    java -jar photon.jar -data-dir /photon &
    echo $! > /photon/photon.pid
    return 0
}

# Convert update interval to seconds
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

# Initialize or verify index
setup_index() {
    mkdir -p "$DATA_DIR" "$TEMP_DIR"
    
    if [ -d "$INDEX_DIR" ]; then
        if verify_structure "$DATA_DIR"; then
            log_info "Found existing valid elasticsearch index, starting photon"
            start_photon
            return 0
        else
            log_error "Found invalid index structure, downloading fresh index"
            rm -rf "$INDEX_DIR"
        fi
    else
        log_info "No elasticsearch index found, performing initial download"
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
            url=$(prepare_download_url)
            
            if check_remote_index "$url"; then
                log_info "Performing scheduled index update"
                update_index
            fi
        done
    else
        log_info "Update strategy is disabled, skipping update loop"
    fi
    
    wait
}

main "$@"
