import pytest
from datetime import datetime, date

from sync.attendance_converter import (
    convert_record,
    load_status_map
)


@pytest.fixture
def status_map():
    """Load the attendance status mappings."""
    return load_status_map()


class TestDataConversion:
    """Test conversion of different school attendance formats."""

    def test_convert_school_a_format_to_standard(self, status_map):
        """Test School A attendance format."""

        raw_data = {
            "student_name": "Alice",
            "date": "2024-01-15",
            "status": "A"
        }

        result = convert_record(raw_data, 8, status_map)

        assert result == {
            "student_name": "Alice",
            "date": date(2024, 1, 15),
            "status": "absent",
            "school_id": 8
        }

    def test_convert_school_b_format_to_standard(self, status_map):
        """Test alternative field names and date format."""

        raw_data = {
            "name": " Bob ",
            "attendance_date": "15/01/2024",
            "attendance_status": "P"
        }

        result = convert_record(raw_data, 8, status_map)

        assert result == {
            "student_name": "Bob",
            "date": date(2024, 1, 15),
            "status": "present",
            "school_id": 8
        }

    def test_convert_school_c_format_to_standard(self, status_map):
        """Test another school's field names and date format."""

        raw_data = {
            "student": "Charlie",
            "recorded_date": "01/20/2024",
            "status": "L"
        }

        result = convert_record(raw_data, 8, status_map)

        assert result == {
            "student_name": "Charlie",
            "date": date(2024, 1, 20),
            "status": "late",
            "school_id": 8
        }

    def test_convert_datetime_string(self, status_map):
        """Test conversion of a date with timestamp."""

        raw_data = {
            "student_name": "David",
            "date": "2024-01-25 14:30:00",
            "status": "present"
        }

        result = convert_record(raw_data, 8, status_map)

        assert result["date"] == date(2024, 1, 25)
        assert result["status"] == "present"

    def test_convert_date_object(self, status_map):
        """Test conversion when date is already a date object."""

        raw_data = {
            "student_name": "Emma",
            "date": date(2024, 1, 26),
            "status": "absent"
        }

        result = convert_record(raw_data, 8, status_map)

        assert result["date"] == date(2024, 1, 26)
        assert result["status"] == "absent"

    def test_reject_invalid_records(self, status_map):
        """Test that incomplete and invalid records are rejected."""

        invalid_records = [
            None,
            {},
            {"date": "2024-01-15", "status": "P"},
            {"student_name": "Frank"},
            {
                "student_name": "George",
                "date": "invalid-date",
                "status": "A"
            }
        ]

        for record in invalid_records:
            result = convert_record(record, 8, status_map)
            assert result is None

    def test_unknown_and_missing_status(self, status_map):
        """Test unknown and missing attendance statuses."""

        unknown_record = {
            "student_name": "Harry",
            "date": "2024-01-27",
            "status": "XYZ"
        }

        missing_status_record = {
            "student_name": "Ivy",
            "date": "2024-01-28"
        }

        unknown_result = convert_record(
            unknown_record, 8, status_map
        )

        missing_result = convert_record(
            missing_status_record, 8, status_map
        )

        assert unknown_result["status"] == "unknown"
        assert missing_result["status"] == "unknown"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])