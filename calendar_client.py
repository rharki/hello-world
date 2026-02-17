from datetime import datetime, timezone

import google.oauth2.credentials
from googleapiclient.discovery import build


def get_credentials(session):
    """Reconstruct a Credentials object from Flask session data."""
    if "credentials" not in session:
        return None
    return google.oauth2.credentials.Credentials(**session["credentials"])


def fetch_upcoming_events(credentials, max_results=20):
    """Fetch upcoming events from the user's primary calendar."""
    service = build("calendar", "v3", credentials=credentials)

    now = datetime.now(timezone.utc).isoformat()

    events_result = service.events().list(
        calendarId="primary",
        timeMin=now,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    return events_result.get("items", [])


def fetch_event(credentials, event_id):
    """Fetch a single event by ID."""
    service = build("calendar", "v3", credentials=credentials)
    return service.events().get(calendarId="primary", eventId=event_id).execute()


def summarize_event(event):
    """Extract the fields we care about from a raw Calendar API event."""
    start = event["start"].get("dateTime", event["start"].get("date", ""))
    end = event["end"].get("dateTime", event["end"].get("date", ""))
    return {
        "id": event["id"],
        "summary": event.get("summary", "(No title)"),
        "description": event.get("description", ""),
        "location": event.get("location", ""),
        "start": start,
        "end": end,
        "attendees": [
            a.get("email", "") for a in event.get("attendees", [])
        ],
        "organizer": event.get("organizer", {}).get("email", ""),
        "html_link": event.get("htmlLink", ""),
    }
