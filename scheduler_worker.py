"""
Standalone Scheduler Worker Process for Student Attendance Sync Platform.

Runs APScheduler in a separate background worker process to avoid duplicate
scheduler instances when running Flask with multiple Gunicorn workers.

Usage:
    python scheduler_worker.py
"""

import logging
import signal
import sys
import time

from config.scheduler import (
    SessionLocal,
    add_sync_job,
    is_valid_cron,
    start_scheduler,
    stop_scheduler
)
from models.sync_schedule import SyncSchedule
from workers.attendance_sync import sync_attendance_for_school

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("scheduler_worker")

running = True


def signal_handler(signum, frame):
    global running
    logger.info("Received termination signal %s. Shutting down...", signum)
    running = False


def register_sync_jobs():
    db = SessionLocal()
    try:
        schedules = db.query(SyncSchedule).filter(
            SyncSchedule.is_active == True
        ).all()

        for schedule in schedules:
            school_id = schedule.school_id
            cron_expr = schedule.cron_expression or "0 8 * * *"

            if not is_valid_cron(cron_expr):
                logger.warning(
                    "Skipping invalid cron '%s' for school %s",
                    cron_expr,
                    school_id
                )
                continue

            try:
                add_sync_job(
                    job_id=f"attendance_sync_school_{school_id}",
                    job_func=lambda s_id=school_id: sync_attendance_for_school(s_id),
                    schedule_time=cron_expr
                )
                logger.info(
                    "Registered sync job for school %s with schedule '%s'",
                    school_id,
                    cron_expr
                )
            except Exception as e:
                logger.error(
                    "Failed to register sync job for school %s: %s",
                    school_id,
                    e
                )
    finally:
        db.close()


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting Attendance Sync Background Worker...")
    try:
        register_sync_jobs()
        start_scheduler()
        logger.info("Scheduler worker is running. Press Ctrl+C to terminate.")

        while running:
            time.sleep(1)

    except Exception:
        logger.exception("Scheduler worker encountered an error")
    finally:
        logger.info("Stopping scheduler...")
        stop_scheduler()
        logger.info("Scheduler worker stopped cleanly.")


if __name__ == "__main__":
    main()
