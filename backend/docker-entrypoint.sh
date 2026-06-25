#!/bin/sh
set -e

# Wait for Postgres, then apply migrations before starting the server.
echo "Running database migrations..."
python manage.py migrate --noinput

exec "$@"
