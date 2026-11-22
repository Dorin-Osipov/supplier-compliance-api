import os
from pathlib import Path

import psycopg


def connect():
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5)


def migrate():
    migrations = Path(__file__).with_name("migrations")
    with connect() as conn:
        # Serialise startup migrations and record each successful file atomically.
        conn.execute("SELECT pg_advisory_xact_lock(405271903)")
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version text PRIMARY KEY)")
        applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
        for path in sorted(migrations.glob("*.sql")):
            if path.name not in applied:
                conn.execute(path.read_text(encoding="utf-8"))
                conn.execute("INSERT INTO schema_migrations VALUES (%s)", (path.name,))


if __name__ == "__main__":
    migrate()
