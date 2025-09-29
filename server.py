from functools import cache
import json
from flask import (
    Flask,
    make_response,
    redirect,
    request,
    jsonify,
    render_template,
    send_from_directory,
    send_file,
)
import os
import json
import requests
from datetime import datetime
import dotenv

dotenv.load_dotenv()

def load_schedule_data():
    """Load schedule data from JSON file"""
    try:
        with open('schedule_data.json', 'r') as f:
            data = json.load(f)
            return data.get('schedule', [])
    except FileNotFoundError:
        print("Warning: schedule_data.json not found. Using empty schedule.")
        return []
    except json.JSONDecodeError:
        print("Warning: Invalid JSON in schedule_data.json. Using empty schedule.")
        return []

# Load schedule data from JSON file
SCHEDULE_DATA = load_schedule_data()

app = Flask(__name__)


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
    return render_template("schedule.html", schedule=SCHEDULE_DATA)


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

api_requests = 0

@app.route("/api/v1/data", methods=["GET"])
def api_data():
    """
    Example API endpoint that returns some data.
    You can modify this to return whatever data you need.
    """

    global api_requests
    api_requests += 1

    data = {
        "header": "Sample API Response",
        "content": f"Hello, this is a sample API response! You have called this endpoint {api_requests} times.",
        "timestamp": datetime.now().isoformat(),
    }
    return jsonify(data)


@app.route("/api/v1/schedule", methods=["GET"])
def api_schedule():
    """
    API endpoint that returns the weekly schedule data.
    """
    # Reload data in case file has been updated
    current_schedule = load_schedule_data()
    return jsonify({"schedule": current_schedule})

# endregion


# region Error Catching
# 404 catch all
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


# endregion
if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")
