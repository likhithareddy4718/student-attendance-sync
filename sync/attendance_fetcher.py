
import os
import requests
from datetime import datetime
from typing import List, Dict, Any


def fetch_attendance_from_api(
    school_id: int,
    api_endpoint: str = "",
    api_key: str = ""
) -> List[Dict[str, Any]]:

    # Demo mode: return sample attendance records
    if os.getenv("DEMO_MODE", "false").lower() == "true":

        today = datetime.now().strftime("%Y-%m-%d")

        demo_records = [
            {
                "student_name": "Test Student",
                "date": today,
                "status": "present"
            },
            {
                "student_name": "Rahul Sharma",
                "date": today,
                "status": "absent"
            },
            {
                "student_name": "Priya Reddy",
                "date": today,
                "status": "present"
            },
            {
                "student_name": "Arjun Kumar",
                "date": today,
                "status": "late"
            },
            {
                "student_name": "Sneha Patel",
                "date": today,
                "status": "present"
            },
            {
                "student_name": "Ananya Singh",
                "date": today,
                "status": "absent"
            }
        ]

        print(f"DEMO MODE: Generated {len(demo_records)} sample records")
        return demo_records

    # Real API mode
    timeout = int(os.getenv("API_TIMEOUT", "30"))

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(
            api_endpoint,
            headers=headers,
            timeout=timeout
        )

        response.raise_for_status()
        records = response.json()

        if not isinstance(records, list):
            records = records.get("data", [])

        return records

    except requests.exceptions.RequestException as e:
        print(f"API fetch error for school {school_id}: {e}")
        return []

    except ValueError:
        print(f"Invalid JSON returned by school {school_id}")
        return []
