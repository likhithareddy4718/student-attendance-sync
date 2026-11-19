import logging

from flask_app import app
from config.scheduler import (
    SessionLocal,
    add_sync_job,
    is_valid_cron,
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
                    job_func=lambda school_id=school_id:
                        sync_attendance_for_school(school_id),
                    schedule_time=cron_expr
                )

                logger.info(
                    "Sync job registered for school %s (%s)",
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