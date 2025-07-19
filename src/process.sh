#!/bin/bash

source "src/config.sh"
source "src/logging.sh"

stop_photon() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE")
        
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
        rm -f "$PID_FILE"
    fi
    return 0
}

start_photon() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null; then
            log_info "Photon service already running with PID: $pid"
            return 0
        else
            log_info "Removing stale PID file"
            rm -f "$PID_FILE"
        fi
    fi

    if [ -n "${JAVA_PARAMS:-}" ]; then
        local clean_params="${JAVA_PARAMS#\"}"
        clean_params="${clean_params%\"}"
        read -a java_args <<< "$clean_params"
        gosu photon java "${java_args[@]}" -jar "$PHOTON_JAR" -data-dir "$PHOTON_DIR" ${PHOTON_PARAMS} &
    else
        gosu photon java -jar "$PHOTON_JAR" -data-dir "$PHOTON_DIR" ${PHOTON_PARAMS} &
    fi
    local new_pid=$!
    echo $new_pid > "$PID_FILE"
    
    log_info "Photon service started successfully with PID: $new_pid"
    return 0
}
