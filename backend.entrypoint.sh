#!/bin/sh
set -e

# Wait until PostgreSQL is ready to accept connections.
echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT} ..."
until pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" >/dev/null 2>&1; do
    sleep 1
done
echo "PostgreSQL is up."

# Collect static files and apply database migrations.
python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate

# Create the superuser from environment variables if it does not exist yet.
# Our custom User model is email-only (no username field).
python manage.py shell <<'PYEOF'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'adminpassword')

if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email=email, password=password)
    print(f"Superuser '{email}' created.")
else:
    print(f"Superuser '{email}' already exists.")
PYEOF

# Start the RQ worker in the background, then run the web server.
python manage.py rqworker default &

exec gunicorn core.wsgi:application --bind 0.0.0.0:8000 --reload
