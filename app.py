"""
Dropbox rclone config generator web app.

Allows multiple users to simultaneously create their own rclone configs
using their own Dropbox app client IDs and secrets via OAuth2.
"""

import json
import os
import secrets
from urllib.parse import urlencode

import requests
from flask import (
    Flask,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(__name__)

# Secret key for signing session cookies. In production, set the
# SECRET_KEY environment variable to a long, random string.
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

DROPBOX_AUTH_URL = "https://www.dropbox.com/oauth2/authorize"
DROPBOX_TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"


@app.route("/", methods=["GET"])
def index():
    callback_url = url_for("callback", _external=True)
    return render_template("index.html", callback_url=callback_url)


@app.route("/start", methods=["POST"])
def start():
    client_id = request.form.get("client_id", "").strip()
    client_secret = request.form.get("client_secret", "").strip()

    if not client_id or not client_secret:
        return render_template(
            "error.html",
            message="Both Client ID and Client Secret are required.",
        )

    # Generate a unique state token to tie this OAuth flow to this session
    # and prevent CSRF attacks.
    state = secrets.token_urlsafe(32)

    # Store credentials and state in the signed session cookie so that each
    # concurrent user has their own isolated state.
    session["client_id"] = client_id
    session["client_secret"] = client_secret
    session["oauth_state"] = state

    # Build the redirect URI based on the current request's base URL so the
    # app works regardless of where it is deployed.
    redirect_uri = url_for("callback", _external=True)

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "token_access_type": "offline",  # request a refresh token
    }

    auth_url = f"{DROPBOX_AUTH_URL}?{urlencode(params)}"
    return redirect(auth_url)


@app.route("/callback")
def callback():
    error = request.args.get("error")
    if error:
        error_description = request.args.get("error_description", error)
        return render_template("error.html", message=error_description)

    code = request.args.get("code")
    returned_state = request.args.get("state")

    # Validate state to prevent CSRF
    expected_state = session.get("oauth_state")
    if not expected_state or returned_state != expected_state:
        return render_template(
            "error.html",
            message="Invalid or expired session. Please start over.",
        )

    client_id = session.get("client_id")
    client_secret = session.get("client_secret")

    if not client_id or not client_secret:
        return render_template(
            "error.html",
            message="Session data missing. Please start over.",
        )

    redirect_uri = url_for("callback", _external=True)

    # Exchange the authorization code for tokens
    try:
        resp = requests.post(
            DROPBOX_TOKEN_URL,
            data={
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
            auth=(client_id, client_secret),
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        app.logger.error("Token exchange failed: %s", exc)
        return render_template(
            "error.html",
            message=(
                "Failed to connect to Dropbox. "
                "Please check your credentials and try again."
            ),
        )

    token_data = resp.json()

    if "error" in token_data:
        return render_template(
            "error.html",
            message=token_data.get("error_description", token_data["error"]),
        )

    # Build the rclone token JSON that rclone expects
    rclone_token = json.dumps(
        {
            "access_token": token_data.get("access_token", ""),
            "token_type": token_data.get("token_type", "bearer"),
            "refresh_token": token_data.get("refresh_token", ""),
            "expiry": "0001-01-01T00:00:00Z",
        }
    )

    config = (
        "[dropbox]\n"
        "type = dropbox\n"
        f"client_id = {client_id}\n"
        f"client_secret = {client_secret}\n"
        f"token = {rclone_token}\n"
    )

    # Clear sensitive session data after successful use
    session.clear()

    return render_template("success.html", config=config)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
