from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean,
    ForeignKey, Table
)
from datetime import datetime

from config.database import Base
from models.sync_log import SyncLog


# Register the existing schools table in SQLAlchemy metadata
if "schools" not in Base.metadata.tables:
    Table(
        "schools",
        Base.metadata,
        Column("id", Integer, primary_key=True)
    )


class SyncSchedule(Base):
    """
    Stores the schedule for each school's attendance sync.
    """
    __tablename__ = "sync_schedules"

    id = Column(Integer, primary_key=True)
    school_id = Column(
        Integer,
        ForeignKey("schools.id"),
        nullable=False
    )
    cron_expression = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )