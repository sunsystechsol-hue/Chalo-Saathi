#!/usr/bin/env bash
set -e

echo "⏳ Waiting for MySQL to be ready on host: $DB_HOST"

python <<END
import os, time, socket

host = os.environ.get("DB_HOST", "db")
port = 3306

while True:
    try:
        s = socket.create_connection((host, port), timeout=2)
        print("✅ MySQL is ready! Starting service...")
        s.close()
        break
    except OSError:
        print("Still waiting for MySQL...")
        time.sleep(2)
END

exec "$@"
