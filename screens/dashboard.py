from datetime import datetime

from config.scheduler import SessionLocal
from models.sync_schedule import SyncSchedule, SyncLog
from croniter import croniter


def get_dashboard_data(school_id):
    """
    Fetch the last sync time and next scheduled sync time.
    """
    db = SessionLocal()

    try:
        last_sync = db.query(SyncLog).filter(
            SyncLog.school_id == school_id
        ).order_by(SyncLog.timestamp.desc()).first()

        last_sync_time = last_sync.timestamp if last_sync else None
        system_status = last_sync.status if last_sync else 'never_synced'

        next_sync_time = get_next_sync_time(school_id, db)

        dashboard_data = {
            'system_status': system_status,
            'last_sync_time': last_sync_time,
            'next_sync_time': next_sync_time
        }

        return dashboard_data

    finally:
        db.close()


def get_next_sync_time(school_id, db):
    """
    Calculate the next sync time using the saved cron expression.
    """
    try:
        sync_schedule = db.query(SyncSchedule).filter(
            SyncSchedule.school_id == school_id,
            SyncSchedule.is_active == True
        ).first()

        if not sync_schedule:
            return None

        cron = croniter(
            sync_schedule.cron_expression,
            datetime.utcnow()
        )

        next_run = cron.get_next(datetime)

        return next_run

    except Exception as e:
        print(
            f"Error calculating next sync time for school {school_id}: {e}"
        )
        return None


def format_dashboard_for_display(dashboard_data):
    """
    Format dashboard information for display.
    """
    last_sync = dashboard_data['last_sync_time']
    next_sync = dashboard_data['next_sync_time']
    status = dashboard_data['system_status']

    last_sync_str = (
        last_sync.strftime('%Y-%m-%d %H:%M:%S')
        if last_sync else 'Never'
    )

    next_sync_str = (
        next_sync.strftime('%Y-%m-%d %H:%M:%S')
        if next_sync else 'Not scheduled'
    )

    display = f"""
    === Dashboard ===

    System Status: {status}
    Last Sync: {last_sync_str}
    Next Scheduled Sync: {next_sync_str}

    [View Sync Activity Log]
    """

    return display