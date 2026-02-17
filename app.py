import os
import functools
from datetime import datetime

import flask
from dotenv import load_dotenv
import google_auth_oauthlib.flow
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from calendar_client import get_credentials, fetch_upcoming_events, fetch_event, summarize_event
from ai_prep import generate_prep_todos

load_dotenv()

app = flask.Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

GOOGLE_CLIENT_CONFIG = {
    "web": {
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


# --- Helpers ---


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if "credentials" not in flask.session:
            return flask.redirect(flask.url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.template_filter("format_datetime")
def format_datetime_filter(value):
    """Format an ISO datetime string for display."""
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%a, %b %d at %I:%M %p")
    except ValueError:
        # All-day events use date-only format like "2025-01-15"
        return value


# --- Auth Routes ---


@app.route("/")
def index():
    if "credentials" in flask.session:
        return flask.redirect(flask.url_for("events"))
    return flask.redirect(flask.url_for("login"))


@app.route("/login")
def login():
    if "credentials" in flask.session:
        return flask.redirect(flask.url_for("events"))
    return flask.render_template("login.html")


@app.route("/authorize")
def authorize():
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        GOOGLE_CLIENT_CONFIG, scopes=SCOPES
    )
    flow.redirect_uri = flask.url_for("oauth2callback", _external=True)

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    flask.session["state"] = state
    return flask.redirect(authorization_url)


@app.route("/oauth2callback")
def oauth2callback():
    state = flask.session.get("state")

    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        GOOGLE_CLIENT_CONFIG, scopes=SCOPES, state=state
    )
    flow.redirect_uri = flask.url_for("oauth2callback", _external=True)

    flow.fetch_token(authorization_response=flask.request.url)

    credentials = flow.credentials
    flask.session["credentials"] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": list(credentials.scopes),
    }

    return flask.redirect(flask.url_for("events"))


@app.route("/logout")
def logout():
    flask.session.clear()
    return flask.redirect(flask.url_for("login"))


# --- App Routes ---


@app.route("/events")
@login_required
def events():
    creds = get_credentials(flask.session)
    upcoming = fetch_upcoming_events(creds, max_results=20)
    event_list = [summarize_event(e) for e in upcoming]
    return flask.render_template("events.html", events=event_list)


@app.route("/events/<event_id>")
@login_required
def event_detail(event_id):
    creds = get_credentials(flask.session)
    event = fetch_event(creds, event_id)
    event_data = summarize_event(event)

    cache_key = f"todos_{event_id}"

    # Clear old cached todos to keep session small
    for key in list(flask.session.keys()):
        if key.startswith("todos_") and key != cache_key:
            del flask.session[key]

    if cache_key in flask.session:
        todos = flask.session[cache_key]
    else:
        try:
            todos = generate_prep_todos(event_data)
        except Exception:
            todos = []
            flask.flash("Could not generate to-dos. Please try again.")
        flask.session[cache_key] = todos

    return flask.render_template("event_detail.html", event=event_data, todos=todos)


@app.route("/events/<event_id>/refresh", methods=["POST"])
@login_required
def refresh_todos(event_id):
    flask.session.pop(f"todos_{event_id}", None)
    return flask.redirect(flask.url_for("event_detail", event_id=event_id))


# --- Error Handlers ---


@app.errorhandler(RefreshError)
def handle_refresh_error(e):
    flask.session.clear()
    flask.flash("Your session expired. Please sign in again.")
    return flask.redirect(flask.url_for("login"))


@app.errorhandler(HttpError)
def handle_google_api_error(e):
    flask.flash(f"Google API error: {e}")
    return flask.redirect(flask.url_for("events"))


# --- Entry Point ---


if __name__ == "__main__":
    # Allow OAuth2 over HTTP for local development only
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    app.run(debug=True, port=5000)
