#!/usr/bin/env python3

import os
import signal
import subprocess
import sys
import threading
import time
from enum import Enum

import schedule

from src.utils import config
from src.utils.logger import get_logger

logger = get_logger()


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
        result = subprocess.run(["uv", "run", "entrypoint.py", "setup"], cwd="/photon")

        if result.returncode != 0:
            logger.error("Setup failed!")
            sys.exit(1)

    def start_photon(self):
        logger.info("Starting Photon...")
        self.state = AppState.RUNNING

        java_params = config.JAVA_PARAMS or ""
        photon_params = config.PHOTON_PARAMS or ""

        cmd = f"java --add-modules jdk.incubator.vector --enable-native-access=ALL-UNNAMED -Des.gateway.auto_import_dangling_indices=true -Des.cluster.routing.allocation.batch_mode=true -Dlog4j2.disable.jmx=true {java_params} -jar /photon/photon.jar {photon_params}"

        self.photon_process = subprocess.Popen(cmd, shell=True, cwd="/photon")

        logger.info(f"Photon started with PID: {self.photon_process.pid}")

    def stop_photon(self):
        if self.photon_process:
            logger.info("Stopping Photon...")
            self.photon_process.terminate()
            try:
                self.photon_process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                logger.warning("Photon didn't stop gracefully, killing...")
                self.photon_process.kill()
                self.photon_process.wait()
            self.photon_process = None

    def run_update(self):
        if config.UPDATE_STRATEGY == "DISABLED":
            logger.info("Updates disabled, skipping")
            return

        self.state = AppState.UPDATING
        logger.info(f"Running {config.UPDATE_STRATEGY.lower()} update...")

        if config.UPDATE_STRATEGY == "SEQUENTIAL":
            self.stop_photon()

        result = subprocess.run(["uv", "run", "updater.py"], cwd="/photon")

        if result.returncode == 0:
            logger.info("Update completed successfully")
            if config.UPDATE_STRATEGY == "PARALLEL":
                self.stop_photon()
                time.sleep(10)
                self.start_photon()
            elif config.UPDATE_STRATEGY == "SEQUENTIAL":
                self.start_photon()
        else:
            logger.error("Update failed!")
            if config.UPDATE_STRATEGY == "SEQUENTIAL" and not self.photon_process:
                logger.info("Restarting Photon after failed update")
                self.start_photon()

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
                    self.start_photon()
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

        self.start_photon()

        self.schedule_updates()

        self.monitor_photon()


if __name__ == "__main__":
    manager = PhotonManager()
    manager.run()
