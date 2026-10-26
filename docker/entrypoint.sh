#!/bin/sh
set -eu
python manage.py migrate --noinput
python manage.py setup_roles
if [ "${LOAD_DEMO_DATA:-false}" = "true" ] && [ ! -f /data/.demo_initialized ]; then
    python manage.py seed_showcase
    touch /data/.demo_initialized
fi
exec "$@"
