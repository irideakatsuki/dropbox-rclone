# dropbox-rclone

A Python web app that lets users generate their own **rclone Dropbox configs** using their own Dropbox app credentials. Multiple users can use the app simultaneously — each session is completely isolated.

## How it works

1. A user visits the app and enters their Dropbox **Client ID** (app key) and **Client Secret** (app secret).
2. The app redirects them to Dropbox to authorise access.
3. After authorisation, the app exchanges the code for tokens and generates a ready-to-use rclone config block.
4. The user copies the config into their rclone config file.

## Prerequisites

- Python 3.9+
- A Dropbox app ([App Console](https://www.dropbox.com/developers/apps))

## Dropbox app setup

1. Create an app in the [Dropbox App Console](https://www.dropbox.com/developers/apps).
2. Under **OAuth 2 → Redirect URIs**, add the callback URL for your deployment, e.g.:
   - Local development: `http://localhost:5000/callback`
   - Production: `https://your-domain.com/callback`
3. Note the **App key** (Client ID) and **App secret** (Client Secret).

## Running locally

```bash
pip install -r requirements.txt

# Optional but recommended in production:
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"

python app.py
# → http://localhost:5000
```

## Running with Gunicorn (recommended for production)

```bash
export SECRET_KEY="a-long-random-string"
export PORT=8080

gunicorn --bind 0.0.0.0:$PORT --workers 4 --threads 2 app:app
```

## Docker

```bash
docker build -t dropbox-rclone .
docker run -p 8080:8080 -e SECRET_KEY="a-long-random-string" dropbox-rclone
```

## Environment variables

| Variable     | Default              | Description                                       |
|--------------|----------------------|---------------------------------------------------|
| `SECRET_KEY` | random (per restart) | Secret key for signing session cookies. **Set this in production.** |
| `PORT`       | `5000`               | Port to listen on when running with `python app.py` |

> **Security note:** Set a stable `SECRET_KEY` in production. Without it, a new random key is generated on every process start, which:
> - Invalidates all existing sessions on restart.
> - Causes session validation failures when using multiple Gunicorn workers (each worker gets its own random key). This will break the OAuth flow for most users in a multi-worker setup.

## Concurrency

The app stores all per-user state in signed, server-side session cookies, so there is no shared mutable state between requests. It scales horizontally — run as many Gunicorn workers or container replicas as you need.
