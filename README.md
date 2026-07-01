# Videoflix Backend

A Netflix-style video streaming backend built with Django & Django REST Framework.
It handles user accounts (email-based, with email activation and JWT auth via
HttpOnly cookies), a video catalog, and adaptive HLS streaming. Uploaded videos
are transcoded to multiple resolutions in the background with FFmpeg.

---

## Features

- **Authentication** — registration with email activation, JWT login/logout via
  HttpOnly cookies, token refresh & blacklisting, password reset.
- **Custom user model** — users log in with their email address (no username).
- **Video catalog** — list endpoint with auto-generated thumbnails, ordered newest first.
- **Adaptive HLS streaming** — each upload is transcoded to 480p / 720p / 1080p and
  served as `.m3u8` playlists + `.ts` segments.
- **Background processing** — FFmpeg conversion runs in a Django RQ worker (Redis queue),
  so uploads return instantly.

## Tech stack

| Area | Technology                                              |
|------|---------------------------------------------------------|
| Language / Framework | Python >3.12, Django 6, Django REST Framework           |
| Auth | djangorestframework-simplejwt (JWT in HttpOnly cookies) |
| Database | PostgreSQL                                              |
| Background jobs / Cache | Redis + Django RQ                                       |
| Video processing | FFmpeg                                                  |
| Server | Gunicorn + WhiteNoise                                   |
| Deployment | Docker & Docker Compose                                 |

## Project structure

```
videoflix/
├── core/            # Django project: settings, urls, wsgi
├── auth_app/        # Custom user + authentication endpoints
│   └── api/         # serializers, views, urls, cookie auth, utils
├── video_app/       # Video model, catalog + HLS endpoints
│   ├── api/         # serializers, views, urls
│   ├── tasks.py     # background job: thumbnail + HLS conversion
│   ├── utils.py     # FFmpeg helpers, path/safety helpers
│   ├── signals.py   # enqueue conversion on upload, cleanup on delete
│   └── management/  # convert_video command (local, no worker needed)
├── backend.Dockerfile      # web/worker image (Alpine + FFmpeg)
├── backend.entrypoint.sh   # migrate, create superuser, start worker + Gunicorn
├── docker-compose.yml
├── requirements.txt
└── .env.template           # template for your .env
```

---

## Setup with Docker (recommended)

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

**1. Clone the repository**
```bash
git clone https://github.com/lucas-hmchr/videoflix.git
cd videoflix
```

**2. Create your `.env`**
```bash
cp .env.template .env
```
Edit `.env` and set at least:
- a strong `SECRET_KEY`
- `DB_PASSWORD` (any value; the DB container is created with it)
- `DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD` (your admin login)
- **`DB_HOST=db`** and **`REDIS_HOST=redis`** (the Docker service names — important!)

**3. Start the stack**
```bash
docker compose up --build
```
This starts three containers: `db` (PostgreSQL), `redis`, and `web`. On startup the
`web` container automatically waits for the database, runs `collectstatic` and
migrations, **creates the admin user from your `.env`**, starts the RQ worker, and
launches Gunicorn.

**4. Open the app**
- API:   http://localhost:8000/api/
- Admin: http://localhost:8000/admin/ (log in with `DJANGO_SUPERUSER_EMAIL` / `DJANGO_SUPERUSER_PASSWORD`)

That's it — no manual `createsuperuser` needed. Uploading a video in the admin
**auto-converts** in the background; watch it with `docker compose logs -f web`.

### Useful Docker commands

| Command | Description |
|---------|-------------|
| `docker compose up -d` | Start in the background |
| `docker compose logs -f web` | Tail the API logs and watch video conversions |
| `docker compose exec web python manage.py <cmd>` | Run any manage.py command |
| `docker compose down` | Stop (data kept in volumes) |
| `docker compose down -v` | Stop and wipe all data (fresh start) |

---

## Setup without Docker (local development)

**Prerequisites:** Python 3.12+, PostgreSQL, and FFmpeg installed and on your PATH.
Redis is optional (see note below).

```bash
git clone https://github.com/lucas-hmchr/videoflix.git
cd videoflix

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt

cp .env.template .env   # set DB_HOST=localhost and REDIS_HOST=localhost

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

**Converting uploaded videos locally:**
- **With Redis running:** start a worker in a separate terminal —
  `python manage.py rqworker default` — and uploads convert automatically.
- **Without Redis:** after uploading a video in the admin, convert it manually:
  ```bash
  python manage.py convert_video <video_id>
  ```

---

## Environment variables

All configuration lives in `.env` (see `.env.template` for a full template).

| Variable | Description | Example |
|----------|-------------|---------|
| `DJANGO_SUPERUSER_EMAIL` / `DJANGO_SUPERUSER_PASSWORD` | Admin auto-created on container start | `admin@example.com` |
| `SECRET_KEY` | Django secret key | *(long random string)* |
| `DEBUG` | Debug mode | `True` (local) / `False` (prod) |
| `ALLOWED_HOSTS` | Allowed host names, comma-separated | `localhost,127.0.0.1` |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | PostgreSQL credentials | |
| `DB_HOST` | DB host — `db` in Docker, `localhost` locally | `db` |
| `DB_PORT` | DB port | `5432` |
| `REDIS_HOST` | Redis host — `redis` in Docker, `localhost` locally | `redis` |
| `REDIS_PORT` / `REDIS_DB` / `REDIS_CACHE_DB` | Redis port and DB slots | `6379` / `0` / `1` |
| `REDIS_LOCATION` | Full Redis URL for the cache | `redis://redis:6379/1` |
| `EMAIL_BACKEND` | Email backend (console prints to log by default) | console / smtp backend |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | SMTP settings (when using the SMTP backend) | |
| `EMAIL_USE_TLS` / `EMAIL_USE_SSL` | SMTP encryption | `True` / `False` |
| `DEFAULT_FROM_EMAIL` | Sender address | `noreply@videoflix.local` |
| `FRONTEND_URL` | Frontend base URL for activation/reset links | `http://localhost:5500` |
| `CORS_ALLOWED_ORIGINS` | Frontend origins allowed to call the API | `http://localhost:5500` |
| `CSRF_TRUSTED_ORIGINS` | Trusted origins for CSRF | `http://localhost:5500` |

### Email sending (activation & password reset)

The app sends two emails: the **activation link** on registration and the
**password reset link**. Where they end up depends solely on `EMAIL_BACKEND` in
your `.env` — the rest of the project (Docker, frontend) does **not** need to be
changed.

**1. Preview only, without real delivery (default):**

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

The email is not sent but printed to the backend log. In addition, the finished
link is logged on its own line (`INFO Activation link for ...`) that you can copy
directly.

**2. Real emails to a real inbox (your own SMTP server):**

You do **not** need to run your own mail server — just enter the SMTP credentials
of *your* email provider in the `.env`. These are the exact values you would also
use in Thunderbird/Outlook for outgoing mail ("Outgoing/SMTP"):

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=<your-provider-smtp-server>     # e.g. smtp.gmail.com, mail.your-domain.com
EMAIL_PORT=587                              # 587 = STARTTLS, 465 = SSL
EMAIL_HOST_USER=<your-email-address>
EMAIL_HOST_PASSWORD=<your-mailbox-password> # Gmail: 16-digit App Password
EMAIL_USE_TLS=True                          # port 465: set to False
EMAIL_USE_SSL=False                         # port 465: set to True
DEFAULT_FROM_EMAIL=<your-email-address>     # must match the SMTP account
```

Common providers:

| Provider | `EMAIL_HOST` | Port / Encryption | Password |
|----------|--------------|-------------------|----------|
| Gmail | `smtp.gmail.com` | 587 / TLS | **App Password** (2FA required, not your normal password) |
| Own domain (shared hosting, e.g. IONOS/All-Inkl/server-center) | `mail.your-domain.com` | 587 / TLS (or 465 / SSL) | normal mailbox password |
| Outlook/Microsoft 365 | `smtp.office365.com` | 587 / TLS | account password |

#### Quick start with Gmail (recommended for testing)

1. **Create an App Password** (Gmail does not allow a normal password for SMTP):
   - Enable two-factor authentication: <https://myaccount.google.com/security>
   - Create an App Password: <https://myaccount.google.com/apppasswords>
   - You receive 16 characters like `abcd efgh ijkl mnop`.
2. **Set these four values in your `.env`** (leave the rest as shown above):

   ```env
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.gmail.com
   EMAIL_HOST_USER=your.address@gmail.com           # <- your Gmail address
   EMAIL_HOST_PASSWORD=abcdefghijklmnop             # <- App Password (no spaces)
   DEFAULT_FROM_EMAIL=your.address@gmail.com         # <- the same Gmail address
   ```

3. Restart the container and test delivery (see below).

Then restart the backend container so the `.env` is re-read:

```bash
docker compose up -d --build web
```

Test delivery without registering (built-in Django command):

```bash
docker compose exec web python manage.py sendtestemail your.address@gmail.com
```

> **Important:**
> - `EMAIL_HOST` must match the account in `EMAIL_HOST_USER`. Sending a
>   `@my-domain.com` address through `smtp.gmail.com` fails with
>   `535 Username and Password not accepted`.
> - `DEFAULT_FROM_EMAIL` should be the same address as `EMAIL_HOST_USER` — most
>   providers forbid spoofing a foreign sender.
> - `.env` is in `.gitignore`; your credentials must **not** be committed.

> **Frontend URL:** activation and password-reset links are built from
> `FRONTEND_URL`. The frontend runs on **Live Server (port 5500)**, so this must be
> `http://localhost:5500`. If `FRONTEND_URL` is missing from `.env`, the link falls
> back to this default. The Live Server must be running to open the link.

---

## API documentation

Base URL: `http://localhost:8000`

### Authentication

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/register/` | Register a new user (creates an inactive account, sends activation email) | – |
| GET | `/api/activate/<uidb64>/<token>/` | Activate an account from the email link | – |
| POST | `/api/login/` | Log in; sets `access_token` & `refresh_token` HttpOnly cookies | – |
| POST | `/api/logout/` | Log out; blacklists the refresh token and clears cookies | cookie |
| POST | `/api/token/refresh/` | Issue a new access token from the refresh cookie | cookie |
| POST | `/api/password_reset/` | Send a password-reset email | – |
| POST | `/api/password_confirm/<uidb64>/<token>/` | Set a new password via the email link | – |

**Examples**

```jsonc
// POST /api/register/
{ "email": "user@example.com", "password": "secret123", "confirmed_password": "secret123" }

// POST /api/login/
{ "email": "user@example.com", "password": "secret123" }

// POST /api/password_reset/
{ "email": "user@example.com" }

// POST /api/password_confirm/<uidb64>/<token>/
{ "new_password": "newsecret123", "confirm_password": "newsecret123" }
```

### Videos (require authentication)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/video/` | List all videos (newest first) with metadata + thumbnail URL |
| GET | `/api/video/<movie_id>/<resolution>/index.m3u8` | HLS manifest for a resolution |
| GET | `/api/video/<movie_id>/<resolution>/<segment>/` | A single `.ts` video segment |

`<resolution>` is `480p`, `720p`, or `1080p`. Authentication is read from the
`access_token` cookie set at login.

---

## How video streaming works

1. An admin uploads a video file via the Django admin.
2. A `post_save` signal enqueues a conversion job on Redis.
3. The RQ **worker** picks up the job and runs **FFmpeg**, producing a thumbnail and
   HLS renditions (480p/720p/1080p) under `media/hls/<video_id>/<resolution>/`.
4. A player requests `index.m3u8`, reads the listed `.ts` segments, and streams them
   in order — switching quality by requesting a different resolution's manifest.

---

## License

This project was built for educational purposes.
