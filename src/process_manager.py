#!/usr/bin/env python3

import os
import signal
import subprocess
import sys
import threading
import time
from enum import Enum
import shlex
import psutil

import requests
from requests.exceptions import RequestException
import schedule

from .utils import config
from .utils.logger import get_logger
from .filesystem import cleanup_backup_after_verification

logger = get_logger()


def check_photon_health(timeout=30, max_retries=10) -> bool:
    url = "http://localhost:2322/status"
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                logger.info("Photon health check passed")
                return True
            else:
                logger.warning(f"Photon health check failed with status {response.status_code}")
        except RequestException as e:
            logger.debug(f"Health check attempt {attempt + 1} failed: {e}")
        
        if attempt < max_retries - 1:
            time.sleep(3)
    
    logger.error(f"Photon health check failed after {max_retries} attempts")
    return False


def wait_for_photon_ready(timeout=120) -> bool:
    start_time = time.time()
    logger.info("Waiting for Photon to become ready...")
    
    while time.time() - start_time < timeout:
        if check_photon_health(timeout=5, max_retries=1):
            elapsed = time.time() - start_time
            logger.info(f"Photon ready after {elapsed:.1f} seconds")
            return True
        time.sleep(5)
    
    logger.error(f"Photon failed to become ready within {timeout} seconds")
    return False


class AppState(Enum):
    INITIALIZING = 1
    RUNNING = 2
    UPDATING = 3
    SHUTTING_DOWN = 4


class PhotonManager:
    def __init__(self):
        self.state = AppState.INITIALIZING
        self.photon_process = None
        self.should_exit = False

        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)

    def handle_shutdown(self, signum, frame):
        logger.info(f"Received shutdown signal {signum}")
        self.should_exit = True
        self.shutdown()

    def run_initial_setup(self):
        logger.info("Running initial setup...")
        result = subprocess.run(["uv", "run", "-m", "src.entrypoint", "setup"], cwd="/photon")

        if result.returncode != 0:
            logger.error("Setup failed!")
            sys.exit(1)

    def start_photon(self, max_startup_retries=3):
        for attempt in range(max_startup_retries):
            logger.info(f"Starting Photon (attempt {attempt + 1}/{max_startup_retries})...")
            self.state = AppState.RUNNING

            java_params = config.JAVA_PARAMS or ""
            photon_params = config.PHOTON_PARAMS or ""

            cmd = [
                "java",
                "--add-modules", "jdk.incubator.vector",
                "--enable-native-access=ALL-UNNAMED",
                "-Des.gateway.auto_import_dangling_indices=true",
                "-Des.cluster.routing.allocation.batch_mode=true",
                "-Dlog4j2.disable.jmx=true"
            ]
            
            if java_params:
                cmd.extend(shlex.split(java_params))
                
            cmd.extend(["-jar", "/photon/photon.jar", "-data-dir", config.DATA_DIR ])
            
            if photon_params:
                cmd.extend(shlex.split(photon_params))

            self.photon_process = subprocess.Popen(cmd, cwd="/photon", 
                                                    preexec_fn=os.setsid)

            logger.info(f"Photon started with PID: {self.photon_process.pid}")

            if wait_for_photon_ready():
                logger.info("Photon startup successful")
                return True
            else:
                logger.error(f"Photon health check failed on attempt {attempt + 1}")
                self.stop_photon()
                
                if attempt < max_startup_retries - 1:
                    logger.info("Retrying Photon startup...")
                    time.sleep(5)
        
        logger.error(f"Photon failed to start successfully after {max_startup_retries} attempts")
        return False

    def stop_photon(self):
        if self.photon_process:
            logger.info("Stopping Photon...")
            
            try:
                os.killpg(os.getpgid(self.photon_process.pid), signal.SIGTERM)
                self.photon_process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                logger.warning("Photon didn't stop gracefully, force killing...")
                # Force kill
                try:
                    os.killpg(os.getpgid(self.photon_process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass  #Process dead
                self.photon_process.wait()
            except ProcessLookupError:
                # Process dead
                pass
                
            self.photon_process = None
            
            self._cleanup_orphaned_photon_processes()
            
            self._cleanup_lock_files()
            
            time.sleep(2)
            
    def _cleanup_orphaned_photon_processes(self):
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['name'] == 'java' and proc.info['cmdline']:
                    if any('photon.jar' in arg for arg in proc.info['cmdline']):
                        logger.warning(f"Found orphaned Photon process PID {proc.info['pid']}, terminating...")
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            proc.kill()
        except Exception as e:
            logger.debug(f"Error checking for orphaned processes: {e}")
            
    def _cleanup_lock_files(self):
        lock_files = [
            os.path.join(config.OS_NODE_DIR, "node.lock"),
            os.path.join(config.OS_NODE_DIR, "data", "node.lock")
        ]
        
        for lock_file in lock_files:
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                    logger.debug(f"Removed lock file: {lock_file}")
                except Exception as e:
                    logger.debug(f"Could not remove lock file {lock_file}: {e}")

    def run_update(self):
        if config.UPDATE_STRATEGY == "DISABLED":
            logger.info("Updates disabled, skipping")
            return

        self.state = AppState.UPDATING
        logger.info(f"Running {config.UPDATE_STRATEGY.lower()} update...")

        if config.UPDATE_STRATEGY == "SEQUENTIAL":
            self.stop_photon()

        result = subprocess.run(["uv", "run", "-m", "src.updater"], cwd="/photon")

        if result.returncode == 0:
            logger.info("Update process completed, verifying Photon health...")
            
            if config.UPDATE_STRATEGY == "PARALLEL":
                self.stop_photon()
                if self.start_photon():
                    logger.info("Update completed successfully - Photon healthy")
                    target_node_dir = os.path.join(config.PHOTON_DATA_DIR, "node_1")
                    cleanup_backup_after_verification(target_node_dir)
                else:
                    logger.error("Update failed - Photon health check failed after restart")
            elif config.UPDATE_STRATEGY == "SEQUENTIAL":
                if self.start_photon():
                    logger.info("Update completed successfully - Photon healthy")
                    target_node_dir = os.path.join(config.PHOTON_DATA_DIR, "node_1")
                    cleanup_backup_after_verification(target_node_dir)
                else:
                    logger.error("Update failed - Photon health check failed after restart")
        else:
            logger.error("Update process failed!")
            if config.UPDATE_STRATEGY == "SEQUENTIAL" and not self.photon_process:
                logger.info("Attempting to restart Photon after failed update")
                if not self.start_photon():
                    logger.error("Failed to restart Photon after update failure")

        self.state = AppState.RUNNING

    def schedule_updates(self):
        if config.UPDATE_STRATEGY == "DISABLED":
            logger.info("Updates disabled, not scheduling")
            return

        interval = config.UPDATE_INTERVAL.lower()

        if interval.endswith("d"):
            days = int(interval[:-1])
            schedule.every(days).days.do(self.run_update)
            logger.info(f"Scheduling updates every {days} days")
        elif interval.endswith("h"):
            hours = int(interval[:-1])
            schedule.every(hours).hours.do(self.run_update)
            logger.info(f"Scheduling updates every {hours} hours")
        elif interval.endswith("m"):
            minutes = int(interval[:-1])
            schedule.every(minutes).minutes.do(self.run_update)
            logger.info(f"Scheduling updates every {minutes} minutes")
        else:
            logger.warning(
                f"Invalid UPDATE_INTERVAL format: {interval}, defaulting to daily"
            )
            schedule.every().day.do(self.run_update)

        def scheduler_loop():
            while not self.should_exit:
                schedule.run_pending()
                time.sleep(1)

        thread = threading.Thread(target=scheduler_loop, daemon=True)
        thread.start()

    def monitor_photon(self):
        while not self.should_exit:
            if self.photon_process and self.state == AppState.RUNNING:
                ret = self.photon_process.poll()
                if ret is not None:
                    logger.warning(f"Photon exited with code {ret}, restarting...")
                    if not self.start_photon():
                        logger.error("Failed to restart Photon after unexpected exit")
            time.sleep(5)

    def shutdown(self):
        logger.info("Shutting down...")
        self.state = AppState.SHUTTING_DOWN
        self.stop_photon()
        sys.exit(0)

    def run(self):
        logger.info("Photon Manager starting...")

        if not config.FORCE_UPDATE and os.path.isdir(config.OS_NODE_DIR):
            logger.info("Existing index found, skipping initial setup")
        else:
            self.run_initial_setup()

        if not self.start_photon():
            logger.error("Failed to start Photon during initial startup")
            sys.exit(1)

        self.schedule_updates()

        self.monitor_photon()


if __name__ == "__main__":
    manager = PhotonManager()
    manager.run()
