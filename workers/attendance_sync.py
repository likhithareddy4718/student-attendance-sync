
import logging

from sync.attendance_sync import run_sync_for_school


logger = logging.getLogger(__name__)


def sync_attendance_for_school(school_id: int):
    """
    Worker function called by the background scheduler.

    It reuses the existing attendance sync process to:
    1. Fetch attendance from the school's API.
    2. Convert attendance data.
    3. Store records in PostgreSQL.
    4. Detect absences.
    5. Process parent notifications.
    6. Save sync logs.

    Args:
        school_id: ID of the school to synchronize.

    Returns:
        Dictionary containing the synchronization result.
    """

    logger.info(
        "Starting scheduled attendance sync for school_id=%s",
        school_id
    )

    try:
        result = run_sync_for_school(school_id)

        if result.get("success"):
            logger.info(
                "Scheduled sync completed for school_id=%s: %s",
                school_id,
                result.get("message")
            )
        else:
            logger.error(
                "Scheduled sync failed for school_id=%s: %s",
                school_id,
                result.get("errors")
            )

        return result

    except Exception:
        logger.exception(
            "Unexpected worker error for school_id=%s",
            school_id
        )
        raise
