import re

from crontab import CronTab

from src.utils import config
from src.utils.logger import get_logger

logging = get_logger()

def setup_cronjob():

    if not config.UPDATE_STRATEGY == "DISABLED":

        update_interval = config.UPDATE_INTERVAL
        try:
            cron = CronTab(user=True)
            command = "flock -n /tmp/photon_updater.lock -c 'uv run /photon/updater.py' >> /proc/1/fd/1 2>&1"
            comment = "photon-docker updater"
            for job in cron:
                if job.comment == comment:
                    logging.info(f"Cronjob with comment '{comment}' already exists. Skipping creation.")
                    return


            job = cron.new(command=command, comment=comment)

            # Parse update interval 
            match = re.match(r"(\d+)([dhm])", update_interval.lower())
            if not match:
                logging.error(f"Invalid UPDATE_INTERVAL format: {update_interval}. Expected format like '30d', '720h', '3m'.")
                return

            value, unit = int(match.group(1)), match.group(2)

            if unit == 'd':
                job.day.every(value)
                job.hour.on(0)
                job.minute.on(0)
            elif unit == 'h':
                job.hour.every(value)
                job.minute.on(0)
            elif unit == 'm':
                job.minute.every(value)

            cron.write()
            logging.info(f"Successfully created cronjob to run every {value}{unit}.")
        
        except Exception as e:
            logging.error(f"Failed to create cronjob: {e}")
    else:
        logging.info("Skipping Cronjob Creation. Updates Disabled")

