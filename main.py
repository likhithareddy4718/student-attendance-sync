import logging

from flask_app import app
from config.scheduler import (
    SessionLocal,
    add_sync_job,
    start_scheduler,
    stop_scheduler
)
from models.sync_schedule import SyncSchedule
from workers.attendance_sync import sync_attendance_for_school


# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def register_sync_jobs():
    db = SessionLocal()

    try:
        schedules = db.query(SyncSchedule).filter(
            SyncSchedule.is_active == True
        ).all()

        for schedule in schedules:
            school_id = schedule.school_id

            add_sync_job(
                job_id=f"attendance_sync_school_{school_id}",
                job_func=lambda school_id=school_id:
                    sync_attendance_for_school(school_id),
                schedule_time=schedule.cron_expression
            )

            logger.info(
                "Sync job registered for school %s",
                school_id
            )

    finally:
        db.close()


if __name__ == "__main__":
    try:
        logger.info("Starting Student Attendance Sync Platform...")

        register_sync_jobs()
        start_scheduler()

        logger.info("Scheduler started successfully.")

        app.run(
            debug=True,
            use_reloader=False
        )

    except KeyboardInterrupt:
        logger.info("Application stopped by user.")

    except Exception:
        logger.exception("Application failed to start.")

    finally:
        stop_scheduler()