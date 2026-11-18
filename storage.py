import json
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "courses.json"


def load_courses():
    """Read all courses from the JSON file."""
    if not DATA_FILE.exists():
        return []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_courses(courses):
    """Write all courses to the JSON file."""
    DATA_FILE.parent.mkdir(exist_ok=True)

    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(courses, file, indent=2)