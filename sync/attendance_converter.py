
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime


def normalize_status(raw_status: str, status_map: Dict[str, str]) -> str:
    """
    Convert a school's status code to our standard format.
    """
    if not raw_status:
        return 'unknown'

    raw_status_lower = str(raw_status).strip().lower()

    if raw_status_lower in status_map:
        return status_map[raw_status_lower]

    if raw_status_lower in ['present', 'absent', 'late']:
        return raw_status_lower

    return 'unknown'


def load_status_map() -> Dict[str, str]:
    """
    Load the status mapping from the environment or use defaults.
    """
    default_map = {
        'a': 'absent',
        'abs': 'absent',
        'absent': 'absent',
        'p': 'present',
        'pres': 'present',
        'present': 'present',
        'l': 'late',
        'late': 'late'
    }

    env_map = os.getenv('ATTENDANCE_STATUS_MAP', '')

    if env_map:
        try:
            custom_map = json.loads(env_map)
            default_map.update(custom_map)
        except json.JSONDecodeError:
            print(f"[{datetime.now()}] Warning: ATTENDANCE_STATUS_MAP is not valid JSON, using defaults")

    return default_map


def convert_record(raw_record: Dict[str, Any], school_id: int, status_map: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """
    Convert a single raw attendance record from the school's API.

    Handles missing fields, unexpected data types and invalid dates.
    """
    if not isinstance(raw_record, dict):
        print(f"[{datetime.now()}] Skipping record from school {school_id}: not a dictionary")
        return None

    # Extract student name
    student_name = (
        raw_record.get('student_name') or
        raw_record.get('name') or
        raw_record.get('student') or
        ''
    )

    student_name = str(student_name).strip() if student_name else ''

    if not student_name:
        print(f"[{datetime.now()}] Skipping record from school {school_id}: no student name found")
        return None

    # Extract date
    date_value = (
        raw_record.get('date') or
        raw_record.get('attendance_date') or
        raw_record.get('recorded_date')
    )

    if not date_value:
        print(f"[{datetime.now()}] Skipping record for {student_name} from school {school_id}: no date found")
        return None

    # Parse the date
    try:
        if isinstance(date_value, str):
            for fmt in [
                '%Y-%m-%d',
                '%d/%m/%Y',
                '%m/%d/%Y',
                '%Y-%m-%d %H:%M:%S'
            ]:
                try:
                    parsed_date = datetime.strptime(date_value, fmt).date()
                    break
                except ValueError:
                    continue
            else:
                print(f"[{datetime.now()}] Skipping record for {student_name}: date '{date_value}' doesn't match known formats")
                return None
        else:
            parsed_date = date_value.date() if hasattr(date_value, 'date') else date_value

    except Exception as e:
        print(f"[{datetime.now()}] Skipping record for {student_name}: error parsing date: {e}")
        return None

    # Extract status
    raw_status = (
        raw_record.get('status') or
        raw_record.get('attendance_status') or
        ''
    )

    normalized_status = normalize_status(raw_status, status_map)

    # Build standardized record
    converted = {
        'student_name': student_name,
        'date': parsed_date,
        'status': normalized_status,
        'school_id': school_id
    }

    return converted
