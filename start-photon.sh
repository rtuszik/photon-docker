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
trap 'handle_error $? $LINENO $BASH_LINENO "$BASH_COMMAND" $(printf "::%s" ${FUNCNAME[@]:-})' ERR

handle_error() {
    local exit_code=$1
    local line_no=$2
    local bash_lineno=$3
    local last_command=$4
    local func_trace=$5
    log_error "Error $exit_code occurred on line $line_no: $last_command"
    log_error "Function trace: $func_trace"
    cleanup_and_exit
}

# Cleanup function
cleanup_and_exit() {
    log_info "Cleaning up temporary files..."
    rm -rf "${TEMP_DIR:?}"/*
    exit 1
}

# Check available disk space against remote file size
check_disk_space() {
    local url=$1
    local available
    local required_space

    # Get remote file size using wget spider
    local remote_size
    remote_size=$(wget --spider --server-response "$url.tar.bz2" 2>&1 | grep "Content-Length" | awk '{print $2}' | tail -1)
    
    if [ -z "$remote_size" ]; then
        log_error "Failed to get remote file size"
        return 1
    fi
    
    # Check available space
    available=$(df -B1 "$DATA_DIR" | awk 'NR==2 {print $4}')
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
    local local_time

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
        
        # Compare timestamps with 1 hour tolerance
        local time_diff=$((remote_epoch - local_epoch))
        if [ "${time_diff#-}" -lt 3600 ]; then
            log_info "Local index is up to date (within 1 hour tolerance)"
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

# Download and verify index
download_index() {
    local target_dir=$1
    local temp_file="$TEMP_DIR/photon-db.tar.bz2"
    local md5_file="$TEMP_DIR/photon-db.md5"
    
    mkdir -p "$TEMP_DIR"
    
    local url="https://download1.graphhopper.com/public/photon-db-latest"
    url="https://download1.graphhopper.com/public/photon-db-latest"
    if [[ -n "${COUNTRY_CODE:-}" ]]; then
        url="https://download1.graphhopper.com/public/extracts/by-country-code/${COUNTRY_CODE}/photon-db-${COUNTRY_CODE}-latest"
    fi
    
    log_info "Downloading index from $url"
    wget --progress=dot:giga -O "$temp_file" "${url}.tar.bz2"
    wget -O "$md5_file" "${url}.tar.bz2.md5"
    
    log_info "Verifying MD5 checksum"
    # Get just the MD5 hash from the file and verify against our downloaded file
    if ! (cd "$TEMP_DIR" && md5sum -c <(cut -d' ' -f1 photon-db.md5 > temp.md5 && echo "$(cat temp.md5)  photon-db.tar.bz2" && rm temp.md5)); then
        log_error "MD5 verification failed"
        return 1
    fi
    
    log_info "Extracting index to temporary location"
    local extract_dir="$TEMP_DIR/extract"
    mkdir -p "$extract_dir"
    
    # Extract to temporary location first
    if ! pbzip2 -dc "$temp_file" | tar x -C "$extract_dir"; then
        log_error "Failed to extract index files"
        return 1
    fi
    
    log_info "Moving extracted files to final location"
    mkdir -p "$target_dir/photon_data"
    
    # Find elasticsearch directory recursively
    local es_dir
    es_dir=$(find "$extract_dir" -type d -name "elasticsearch" | head -n 1)
    
    if [ -n "$es_dir" ]; then
        log_info "Found elasticsearch directory at $es_dir"
        
        log_debug "Extract directory structure:"
        find "$extract_dir" -type d -maxdepth 3 | while read -r line; do log_debug "DIR: $line"; done
        
        log_debug "Target directory structure before move:"
        find "$target_dir" -type d -maxdepth 3 | while read -r line; do log_debug "DIR: $line"; done
        
        log_info "Removing old elasticsearch directory at $target_dir/photon_data/elasticsearch"
        rm -rf "$target_dir/photon_data/elasticsearch"
        
        log_info "Moving elasticsearch from $es_dir to $target_dir/photon_data/elasticsearch"
        mkdir -p "$target_dir/photon_data"
        mv "$es_dir" "$target_dir/photon_data/elasticsearch"
        
        log_debug "Target directory structure after move:"
        find "$target_dir" -type d -maxdepth 3 | while read -r line; do log_debug "DIR: $line"; done
        
        log_info "Cleaning up extract directory at $extract_dir"
        rm -rf "$extract_dir"
    else
        log_error "Could not find elasticsearch directory in extracted files"
        log_debug "Extract directory contents:"
        find "$extract_dir" -type d | while read -r line; do log_debug "$line"; done
        rm -rf "$extract_dir"
        return 1
    fi
    
    if ! verify_structure "$target_dir"; then
        log_error "Index verification failed after extraction"
        return 1
    fi
}

# Update index based on strategy
update_index() {
    case "$UPDATE_STRATEGY" in
        PARALLEL)
            local temp_data_dir="$TEMP_DIR/photon_data"
            download_index "$TEMP_DIR"
            if verify_structure "$TEMP_DIR"; then
                log_info "Stopping Photon service for index swap"
                if [ -f /photon/photon.pid ]; then
                    kill -15 "$(cat /photon/photon.pid)"
                    sleep 5
                fi
                log_info "Swapping index directories"
                mv "$INDEX_DIR" "$INDEX_DIR.old" 2>/dev/null || true
                mv "$TEMP_DIR/photon_data/elasticsearch" "$INDEX_DIR"
                rm -rf "$INDEX_DIR.old" 2>/dev/null || true
                start_photon
            fi
            rm -rf "$temp_data_dir" 2>/dev/null || true
            ;;
        SEQUENTIAL)
            log_info "Stopping Photon service for update"
            if [ -f /photon/photon.pid ]; then
                kill -15 "$(cat /photon/photon.pid)"
                sleep 5
            fi
            if [ -d "$INDEX_DIR" ]; then
                log_info "Removing existing elasticsearch directory at $INDEX_DIR"
                rm -rf "$INDEX_DIR"
            fi
            download_index "$DATA_DIR"
            if verify_structure "$DATA_DIR"; then
                start_photon
            else
                log_error "Failed to verify new index structure"
                return 1
            fi
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
    java -jar photon.jar -data-dir /photon "$@" &
    echo $! > /photon/photon.pid
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

# Main execution
main() {
    mkdir -p "$DATA_DIR" "$TEMP_DIR"
    url="https://download1.graphhopper.com/public/photon-db-latest"
    if [[ -n "${COUNTRY_CODE:-}" ]]; then
        url="https://download1.graphhopper.com/public/extracts/by-country-code/${COUNTRY_CODE}/photon-db-${COUNTRY_CODE}-latest"
    fi
    check_disk_space "$url"
    
    if [ -d "$INDEX_DIR" ]; then
        if verify_structure "$DATA_DIR"; then
            log_info "Found existing valid elasticsearch index"
            local url="https://download1.graphhopper.com/public/photon-db-latest"
            if [[ -n "${COUNTRY_CODE:-}" ]]; then
                url="https://download1.graphhopper.com/public/extracts/by-country-code/${COUNTRY_CODE}/photon-db-${COUNTRY_CODE}-latest"
            fi
            
            if check_remote_index "$url"; then
                log_info "Downloading newer index version"
                rm -rf "$INDEX_DIR"
                download_index "$DATA_DIR"
            fi
        else
            log_error "Found invalid index structure, downloading fresh index"
            rm -rf "$INDEX_DIR"
            download_index "$DATA_DIR"
        fi
    else
        log_info "No elasticsearch index found, performing initial download"
        download_index "$DATA_DIR"
    fi
    
    if ! verify_structure "$DATA_DIR"; then
        log_error "Invalid index structure detected after setup"
        exit 1
    fi
    
    start_photon "$@"
    
    if [ "$UPDATE_STRATEGY" != "DISABLED" ]; then
        local update_seconds
        update_seconds=$(interval_to_seconds "$UPDATE_INTERVAL")
        log_info "Update strategy: $UPDATE_STRATEGY"
        log_info "Update interval: $UPDATE_INTERVAL (${update_seconds} seconds)"
        
        while true; do
            log_info "Sleeping for ${update_seconds} seconds until next update"
            sleep "$update_seconds"
            log_info "Checking for index updates"
            local url="https://download1.graphhopper.com/public/photon-db-latest"
            if [[ -n "${COUNTRY_CODE:-}" ]]; then
                url="https://download1.graphhopper.com/public/extracts/by-country-code/${COUNTRY_CODE}/photon-db-${COUNTRY_CODE}-latest"
            fi
            
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
