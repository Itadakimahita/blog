#!/bin/sh
set -eu

export REDIS_WAIT_URL="${BLOG_REDIS_URL:-${REDIS_URL:-${BLOG_CELERY_BROKER_URL:-redis://redis:6379/0}}}"

mkdir -p /data
chown -R appuser:appuser /data /app

echo "Waiting for Redis at ${REDIS_WAIT_URL}..."
until python - <<'PY'
import os
from redis import Redis

url = os.environ["REDIS_WAIT_URL"]
client = Redis.from_url(url)
client.ping()
PY
do
  sleep 1
done

echo "Redis is available."
su -s /bin/sh appuser -c "python manage.py migrate --noinput"
su -s /bin/sh appuser -c "python manage.py collectstatic --noinput"
su -s /bin/sh appuser -c "python manage.py compilemessages"

seed_db="$(printf '%s' "${BLOG_SEED_DB:-false}" | tr '[:upper:]' '[:lower:]')"
if [ "$seed_db" = "true" ]; then
  su -s /bin/sh appuser -c "python manage.py seed"
fi

exec su -s /bin/sh appuser -c "$*"
