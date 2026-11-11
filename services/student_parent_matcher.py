
from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher


# Custom matching error
class MatchingError(Exception):
    """Raised when matching logic fails."""
    pass


# --------------------------------------------------
# PART 1: CALCULATE NAME SIMILARITY
# --------------------------------------------------

def calculate_name_similarity(
    name1: str,
    name2: str
) -> float:
    """
    Compare two names and return a score from 0 to 1.

    1.0 means identical.
    0.0 means completely different.
    """

    name1_clean = (name1 or "").lower().strip()
    name2_clean = (name2 or "").lower().strip()

    matcher = SequenceMatcher(
        None,
        name1_clean,
        name2_clean
    )

    return matcher.ratio()


# --------------------------------------------------
# PART 2: FIND BEST MATCHING PARENT
# --------------------------------------------------

def find_best_parent_match(
    student_name: str,
    parent_name_from_csv: str,
    parent_email_from_csv: str,
    parent_phone_from_csv: str,
    existing_parents: List[Dict]
) -> Tuple[Optional[Dict], float]:
    """
    Find the best matching parent from existing database records.

    Matching scores:
    Name similarity: 50%
    Exact email match: 25%
    Exact phone match: 25%

    Returns:
        (best_parent, confidence_score)
    """

    # Minimum score required for a match
    name_threshold = 0.6

    best_match = None
    best_score = 0.0

    for existing_parent in existing_parents:

        score = 0.0

        # Score 1: Name similarity (50%)

        name_sim = calculate_name_similarity(
            parent_name_from_csv,
            existing_parent.get("name", "")
        )

        score += name_sim * 0.5

        # Score 2: Exact email match (25%)

        existing_email = (
            existing_parent.get("email") or ""
        ).lower().strip()

        csv_email = (
            parent_email_from_csv or ""
        ).lower().strip()

        if csv_email and existing_email:

            if csv_email == existing_email:
                score += 0.25

        # Score 3: Exact phone match (25%)

        existing_phone = (
            existing_parent.get("phone") or ""
        ).strip()

        csv_phone = (
            parent_phone_from_csv or ""
        ).strip()

        if csv_phone and existing_phone:

            if csv_phone == existing_phone:
                score += 0.25

        # Update the best match

        if score > best_score:

            best_score = score
            best_match = existing_parent

    # Check minimum confidence threshold

    if best_score >= name_threshold:

        return best_match, best_score

    return None, best_score


# --------------------------------------------------
# PART 3: MATCH STUDENTS WITH PARENTS
# --------------------------------------------------

def match_students_to_parents(
    csv_rows: List[Dict[str, str]],
    existing_students: List[Dict],
    existing_parents: List[Dict]
) -> List[Dict]:
    """
    Match each student from CSV with a database student
    and find the best matching parent.

    Returns a list of proposed matches with confidence scores.

    Status values:
        matched
        no_student_found
        no_parent_found
    """

    matches = []

    for row in csv_rows:

        student_name = (
            row.get("student_name") or ""
        ).strip()

        parent_name = (
            row.get("parent_name") or ""
        ).strip()

        parent_email = (
            row.get("parent_email") or ""
        ).strip()

        parent_phone = (
            row.get("parent_phone") or ""
        ).strip()

        # ------------------------------------------
        # STEP 1: FIND STUDENT IN DATABASE
        # ------------------------------------------

        student_match = None

        for existing_student in existing_students:

            similarity = calculate_name_similarity(
                student_name,
                existing_student.get("name", "")
            )

            if similarity > 0.8:

                student_match = existing_student
                break

        # Student not found

        if not student_match:

            matches.append({

                "student_id": None,

                "student_name": student_name,

                "parent_id": None,

                "parent_name": parent_name,

                "parent_email": parent_email,

                "parent_phone": parent_phone,

                "confidence": 0.0,

                "status": "no_student_found"

            })

            continue

        # ------------------------------------------
        # STEP 2: FIND BEST MATCHING PARENT
        # ------------------------------------------

        parent_match, confidence = find_best_parent_match(

            student_name,

            parent_name,

            parent_email,

            parent_phone,

            existing_parents

        )

        # Parent not found or confidence too low

        if not parent_match:

            matches.append({

                "student_id": student_match["id"],

                "student_name": student_name,

                "parent_id": None,

                "parent_name": parent_name,

                "parent_email": parent_email,

                "parent_phone": parent_phone,

                "confidence": confidence,

                "status": "no_parent_found"

            })

            continue

        # ------------------------------------------
        # STEP 3: BOTH STUDENT AND PARENT FOUND
        # ------------------------------------------

        matches.append({

            "student_id": student_match["id"],

            "student_name": student_name,

            "parent_id": parent_match["id"],

            "parent_name": parent_name,

            "parent_email": parent_email,

            "parent_phone": parent_phone,

            "confidence": confidence,

            "status": "matched"

        })

    return matches
