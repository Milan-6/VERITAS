#!/bin/bash
set -e

CMD="${1:-api}"

# Wait for PostgreSQL if DATABASE_URL contains postgres
if [[ "$DATABASE_URL" == *"postgres"* ]]; then
    echo "Waiting for PostgreSQL database to become available..."
    python -c "
import time, os, sys
from urllib.parse import urlparse

url = os.getenv('DATABASE_URL', '')
try:
    import psycopg2
    result = urlparse(url)
    username = result.username
    password = result.password
    database = result.path[1:]
    hostname = result.hostname
    port = result.port or 5432

    for i in range(30):
        try:
            conn = psycopg2.connect(
                dbname=database,
                user=username,
                password=password,
                host=hostname,
                port=port,
                connect_timeout=3
            )
            conn.close()
            print('PostgreSQL is online and ready!')
            sys.exit(0)
        except Exception as e:
            print(f'Waiting for PostgreSQL ({i+1}/30)...')
            time.sleep(1)
    sys.exit(1)
except ImportError:
    print('psycopg2 not installed; skipping explicit connection probe')
" || { echo "Database connection timed out"; exit 1; }
fi

if [ "$CMD" = "api" ] || [ "$CMD" = "web" ] || [ "$CMD" = "server" ]; then
    echo "Executing Alembic database migrations..."
    alembic upgrade head
    echo "Starting VERITAS FastAPI server on 0.0.0.0:${PORT:-8000}..."
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
elif [ "$CMD" = "worker" ] || [ "$CMD" = "celery" ]; then
    echo "Starting VERITAS Celery Background Worker..."
    exec celery -A app.workers.celery_app worker --loglevel="${CELERY_LOG_LEVEL:-info}" -c "${CELERY_CONCURRENCY:-4}"
else
    exec "$@"
fi
