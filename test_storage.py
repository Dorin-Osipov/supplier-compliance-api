import asyncio
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

import storage
from api import app


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "requires a disposable PostgreSQL database")
class DocumentHistoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_history_survives_requests_and_is_scoped_by_supplier_and_date(self):
        with patch.dict(os.environ, DATABASE_URL=os.environ["TEST_DATABASE_URL"]):
            storage.migrate()
            storage.migrate()
            supplier = f"/suppliers/{uuid4()}"
            other = f"/suppliers/{uuid4()}"
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                for start, end in [("2026-01-01", "2026-11-20"), ("2026-11-23", "2027-11-23")]:
                    response = await client.post(supplier + "/documents", json={
                        "kind": "insurance", "valid_from": start, "expires_on": end,
                    })
                    self.assertEqual(response.status_code, 201, response.text)
                for owner, day, missing, expired in [
                    (supplier, "2026-11-20", [], []),
                    (supplier, "2026-11-22", [], ["insurance"]),
                    (supplier, "2026-11-23", [], []),
                    (other, "2026-11-23", ["insurance"], []),
                ]:
                    response = await client.post(owner + "/assessments", json={
                        "required": ["insurance"], "as_of": day,
                    })
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json(), {
                        "missing": missing, "expired": expired, "compliant": not (missing or expired),
                    })


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "requires a disposable PostgreSQL database")
class SubmissionRetryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        env = patch.dict(os.environ, DATABASE_URL=os.environ["TEST_DATABASE_URL"])
        env.start()
        self.addCleanup(env.stop)
        storage.migrate()
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)
        self.supplier = uuid4()
        self.url = f"/suppliers/{self.supplier}/documents"
        self.headers = {"Idempotency-Key": str(uuid4())}
        self.body = {"kind": "tax", "valid_from": "2026-01-01", "expires_on": "2026-12-31"}

    async def test_concurrent_retries_return_one_persisted_receipt(self):
        responses = await asyncio.gather(*(
            self.client.post(self.url, headers=self.headers, json=self.body) for _ in range(4)
        ))
        for response in responses:
            self.assertEqual(response.status_code, 201, response.text)
            self.assertEqual(response.json(), responses[0].json())
        with storage.connect() as conn:
            rows = conn.execute(
                "SELECT id FROM supplier_documents WHERE supplier_id = %s", (self.supplier,)
            ).fetchall()
        self.assertEqual([str(row[0]) for row in rows], [responses[0].json()["id"]])

    async def test_changed_payload_conflicts_and_original_receipt_remains_replayable(self):
        first = await self.client.post(self.url, headers=self.headers, json=self.body)
        self.assertEqual(first.status_code, 201)
        for field, value in [("kind", "insurance"), ("valid_from", "2026-02-01"),
                             ("expires_on", "2027-01-01")]:
            with self.subTest(field=field):
                result = await self.client.post(
                    self.url, headers=self.headers, json={**self.body, field: value}
                )
                self.assertEqual(result.status_code, 409)
        replay = await self.client.post(self.url, headers=self.headers, json=self.body)
        self.assertEqual(replay.status_code, 201)
        self.assertEqual(replay.json(), first.json())

    async def test_keys_are_supplier_scoped_and_optional(self):
        urls = [self.url, f"/suppliers/{uuid4()}/documents", self.url, self.url]
        ids = []
        for url, headers in zip(urls, [self.headers, self.headers, {}, {}]):
            response = await self.client.post(url, headers=headers, json=self.body)
            self.assertEqual(response.status_code, 201, response.text)
            ids.append(response.json()["id"])
        self.assertEqual(len(set(ids)), 4)
