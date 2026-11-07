
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime

from config.database import Base


class SyncLog(Base):
    """
    SQLAlchemy model for the sync_logs database table.
    """

    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)

    school_id = Column(
        Integer,
        ForeignKey("schools.id"),
        nullable=False
    )

    timestamp = Column(
        DateTime,
        default=datetime.utcnow
    )

    status = Column(String(255))

    error_message = Column(String)

    def __repr__(self):
        return (
            f"<SyncLog(id={self.id}, "
            f"school_id={self.school_id}, "
            f"status={self.status}, "
            f"timestamp={self.timestamp})>"
        )


# ------------------------------------------
# FETCH RECENT SYNC LOGS FOR A SCHOOL
# ------------------------------------------

def get_sync_logs_for_school(db, school_id, limit=50):
    """
    Fetch recent sync logs for a specific school,
    ordered by newest first.

    Args:
        db: Database session from get_db()
        school_id: School ID
        limit: Maximum number of logs to return

    Returns:
        List of SyncLog objects.
    """

    return db.query(SyncLog).filter(
        SyncLog.school_id == school_id
    ).order_by(
        SyncLog.timestamp.desc()
    ).limit(limit).all()


# ------------------------------------------
# FETCH ONE SYNC LOG BY ID
# ------------------------------------------

def get_sync_log_by_id(db, log_id):
    """
    Fetch a single sync log using its ID.

    Returns:
        SyncLog object or None if not found.
    """

    return db.query(SyncLog).filter(
        SyncLog.id == log_id
    ).first()
