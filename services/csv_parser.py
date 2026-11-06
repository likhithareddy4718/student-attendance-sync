
import csv
import io
from typing import List, Dict, Tuple
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Custom CSV parsing error
class CSVParseError(Exception):
    """Raised when CSV parsing fails."""
    pass


# ------------------------------------------
# PART 1: PARSE CSV FILE
# ------------------------------------------

def parse_csv_file(file_stream) -> List[Dict[str, str]]:
    """
    Parse a CSV file and return a list of dictionaries.

    Each row becomes one dictionary with column names as keys.

    Args:
        file_stream: A file-like object from Flask request.files.

    Returns:
        List of dictionaries, one per row.

    Raises:
        CSVParseError: If CSV is empty, invalid or too large.
    """

    max_rows = int(os.getenv('MAX_CSV_ROWS', 1000))

    try:
        # Read uploaded file and convert bytes into text
        content = file_stream.read().decode('utf-8')

    except UnicodeDecodeError:
        raise CSVParseError(
            "File must be UTF-8 encoded. "
            "Try saving as CSV (UTF-8) in Excel."
        )

    # Check empty file
    if not content.strip():
        raise CSVParseError("CSV file is empty.")

    # Parse CSV data
    try:
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)

    except Exception as e:
        raise CSVParseError(
            f"Could not read CSV: {str(e)}"
        )

    # Check whether data rows exist
    if not rows:
        raise CSVParseError(
            "CSV has no data rows (only headers or completely empty)."
        )

    # Check maximum row limit
    if len(rows) > max_rows:
        raise CSVParseError(
            f"CSV has {len(rows)} rows, but maximum is {max_rows}."
        )

    return rows


# ------------------------------------------
# PART 2: VALIDATE STUDENT-PARENT CSV
# ------------------------------------------

def validate_student_parent_csv(
    rows: List[Dict[str, str]]
) -> Tuple[bool, str, List[Dict[str, str]]]:
    """
    Validate student and parent information.

    Required columns:
        student_name
        parent_name

    At least one contact field is required:
        parent_email or parent_phone

    Returns:
        Tuple of (is_valid, error_message, cleaned_rows)
    """

    required_columns = {
        'student_name',
        'parent_name'
    }

    contact_columns = {
        'parent_email',
        'parent_phone'
    }

    # Check whether rows exist
    if not rows:
        return False, "No rows to validate.", []

    # Get CSV headers
    first_row_keys = set(rows[0].keys())

    # Validate required columns
    if not required_columns.issubset(first_row_keys):

        missing = required_columns - first_row_keys

        return (
            False,
            f"Missing required columns: {', '.join(missing)}. "
            "Expected: student_name, parent_name, "
            "parent_email, parent_phone",
            []
        )

    # Check at least one contact column exists
    if not contact_columns.intersection(first_row_keys):

        return (
            False,
            "At least one of 'parent_email' or "
            "'parent_phone' must be present.",
            []
        )

    # Validate individual rows
    cleaned_rows = []
    errors = []

    for idx, row in enumerate(rows, start=2):

        student_name = (
            row.get('student_name') or ''
        ).strip()

        parent_name = (
            row.get('parent_name') or ''
        ).strip()

        parent_email = (
            row.get('parent_email') or ''
        ).strip()

        parent_phone = (
            row.get('parent_phone') or ''
        ).strip()

        # Check student name
        if not student_name:
            errors.append(
                f"Row {idx}: student_name is empty."
            )
            continue

        # Check parent name
        if not parent_name:
            errors.append(
                f"Row {idx}: parent_name is empty."
            )
            continue

        # Check contact information
        if not parent_email and not parent_phone:
            errors.append(
                f"Row {idx}: at least one of "
                "parent_email or parent_phone must be filled."
            )
            continue

        # Add cleaned record
        cleaned_rows.append({
            'student_name': student_name,
            'parent_name': parent_name,
            'parent_email': parent_email,
            'parent_phone': parent_phone
        })

    # Return validation errors
    if errors:

        error_msg = (
            "Validation errors:\n"
            + "\n".join(errors[:5])
        )

        if len(errors) > 5:
            error_msg += (
                f"\n... and {len(errors) - 5} more."
            )

        return False, error_msg, []

    # All rows are valid
    return True, "", cleaned_rows
