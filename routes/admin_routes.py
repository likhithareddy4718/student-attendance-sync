
from flask import Blueprint, render_template, session

from config.database import get_db

from models.sync_log import (
    get_sync_logs_for_school,
    get_sync_log_by_id
)
from screens.dashboard import get_next_sync_time
from utils.security import login_required


# Create admin routes blueprint.
admin_routes_bp = Blueprint(
    "admin_routes",
    __name__
)


# Default fallback school ID if not in session
ADMIN_SCHOOL_ID = 8


# --------------------------------------------------
# ROUTE 1: DISPLAY SYNC ACTIVITY LOG
# --------------------------------------------------

@admin_routes_bp.route("/admin/sync-activity-log")
@login_required
def sync_activity_log():
    """
    Display recent sync attempts for the administrator's school.
    """

    db_generator = get_db()
    db = next(db_generator)

    try:
        school_id = session.get("school_id") or ADMIN_SCHOOL_ID

        # Fetch the 50 most recent sync logs.
        sync_logs = get_sync_logs_for_school(
            db,
            school_id,
            limit=50
        )

        next_run = get_next_sync_time(school_id, db)
        next_sync_str = (
            next_run.strftime('%Y-%m-%d %H:%M:%S')
            if next_run else "Not scheduled"
        )

        return render_template(
            "sync_activity_log.html",
            sync_logs=sync_logs,
            next_sync_time=next_sync_str
        )

    finally:
        db_generator.close()


# --------------------------------------------------
# ROUTE 2: DISPLAY ERROR DETAILS
# --------------------------------------------------

@admin_routes_bp.route(
    "/admin/sync-error-details/<int:log_id>"
)
@login_required
def sync_error_details(log_id):
    """
    Display detailed error information for a specific sync.
    """

    db_generator = get_db()
    db = next(db_generator)

    try:
        school_id = session.get("school_id") or ADMIN_SCHOOL_ID

        # Fetch the selected sync log by its ID.
        sync_log = get_sync_log_by_id(
            db,
            log_id
        )

        # Check whether the log exists and belongs
        # to the administrator's school.
        if not sync_log or sync_log.school_id != school_id:
            return "Sync log not found", 404

        # Pass the record as 'log' because the HTML
        # template uses the variable name log.
        return render_template(
            "sync_error_details.html",
            log=sync_log
        )

    finally:
        db_generator.close()
