"""
CodeCraftHub - Course REST API

This Flask application provides CRUD operations for courses.

Data is stored in a local JSON file named courses.json.
No database or authentication is used.
"""

import json
from datetime import date, datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request


# Create the Flask application
app = Flask(__name__)


# Store courses.json in the same folder as this app.py file
DATA_FILE = Path(__file__).resolve().parent / "courses.json"


# Allowed values for the course status field
VALID_STATUSES = {
    "Not Started",
    "In Progress",
    "Completed",
}


# Required fields when creating or replacing a course
REQUIRED_FIELDS = {
    "name",
    "description",
    "target_date",
    "status",
}


def create_data_file_if_needed():
    """
    Create courses.json automatically if it does not already exist.

    The file starts with an empty JSON list because courses will be
    stored as a list of objects.
    """
    if not DATA_FILE.exists():
        with DATA_FILE.open("w", encoding="utf-8") as file:
            json.dump([], file, indent=4)


def read_courses():
    """
    Read and return all courses from courses.json.

    Returns:
        list: A list of course dictionaries.

    Raises:
        OSError: If the file cannot be read or created.
        ValueError: If the JSON data is invalid.
    """
    try:
        # Make sure the file exists before trying to read it
        create_data_file_if_needed()

        with DATA_FILE.open("r", encoding="utf-8") as file:
            courses = json.load(file)

        # The file should contain a JSON list
        if not isinstance(courses, list):
            raise ValueError("courses.json must contain a JSON list")

        return courses

    except json.JSONDecodeError as error:
        raise ValueError("courses.json contains invalid JSON") from error

    except OSError as error:
        raise OSError("Unable to read courses.json") from error


def write_courses(courses):
    """
    Save all courses to courses.json.

    Args:
        courses (list): The list of course dictionaries to save.

    Raises:
        OSError: If the file cannot be written.
    """
    try:
        with DATA_FILE.open("w", encoding="utf-8") as file:
            json.dump(courses, file, indent=4)

    except OSError as error:
        raise OSError("Unable to write to courses.json") from error


def error_response(message, status_code):
    """
    Return a consistent JSON error response.

    Example:
        {
            "error": "Course not found"
        }
    """
    return jsonify({"error": message}), status_code


def validate_course_data(data):
    """
    Validate the fields provided for a course.

    This function checks:
    - Required fields are present
    - Required fields contain text
    - target_date uses YYYY-MM-DD format
    - status has an allowed value

    Args:
        data (dict): Course data received from the request.

    Returns:
        str or None: An error message if invalid, otherwise None.
    """
    if not isinstance(data, dict):
        return "Request body must be a JSON object"

    # Find any required fields that are missing
    missing_fields = REQUIRED_FIELDS - data.keys()

    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        return f"Missing required field(s): {missing}"

    # Check that text fields are strings and are not empty
    for field in ["name", "description", "target_date", "status"]:
        if not isinstance(data[field], str) or not data[field].strip():
            return f"{field} is required and must be a non-empty string"

    # Check that target_date uses the YYYY-MM-DD format
    try:
        parsed_date = date.fromisoformat(data["target_date"])

        # Make sure the input is exactly YYYY-MM-DD.
        # For example, this rejects values with time information.
        if parsed_date.isoformat() != data["target_date"]:
            return "target_date must use YYYY-MM-DD format"

    except ValueError:
        return "target_date must use YYYY-MM-DD format"

    # Check that status is one of the allowed values
    if data["status"] not in VALID_STATUSES:
        valid_values = ", ".join(sorted(VALID_STATUSES))
        return f"Invalid status. Must be one of: {valid_values}"

    return None


def get_next_course_id(courses):
    """
    Generate the next course ID.

    IDs start at 1. If there are no courses, the next ID is 1.
    Otherwise, the next ID is one greater than the largest existing ID.
    """
    if not courses:
        return 1

    existing_ids = [
        course.get("id", 0)
        for course in courses
        if isinstance(course.get("id"), int)
    ]

    if not existing_ids:
        return 1

    return max(existing_ids) + 1


@app.route("/api/courses", methods=["POST"])
def add_course():
    """
    Add a new course.

    Endpoint:
        POST /api/courses
    """
    try:
        # Get JSON data from the request body
        data = request.get_json(silent=True)

        # Validate the submitted course information
        validation_error = validate_course_data(data)

        if validation_error:
            return error_response(validation_error, 400)

        courses = read_courses()

        # Build the new course object
        new_course = {
            "id": get_next_course_id(courses),
            "name": data["name"].strip(),
            "description": data["description"].strip(),
            "target_date": data["target_date"],
            "status": data["status"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Add the new course and save the updated list
        courses.append(new_course)
        write_courses(courses)

        return jsonify(new_course), 201

    except (OSError, ValueError) as error:
        return error_response(str(error), 500)


@app.route("/api/courses", methods=["GET"])
def get_all_courses():
    """
    Return all courses.

    Endpoint:
        GET /api/courses
    """
    try:
        courses = read_courses()
        return jsonify(courses), 200

    except (OSError, ValueError) as error:
        return error_response(str(error), 500)


@app.route("/api/courses/<int:course_id>", methods=["GET"])
def get_course(course_id):
    """
    Return one course by ID.

    Endpoint:
        GET /api/courses/<id>
    """
    try:
        courses = read_courses()

        # Search for a course whose ID matches the URL ID
        course = next(
            (course for course in courses if course.get("id") == course_id),
            None,
        )

        if course is None:
            return error_response("Course not found", 404)

        return jsonify(course), 200

    except (OSError, ValueError) as error:
        return error_response(str(error), 500)


@app.route("/api/courses/<int:course_id>", methods=["PUT"])
def update_course(course_id):
    """
    Replace an existing course.

    The id and created_at fields are kept from the original course.
    The other course fields must be provided in the request.

    Endpoint:
        PUT /api/courses/<id>
    """
    try:
        data = request.get_json(silent=True)

        # PUT replaces the course, so all required course fields are needed
        validation_error = validate_course_data(data)

        if validation_error:
            return error_response(validation_error, 400)
            
        courses = read_courses()

        # Find the course to update
        course = next(
            (course for course in courses if course.get("id") == course_id),
            None,
        )

        if course is None:
            return error_response("Course not found", 404)

        # Update only the editable fields
        course["name"] = data["name"].strip()
        course["description"] = data["description"].strip()
        course["target_date"] = data["target_date"]
        course["status"] = data["status"]

        # Save the updated course list
        write_courses(courses)

        return jsonify(course), 200

    except (OSError, ValueError) as error:
        return error_response(str(error), 500)


@app.route("/api/courses/<int:course_id>", methods=["DELETE"])
def delete_course(course_id):
    """
    Delete a course by ID.

    Endpoint:
        DELETE /api/courses/<id>
    """
    try:
        courses = read_courses()

        # Find the course to delete
        course = next(
            (course for course in courses if course.get("id") == course_id),
            None,
        )

        if course is None:
            return error_response("Course not found", 404)

        # Keep every course except the one being deleted
        remaining_courses = [
            course for course in courses
            if course.get("id") != course_id
        ]

        write_courses(remaining_courses)

        return jsonify({
            "message": "Course deleted successfully",
            "id": course_id,
        }), 200

    except (OSError, ValueError) as error:
        return error_response(str(error), 500)


@app.errorhandler(404)
def handle_404(error):
    """
    Handle requests to routes that do not exist.
    """
    return error_response("Endpoint not found", 404)


@app.errorhandler(405)
def handle_405(error):
    """
    Handle HTTP methods that are not supported by an endpoint.
    """
    return error_response("HTTP method not allowed", 405)


if __name__ == "__main__":
    # Create courses.json when the application starts.
    # If the file already exists, it will not be overwritten.
    try:
        create_data_file_if_needed()
        print(f"Using course data file: {DATA_FILE}")

    except OSError as error:
        print(f"Could not create courses.json: {error}")
        raise

    # debug=True is useful during development.
    # Set debug=False when deploying the application.
    app.run(debug=True,port=5001)