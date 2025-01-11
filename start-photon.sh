#!/bin/bash

# Configuration
DATA_DIR="/photon/app/photon_data"
INDEX_DIR="$DATA_DIR/elasticsearch"
TEMP_DIR="/photon/app/temp"
LOG_FILE="/photon/app/photon.log"
UPDATE_STRATEGY="${UPDATE_STRATEGY:-SEQUENTIAL}"
UPDATE_INTERVAL="${UPDATE_INTERVAL:-24h}"
MIN_DISK_SPACE=100000000  # 100GB in bytes

# Logging functions
log_info() { echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_FILE"; }
log_error() { echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_FILE" >&2; }
log_debug() { echo "[DEBUG] $(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_FILE"; }

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

# Check available disk space
check_disk_space() {
    local available
    available=$(df -B1 "$DATA_DIR" | awk 'NR==2 {print $4}')
    if [ "$available" -lt "$MIN_DISK_SPACE" ]; then
        log_error "Insufficient disk space. Required: ${MIN_DISK_SPACE}B, Available: ${available}B"
        return 1
    fi
}

# Verify directory structure
verify_structure() {
    local dir=$1
    if [ ! -d "$dir/photon_data/elasticsearch" ]; then
        log_error "Invalid structure: missing elasticsearch directory"
        return 1
    fi
    return 0
}

# Download and verify index
download_index() {
    local target_dir=$1
    local temp_file="$TEMP_DIR/photon-db.tar.bz2"
    local md5_file="$TEMP_DIR/photon-db.md5"
    
    mkdir -p "$TEMP_DIR"
    
    if [[ -n "${COUNTRY_CODE}" ]]; then
        local url="https://download1.graphhopper.com/public/extracts/by-country-code/${COUNTRY_CODE}/photon-db-${COUNTRY_CODE}-latest"
    else
        local url="https://download1.graphhopper.com/public/photon-db-latest"
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
    
    log_info "Extracting index to $target_dir"
    mkdir -p "$target_dir"
    pbzip2 -dc "$temp_file" | tar x -C "$target_dir"
    
    verify_structure "$target_dir"
}

# Update index based on strategy
update_index() {
    case "$UPDATE_STRATEGY" in
        PARALLEL)
            local temp_data_dir="$TEMP_DIR/photon_data"
            download_index "$temp_data_dir"
            if verify_structure "$temp_data_dir"; then
                log_info "Swapping index directories"
                mv "$INDEX_DIR" "$INDEX_DIR.old"
                mv "$temp_data_dir/elasticsearch" "$INDEX_DIR"
                rm -rf "$INDEX_DIR.old"
            fi
            ;;
        SEQUENTIAL)
            log_info "Stopping Photon service for update"
            if [ -f /photon/photon.pid ]; then
                kill -15 "$(cat /photon/photon.pid)"
                sleep 5
            fi
            download_index "$DATA_DIR"
            start_photon
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
    java -jar photon.jar -data-dir /photon/app "$@" &
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
    check_disk_space
    
    if [ ! -d "$INDEX_DIR" ]; then
        log_info "Initial index download required"
        download_index "$DATA_DIR"
    fi
    
    if ! verify_structure "$DATA_DIR"; then
        log_error "Invalid index structure detected"
        exit 1
    fi
    
    start_photon "$@"
    
    if [ "$UPDATE_STRATEGY" != "DISABLED" ]; then
        local update_seconds
        update_seconds=$(interval_to_seconds "$UPDATE_INTERVAL")
        
        while true; do
            sleep "$update_seconds"
            log_info "Performing scheduled index update"
            update_index
        done
    fi
    
    wait
}

main "$@"
