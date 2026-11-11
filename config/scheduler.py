
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Reuse the existing PostgreSQL database configuration.
from config.database import engine, SessionLocal


logger = logging.getLogger(__name__)


# ------------------------------------------
# CREATE AND CONFIGURE SCHEDULER
# ------------------------------------------

scheduler = BackgroundScheduler()


# ------------------------------------------
# START SCHEDULER
# ------------------------------------------

def start_scheduler():
    """
    Start the background scheduler.
    """

    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started.")


# ------------------------------------------
# STOP SCHEDULER
# ------------------------------------------

def stop_scheduler():
    """
    Stop the background scheduler gracefully.
    """

    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped.")


# ------------------------------------------
# ADD SYNC JOB
# ------------------------------------------

def add_sync_job(
    job_id,
    job_func,
    schedule_time="0 8 * * *"
):
    """
    Add a sync job to the scheduler.

    Args:
        job_id: Unique job name.
        job_func: Function to execute.
        schedule_time: Cron expression (default 8 AM daily).
    """

    try:
        scheduler.add_job(
            job_func,
            CronTrigger.from_crontab(schedule_time),
            id=job_id,
            name=job_id,
            replace_existing=True
        )

        logger.info(
            "Job '%s' scheduled at %s.",
            job_id,
            schedule_time
        )

    except Exception:
        logger.exception(
            "Error scheduling job '%s'",
            job_id
        )
        raise


# ------------------------------------------
# GET DATABASE SESSION
# ------------------------------------------

def get_db():
    """
    Get a database session.
    Close the session if initialization fails.
    """

    db = None

    try:
        db = SessionLocal()
        return db

    except Exception:
        if db is not None:
            db.close()

        logger.exception(
            "Failed to create database session"
        )
        raise
