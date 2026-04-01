import json
from flask import (
    Flask,
    make_response,
    jsonify,
    render_template,
    send_from_directory,
    send_file,
)
import os
import requests
import dotenv
import csv
from io import StringIO
from datetime import date, datetime

dotenv.load_dotenv()


def load_schedule_data():
    """Load schedule data from Google Sheets or fallback to JSON file"""
    # Try to load from Google Sheets first
    google_sheet_url = os.getenv("GOOGLE_SHEET_URL")

    if google_sheet_url:
        try:
            # Convert Google Sheets URL to CSV export URL
            if "/edit" in google_sheet_url:
                csv_url = google_sheet_url.replace(
                    "/edit#gid=", "/export?format=csv&gid="
                )
                csv_url = csv_url.replace("/edit", "/export?format=csv")
            else:
                csv_url = google_sheet_url

            print(f"Fetching schedule from Google Sheets: {csv_url}")

            response = requests.get(csv_url, timeout=10)
            response.raise_for_status()

            # Parse CSV data
            csv_data = StringIO(response.text)
            reader = csv.DictReader(csv_data)

            schedule = []
            for row in reader:
                # Map CSV columns to our expected format
                leaders_str = row.get("Leaders", "").strip()
                # Expected columns: Date, Primary Leader, Secondary Leader, Topic
                schedule_item = {
                    "date": row.get("Date", "").strip(),
                    "leaders": [leader for leader in leaders_str.split(", ") if leader]
                    if leaders_str
                    else [],
                    "topic": row.get("Topic", "").strip(),
                }

                # Only add rows that have at least a date and topic
                if schedule_item["date"] and schedule_item["topic"]:
                    schedule.append(schedule_item)

            print(f"Successfully loaded {len(schedule)} items from Google Sheets")
            return schedule

        except requests.RequestException as e:
            print(f"Error fetching from Google Sheets: {e}")
        except Exception as e:
            print(f"Error parsing Google Sheets data: {e}")

    # Fallback to JSON file
    try:
        with open("schedule_data.json", "r") as f:
            data = json.load(f)
            print("Loaded schedule from local JSON file")
            return data.get("schedule", [])
    except FileNotFoundError:
        print("Warning: schedule_data.json not found. Using empty schedule.")
        return []
    except json.JSONDecodeError:
        print("Warning: Invalid JSON in schedule_data.json. Using empty schedule.")
        return []


# Load schedule data from JSON file
SCHEDULE_DATA = load_schedule_data()

app = Flask(__name__)


def parse_schedule_date(raw_date: str) -> date | None:
    """Parse a schedule date string using common formats."""
    if not raw_date:
        return None

    cleaned = raw_date.strip()

    # Try ISO date first.
    try:
        return date.fromisoformat(cleaned)
    except ValueError:
        pass

    formats = [
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d/%m/%y",
        "%m/%d/%y",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%a %d %b %Y",
        "%A %d %B %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue

    month_day_formats = [
        "%B %d",
        "%b %d",
        "%B %d,",
        "%b %d,",
    ]

    current_year = date.today().year
    for fmt in month_day_formats:
        try:
            # Add current year to the end of the string for parsing
            date_str_with_year = f"{cleaned} {current_year}"
            return datetime.strptime(date_str_with_year, fmt + " %Y").date()
        except ValueError:
            continue

    return None


def find_upcoming_week_index(schedule: list[dict]) -> int | None:
    """Return the index of the next schedule item that is today or later."""
    today = date.today()
    for index, item in enumerate(schedule):
        parsed_date = parse_schedule_date(item.get("date", ""))
        if parsed_date and parsed_date >= today:
            return index
    return None


def find(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)


# Assets routes
@app.route("/assets/<path:path>")
def send_assets(path):
    if path.endswith(".json"):
        return send_from_directory(
            "templates/assets", path, mimetype="application/json"
        )

    if os.path.isfile("templates/assets/" + path):
        return send_from_directory("templates/assets", path)

    # Try looking in one of the directories
    filename: str = path.split("/")[-1]
    if (
        filename.endswith(".png")
        or filename.endswith(".jpg")
        or filename.endswith(".jpeg")
        or filename.endswith(".svg")
    ):
        if os.path.isfile("templates/assets/img/" + filename):
            return send_from_directory("templates/assets/img", filename)
        if os.path.isfile("templates/assets/img/favicon/" + filename):
            return send_from_directory("templates/assets/img/favicon", filename)

    return render_template("404.html"), 404


# region Special routes
@app.route("/favicon.png")
def faviconPNG():
    return send_from_directory("templates/assets/img", "favicon.png")


@app.route("/.well-known/<path:path>")
def wellknown(path):
    # Try to proxy to https://nathan.woodburn.au/.well-known/
    req = requests.get(f"https://nathan.woodburn.au/.well-known/{path}")
    return make_response(
        req.content, 200, {"Content-Type": req.headers["Content-Type"]}
    )


# endregion


# region Main routes
@app.route("/")
def index():
    upcoming_week_index = find_upcoming_week_index(SCHEDULE_DATA)
    return render_template(
        "schedule.html",
        schedule=SCHEDULE_DATA,
        upcoming_week_index=upcoming_week_index,
    )


@app.route("/<path:path>")
def catch_all(path: str):
    if os.path.isfile("templates/" + path):
        return render_template(path)

    # Try with .html
    if os.path.isfile("templates/" + path + ".html"):
        return render_template(path + ".html")

    if os.path.isfile("templates/" + path.strip("/") + ".html"):
        return render_template(path.strip("/") + ".html")

    # Try to find a file matching
    if path.count("/") < 1:
        # Try to find a file matching
        filename = find(path, "templates")
        if filename:
            return send_file(filename)

    return render_template("404.html"), 404


# endregion


# region API routes


@app.route("/api/v1/schedule", methods=["GET"])
def api_schedule():
    """
    API endpoint that returns the weekly schedule data.
    """
    # Always reload data in case Google Sheet has been updated
    current_schedule = load_schedule_data()
    # Set the global variable to the latest data
    global SCHEDULE_DATA
    SCHEDULE_DATA = current_schedule
    return jsonify({"schedule": current_schedule})


@app.route("/api/v1/status")
def api_status():
    """
    API endpoint that returns the status of the server.
    """
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


# endregion


# region Error Catching
# 404 catch all
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


# endregion
if __name__ == "__main__":
    app.run(debug=True, port=5000, host="127.0.0.1")
