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
