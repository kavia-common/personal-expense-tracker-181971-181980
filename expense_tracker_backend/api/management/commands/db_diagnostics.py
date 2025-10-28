import os
import sys
from urllib.parse import urlparse

from django.core.management.base import BaseCommand
from django.conf import settings


def _effective_db_settings():
    """
    Extract the resolved DATABASES['default'] as Django is using it.
    """
    return settings.DATABASES.get("default", {})


def _get_env_db_values():
    """
    Collect environment variables that influence DB config.
    """
    return {
        "DATABASE_URL": os.getenv("DATABASE_URL", ""),
        "POSTGRES_HOST": os.getenv("POSTGRES_HOST", ""),
        "POSTGRES_PORT": os.getenv("POSTGRES_PORT", ""),
        "POSTGRES_DB": os.getenv("POSTGRES_DB", ""),
        "POSTGRES_USER": os.getenv("POSTGRES_USER", ""),
        "POSTGRES_PASSWORD": "***" if os.getenv("POSTGRES_PASSWORD") else "",
    }


def _parse_database_url(db_url: str):
    """
    Parse DATABASE_URL for quick visibility.
    """
    try:
        parsed = urlparse(db_url)
        return {
            "scheme": parsed.scheme,
            "user": parsed.username or "",
            "password": "***" if parsed.password else "",
            "host": parsed.hostname or "",
            "port": parsed.port or "",
            "db": (parsed.path or "").lstrip("/"),
        }
    except Exception as exc:
        return {"error": f"Failed to parse DATABASE_URL: {exc}"}


def _try_psycopg_connect():
    """
    Attempt a direct psycopg (v3) connection using current django settings.
    Falls back to psycopg2 if psycopg is not available.
    """
    db = settings.DATABASES.get("default", {})
    engine = db.get("ENGINE", "")
    if "postgresql" not in engine:
        return False, "Not a PostgreSQL engine; skipping direct psycopg test."

    name = db.get("NAME") or os.getenv("POSTGRES_DB") or ""
    user = db.get("USER") or os.getenv("POSTGRES_USER") or ""
    password = db.get("PASSWORD") or os.getenv("POSTGRES_PASSWORD") or ""
    host = db.get("HOST") or os.getenv("POSTGRES_HOST") or "localhost"
    port = str(db.get("PORT") or os.getenv("POSTGRES_PORT") or "5001")

    # Try psycopg3 first
    try:
        import psycopg

        conn_str = f"dbname={name} user={user} password={password} host={host} port={port}"
        with psycopg.connect(conn_str, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        return True, f"psycopg connection OK to {host}:{port}/{name} as {user}"
    except Exception as exc_psycopg:
        # Try psycopg2 as fallback
        try:
            import psycopg2  # type: ignore

            conn = psycopg2.connect(
                dbname=name, user=user, password=password, host=host, port=port, connect_timeout=5
            )
            cur = conn.cursor()
            cur.execute("SELECT 1;")
            cur.fetchone()
            cur.close()
            conn.close()
            return True, f"psycopg2 connection OK to {host}:{port}/{name} as {user}"
        except Exception as exc_psycopg2:
            return False, f"psycopg error: {exc_psycopg}; psycopg2 error: {exc_psycopg2}"


# PUBLIC_INTERFACE
class Command(BaseCommand):
    """Print effective database configuration and attempt direct DB connection to diagnose issues."""

    help = "Diagnose database configuration and connectivity."

    def handle(self, *args, **options):
        env_vals = _get_env_db_values()
        self.stdout.write(self.style.NOTICE("Environment variables affecting DB:"))
        for k, v in env_vals.items():
            self.stdout.write(f"  {k} = {v}")

        if env_vals.get("DATABASE_URL"):
            parsed = _parse_database_url(env_vals["DATABASE_URL"])
            self.stdout.write(self.style.NOTICE("Parsed DATABASE_URL:"))
            for k, v in parsed.items():
                self.stdout.write(f"  {k}: {v}")

        eff = _effective_db_settings()
        self.stdout.write(self.style.NOTICE("Django DATABASES['default'] (effective):"))
        redacted = eff.copy()
        if "PASSWORD" in redacted and redacted["PASSWORD"]:
            redacted["PASSWORD"] = "***"
        self.stdout.write(str(redacted))

        ok, msg = _try_psycopg_connect()
        if ok:
            self.stdout.write(self.style.SUCCESS(msg))
            sys.exit(0)
        else:
            self.stdout.write(self.style.ERROR(msg))
            sys.exit(1)
