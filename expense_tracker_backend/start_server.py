#!/usr/bin/env python3
"""
Convenience script to start the Django server with database readiness handling.

Behavior:
  1) Wait for Postgres to be available using manage.py wait_for_db.
  2) Run migrations (safe to run repeatedly).
  3) Start the server on 0.0.0.0:3001.

Environment variables required for Postgres configuration (if not using DATABASE_URL):
  - POSTGRES_HOST
  - POSTGRES_PORT (default 5001)
  - POSTGRES_DB
  - POSTGRES_USER
  - POSTGRES_PASSWORD

Note:
  - Do not hardcode secrets; set them via environment or .env file managed by orchestrator.
  - This script is optional; you can run each step manually if preferred.
"""
import os
import subprocess
import sys

def run(cmd: list[str]) -> int:
    print(f"+ {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd)

def main() -> int:
    # Step 1: wait for DB (will exit non-zero if not available within timeout)
    if run([sys.executable, "manage.py", "wait_for_db", "--timeout", "60", "--sleep-interval", "1"]) != 0:
        return 1

    # Step 2: apply migrations
    if run([sys.executable, "manage.py", "migrate", "--noinput"]) != 0:
        return 1

    # Step 3: start server
    port = os.getenv("PORT", "3001")
    return run([sys.executable, "manage.py", "runserver", f"0.0.0.0:{port}"])

if __name__ == "__main__":
    sys.exit(main())
