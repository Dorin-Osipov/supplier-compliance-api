import os
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

import storage


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "requires a disposable PostgreSQL database")
class MigrationUpgradeTests(unittest.TestCase):
    def test_existing_supplier_history_survives_upgrade_and_replay(self):
        database = os.environ["TEST_DATABASE_URL"]
        schema = "upgrade_" + uuid4().hex
        with psycopg.connect(database, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            try:
                isolated = make_conninfo(database, options=f"-c search_path={schema}")
                with patch.dict(os.environ, DATABASE_URL=isolated):
                    self.check_populated_upgrade()
            finally:
                admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))

    def check_populated_upgrade(self):
        initial = Path(__file__).with_name("migrations") / "001_supplier_documents.sql"
        supplier = uuid4()
        certificates = [
            (uuid4(), supplier, "insurance", date(2025, 1, 1), date(2025, 12, 31)),
            (uuid4(), supplier, "insurance", date(2026, 1, 1), date(2026, 12, 31)),
        ]
        with storage.connect() as conn:
            conn.execute(initial.read_text(encoding="utf-8"))
            conn.execute("CREATE TABLE schema_migrations (version text PRIMARY KEY)")
            conn.execute("INSERT INTO schema_migrations VALUES (%s)", (initial.name,))
            with conn.cursor() as cursor:
                cursor.executemany(
                    """INSERT INTO supplier_documents (id, supplier_id, kind, valid_from, expires_on)
                       VALUES (%s, %s, %s, %s, %s)""",
                    certificates,
                )

        storage.migrate()
        storage.migrate()

        with storage.connect() as conn:
            rows = conn.execute(
                """SELECT id, supplier_id, kind, valid_from, expires_on, idempotency_key
                   FROM supplier_documents ORDER BY valid_from"""
            ).fetchall()
            self.assertEqual(rows, [(*record, None) for record in certificates])
            versions = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
            self.assertIn("002_document_idempotency.sql", versions)
