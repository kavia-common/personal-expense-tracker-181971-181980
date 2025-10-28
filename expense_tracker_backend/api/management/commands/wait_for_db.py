import time
import os
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError, InterfaceError, ProgrammingError


# PUBLIC_INTERFACE
class Command(BaseCommand):
    """
    Wait for the default database to be available before proceeding.

    Usage:
      python manage.py wait_for_db --timeout 60 --sleep-interval 1

    Options:
      --timeout: total seconds to wait before failing (default: 60)
      --sleep-interval: seconds between retries (default: 1)

    Behavior:
      - Attempts to get a cursor on the 'default' connection.
      - Retries on common database connection exceptions until success or timeout.
      - Exits with a non-zero code if the database never becomes available.
    """
    help = "Wait for database to become available."

    def add_arguments(self, parser):
        parser.add_argument("--timeout", type=int, default=60, help="Seconds to wait for DB")
        parser.add_argument(
            "--sleep-interval", type=float, default=1.0, help="Seconds between retries"
        )

    def handle(self, *args, **options):
        timeout = options["timeout"]
        interval = options["sleep_interval"]
        start_time = time.time()

        db = connections["default"]
        # Provide visibility into the configured target for troubleshooting
        host = os.getenv("POSTGRES_HOST") or os.getenv("DB_HOST") or ""
        port = os.getenv("POSTGRES_PORT") or os.getenv("DB_PORT") or ""
        name = os.getenv("POSTGRES_DB") or os.getenv("DB_NAME") or ""
        user = os.getenv("POSTGRES_USER") or os.getenv("DB_USER") or ""
        using_url = bool(os.getenv("DATABASE_URL"))
        url_note = "DATABASE_URL" if using_url else "POSTGRES_* / DB_*"
        self.stdout.write(
            self.style.NOTICE(
                f"Waiting for database via {url_note} (host={host or 'env/DATABASE_URL'}, port={port or 'env/DATABASE_URL'}, db={name}, user={user})..."
            )
        )

        last_error: Exception | None = None
        while True:
            try:
                # Force connection initialization and cursor creation
                db.cursor()
            except (OperationalError, InterfaceError, ProgrammingError) as exc:
                last_error = exc
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    self.stdout.write(self.style.ERROR("Database not available before timeout."))
                    if last_error:
                        self.stdout.write(self.style.ERROR(f"Last error: {last_error}"))
                    # Exit with error code so orchestrators can fail fast
                    raise SystemExit(1)
                time.sleep(interval)
            else:
                break

        self.stdout.write(self.style.SUCCESS("Database is available."))
