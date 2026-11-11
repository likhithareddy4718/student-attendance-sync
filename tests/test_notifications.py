import pytest
from datetime import date
from unittest.mock import MagicMock, patch

from services.student_parent_matcher import (
    calculate_name_similarity,
    find_best_parent_match,
    match_students_to_parents
)
from services.message_formatter import MessageFormatter
from services.notification_validator import (
    validate_notification_safe_to_send
)
from services.deduplication import DeduplicationChecker


# Student-parent matching tests

def test_name_similarity():
    score = calculate_name_similarity(
        "Alice Johnson",
        "alice johnson"
    )
    assert score == 1.0


def test_find_best_parent_match():
    parents = [
        {
            "id": 5,
            "name": "Ramesh Kumar",
            "email": "ramesh@example.com",
            "phone": "9876543210"
        }
    ]

    parent, confidence = find_best_parent_match(
        "Alice",
        "Ramesh Kumar",
        "ramesh@example.com",
        "9876543210",
        parents
    )

    assert parent["id"] == 5
    assert confidence >= 0.6


def test_students_to_parents_matching():
    csv_rows = [
        {
            "student_name": "Alice Johnson",
            "parent_name": "Ramesh Kumar",
            "parent_email": "ramesh@example.com",
            "parent_phone": "9876543210"
        }
    ]

    students = [
        {
            "id": 10,
            "name": "Alice Johnson",
            "school_id": 8
        }
    ]

    parents = [
        {
            "id": 5,
            "name": "Ramesh Kumar",
            "email": "ramesh@example.com",
            "phone": "9876543210"
        }
    ]

    result = match_students_to_parents(
        csv_rows, students, parents
    )

    assert len(result) == 1
    assert result[0]["status"] == "matched"
    assert result[0]["student_id"] == 10
    assert result[0]["parent_id"] == 5


def test_student_not_found():
    result = match_students_to_parents(
        [{
            "student_name": "Unknown Student",
            "parent_name": "Ramesh",
            "parent_email": "ramesh@example.com",
            "parent_phone": "9876543210"
        }],
        [],
        []
    )

    assert result[0]["status"] == "no_student_found"


# Notification message tests

def test_email_message_format():
    formatter = MessageFormatter("ABC School")

    absence = {
        "student_name": "Alice",
        "parent_name": "Ramesh",
        "date": date(2024, 1, 15),
        "reason": "Not specified"
    }

    message = formatter.format_email(absence)

    assert "subject" in message
    assert "body" in message
    assert "Alice" in message["subject"]
    assert "Ramesh" in message["body"]
    assert "ABC School" in message["body"]


def test_sms_message_format():
    formatter = MessageFormatter("ABC School")

    absence = {
        "student_name": "Alice",
        "date": date(2024, 1, 15),
        "reason": "Not specified"
    }

    message = formatter.format_sms(absence)

    assert "Alice" in message
    assert "ABC School" in message
    assert "STOP" in message


def test_notification_message_validation():
    formatter = MessageFormatter()

    assert formatter.validate_message("Attendance alert") is True
    assert formatter.validate_message("") is False


# Notification safety validation tests

@patch("services.notification_validator.validate_student_parent_pair")
@patch("services.notification_validator.validate_parent_contact_exists")
def test_notification_allowed_for_valid_match(
    mock_contact,
    mock_pair
):
    mock_pair.return_value = (True, "Pair verified")
    mock_contact.return_value = (True, "Contact available")

    valid, reason = validate_notification_safe_to_send(
        10, 5, "email"
    )

    assert valid is True
    assert "safe to send" in reason.lower()


@patch("services.notification_validator.validate_student_parent_pair")
@patch("services.notification_validator.validate_parent_contact_exists")
def test_notification_blocked_for_invalid_match(
    mock_contact,
    mock_pair
):
    mock_pair.return_value = (False, "No confirmed student-parent link")

    valid, reason = validate_notification_safe_to_send(
        10, 5, "email"
    )

    assert valid is False
    assert "No confirmed" in reason
    mock_contact.assert_not_called()


# Notification duplicate-check tests

def test_notification_not_sent_previously():
    db = MagicMock()
    cursor = db.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = {"count": 0}

    checker = DeduplicationChecker(db)

    result = checker.has_notification_been_sent(
        10, 5, "2026-11-09"
    )

    assert result is False


def test_duplicate_notification_detected():
    db = MagicMock()
    cursor = db.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = {"count": 1}

    checker = DeduplicationChecker(db)

    result = checker.has_notification_been_sent(
        10, 5, "2026-11-09"
    )

    assert result is True