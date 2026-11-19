from .school import db, School, APICredentials
from .sync_log import SyncLog
from .sync_schedule import SyncSchedule

Schools = School

__all__ = ["db", "School", "Schools", "APICredentials", "SyncLog", "SyncSchedule"]
