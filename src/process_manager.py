#!/usr/bin/env python3
import os
import shlex
import signal
import subprocess
import sys
import threading
import time
from enum import Enum

import psutil
import requests
import schedule
from requests.exceptions import RequestException

from src import index, update
from src.check_remote import compare_mtime
from src.entrypoint import run_setup
from src.utils import config
from src.utils.logger import get_logger, setup_logging
from src.utils.notify import send_notification

logger = get_logger()


def check_photon_health(timeout=30, max_retries=10) -> bool:
    url = "http://localhost:2322/status"

    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                logger.info("Photon health check passed")
                return True
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

    def handle_shutdown(self, signum, _frame):
        logger.info(f"Received shutdown signal {signum}")
        self.should_exit = True
        self.shutdown()

    def start_photon(self, max_startup_retries=3):
        for attempt in range(max_startup_retries):
            logger.info(f"Starting Photon (attempt {attempt + 1}/{max_startup_retries})...")
            self.state = AppState.RUNNING

            enable_metrics = config.ENABLE_METRICS or ""
            java_params = config.JAVA_PARAMS or ""
            photon_params = config.PHOTON_PARAMS or ""

            cmd = [
                "java",
                "--add-modules",
                "jdk.incubator.vector",
                "--enable-native-access=ALL-UNNAMED",
                "-Des.gateway.auto_import_dangling_indices=true",
                "-Des.cluster.routing.allocation.batch_mode=true",
                "-Dlog4j2.disable.jmx=true",
            ]

            if java_params:
                cmd.extend(shlex.split(java_params))

            cmd.extend(
                [
                    "-jar",
                    "/photon/photon.jar",
                    "serve",
                    "-listen-ip",
                    config.PHOTON_LISTEN_IP,
                    "-data-dir",
                    config.DATA_DIR,
                ]
            )

            if enable_metrics:
                cmd.extend(["-metrics-enable", "prometheus"])

            if photon_params:
                cmd.extend(shlex.split(photon_params))

            self.photon_process = subprocess.Popen(cmd, cwd="/photon", preexec_fn=os.setsid)  # noqa S603

            logger.info(f"Photon started with PID: {self.photon_process.pid}")

            if wait_for_photon_ready():
                logger.info("Photon startup successful")
                return True
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
                    pass  # Process dead
                self.photon_process.wait()
            except ProcessLookupError:
                # Process dead
                pass

            self.photon_process = None

            self.cleanup_orphaned_photon_processes()

            self._cleanup_lock_files()

            time.sleep(2)

    def cleanup_orphaned_photon_processes(self):
        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                if (
                    proc.info["name"] == "java"
                    and proc.info["cmdline"]
                    and any("photon.jar" in arg for arg in proc.info["cmdline"])
                ):
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
            os.path.join(config.OS_NODE_DIR, "data", "node.lock"),
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

        if config.IMPORT_MODE == "jsonl":
            logger.info("Scheduled JSONL rebuilds are not implemented yet, skipping")
            return

        self.state = AppState.UPDATING
        logger.info(f"Running {config.UPDATE_STRATEGY.lower()} update...")
        update_start = time.time()

        try:
            if not compare_mtime():
                update_duration = time.time() - update_start
                logger.info(f"Index already up to date - no restart needed ({update_duration:.1f}s)")
                return

            if config.UPDATE_STRATEGY == "SEQUENTIAL":
                self.stop_photon()

            try:
                update.run_update(config.UPDATE_STRATEGY)
            except Exception as e:
                update_duration = time.time() - update_start
                logger.error(f"Update failed: {e} ({update_duration:.1f}s)")
                send_notification(f"Photon Update Failed - {e}")
                if not self.photon_process:
                    logger.info("Attempting to restart Photon after failed update")
                    if not self.start_photon():
                        logger.error("Failed to restart Photon after update failure")
                return

            logger.info("Update process completed, verifying Photon health...")

            self.stop_photon()
            if self.start_photon():
                update_duration = time.time() - update_start
                logger.info(f"Update completed successfully - Photon healthy ({update_duration:.1f}s)")
                send_notification("Photon Index Updated Successfully")
                index.drop_backup()
            else:
                update_duration = time.time() - update_start
                logger.error(f"Update failed - Photon health check failed after restart ({update_duration:.1f}s)")
                send_notification("Photon Update Failed - health check failed after index swap, service may be down")
        except Exception:
            logger.exception("Update run failed unexpectedly")
            send_notification("Photon Update Failed - unexpected error during update run")
        finally:
            self.state = AppState.RUNNING

    def schedule_updates(self):
        if config.UPDATE_STRATEGY == "DISABLED":
            logger.info("Updates disabled, not scheduling")
            return

        if config.IMPORT_MODE == "jsonl":
            logger.info("Skipping scheduled updates in JSONL mode until rebuild support is implemented")
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
            logger.warning(f"Invalid UPDATE_INTERVAL format: {interval}, defaulting to daily")
            schedule.every().day.do(self.run_update)

        def scheduler_loop():
            while not self.should_exit:
                self._run_pending_jobs()
                time.sleep(1)

        thread = threading.Thread(target=scheduler_loop, daemon=True)
        thread.start()

    def _run_pending_jobs(self):
        try:
            schedule.run_pending()
        except Exception:
            logger.exception("Scheduled job raised unexpectedly; scheduler continues running")

    def monitor_photon(self):
        while not self.should_exit:
            if self.state == AppState.RUNNING:
                if self.photon_process is None:
                    logger.warning("Photon is not running while in RUNNING state, restarting...")
                    if not self.start_photon():
                        logger.error("Failed to restart Photon, exiting for supervisor to recover")
                        sys.exit(1)
                else:
                    ret = self.photon_process.poll()
                    if ret is not None:
                        logger.warning(f"Photon exited with code {ret}, restarting...")
                        if not self.start_photon():
                            logger.error("Failed to restart Photon, exiting for supervisor to recover")
                            sys.exit(1)
            time.sleep(5)

    def shutdown(self):
        logger.info("Shutting down...")
        self.state = AppState.SHUTTING_DOWN
        self.stop_photon()
        sys.exit(0)

    def run(self):
        logger.info("Photon Manager starting...")

        try:
            run_setup()
        except update.InsufficientSpaceError:
            logger.error("Setup failed: insufficient disk space")
            sys.exit(75)
        except Exception as e:
            logger.exception("Setup failed!")
            send_notification(f"Photon-Docker setup failed - {e}")
            sys.exit(1)

        if not self.start_photon():
            logger.error("Failed to start Photon during initial startup")
            sys.exit(1)

        send_notification("Photon started successfully")

        self.schedule_updates()

        self.monitor_photon()


if __name__ == "__main__":
    setup_logging()
    manager = PhotonManager()
    manager.run()
