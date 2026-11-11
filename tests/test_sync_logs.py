import pytest
from datetime import datetime
from unittest.mock import MagicMock

from models.sync_log import (
    SyncLog,
    get_sync_logs_for_school,
    get_sync_log_by_id
)


def test_create_success_sync_log():
    log = SyncLog(
        id=1,
        school_id=8,
        timestamp=datetime.now(),
        status="success",
        error_message=None
    )

    assert log.school_id == 8
    assert log.status == "success"
    assert log.error_message is None


def test_create_failed_sync_log():
    error = "API connection failed"

    log = SyncLog(
        id=2,
        school_id=8,
        timestamp=datetime.now(),
        status="error",
        error_message=error
    )

    assert log.status == "error"
    assert log.error_message == error


def test_get_sync_logs_for_school():
    db = MagicMock()

    expected_logs = [
        SyncLog(
            id=1,
            school_id=8,
            timestamp=datetime.now(),
            status="success",
            error_message=None
        )
    ]

    query = db.query.return_value
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = expected_logs

    result = get_sync_logs_for_school(db, 8, limit=50)

    assert len(result) == 1
    assert result[0].school_id == 8
    assert result[0].status == "success"


def test_get_sync_logs_when_none_exist():
    db = MagicMock()

    query = db.query.return_value
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = []

    result = get_sync_logs_for_school(db, 8, limit=50)

    assert result == []


def test_get_sync_log_by_id():
    db = MagicMock()

    expected_log = SyncLog(
        id=3,
        school_id=8,
        timestamp=datetime.now(),
        status="error",
        error_message="Database connection failed"
    )

    query = db.query.return_value
    query.filter.return_value.first.return_value = expected_log

    result = get_sync_log_by_id(db, 3)

    assert result.id == 3
    assert result.status == "error"
    assert "Database connection failed" in result.error_message


def test_sync_log_not_found():
    db = MagicMock()

    query = db.query.return_value
    query.filter.return_value.first.return_value = None

    result = get_sync_log_by_id(db, 999)

    assert result is None