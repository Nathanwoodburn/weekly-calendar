# Weekly Calendar

Flask app for displaying a weekly Bible study schedule, with optional Google Sheets integration and an automatic upcoming-week highlight.

## Features

- Renders schedule entries with date, leaders, and topic
- Highlights the next upcoming week automatically
- Supports theme switching in the UI
- Loads schedule data from Google Sheets CSV export or local fallback JSON
- Provides an API endpoint for schedule data

## Requirements

- Python 3.13+ (recommended)

## Local Development

1. Install dependencies using UV

```bash
uv sync
```

2. Start the development server:

```bash
uv run main.py
```

3. Open:

```text
http://127.0.0.1:5000
```

## Production Run

Run with Gunicorn via the included launcher:

```bash
uv run main.py
```

Default bind address is `0.0.0.0:5000`.

## Configuration

Use a `.env` file or environment variables.

- `GOOGLE_SHEET_URL`: Optional. If set, schedule data is fetched from Google Sheets.
- `WORKERS`: Optional Gunicorn worker count (default: `1`).
- `THREADS`: Optional Gunicorn thread count (default: `2`).

If `GOOGLE_SHEET_URL` is not set or fetch/parsing fails, the app falls back to `schedule_data.json` if present.

## Google Sheets Data Format

Expected columns:

- `Date`
- `Leaders` (comma-separated names)
- `Topic`

Supported date formats include:

- `2026-04-07`
- `7/4/2026`, `04/07/2026`, `7-4-2026`
- `7 Apr 2026`, `April 7, 2026`
- `April 7` (current year inferred)

## API

- `GET /api/v1/schedule`

Response shape:

```json
{
	"schedule": [
		{
			"date": "April 7",
			"leaders": ["Alice", "Bob"],
			"topic": "Romans 8"
		}
	]
}
```

## Docker

Build and run:

```bash
docker build -t weekly-calendar .
docker run --rm -p 5000:5000 --env-file .env weekly-calendar
```

Built images are available at: `git.woodburn.au/nathanwoodburn/weekly-calendar:latest`