import unittest

from httpx import ASGITransport, AsyncClient

from api import app


class AssessmentEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)
        self.payload = {
            "required": ["insurance", "registration"],
            "documents": [{"kind": "insurance", "expires_on": "2026-11-20"}],
            "as_of": "2026-11-21",
        }

    async def test_blocked_supplier_receives_actionable_assessment(self):
        response = await self.client.post("/assessments", json=self.payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "compliant": False, "missing": ["registration"], "expired": ["insurance"]
        })

    async def test_current_renewal_and_registration_allow_onboarding(self):
        self.payload["documents"][:0] = [
            {"kind": kind, "expires_on": self.payload["as_of"]}
            for kind in self.payload["required"]
        ]
        response = await self.client.post("/assessments", json=self.payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"compliant": True, "missing": [], "expired": []})

    async def test_invalid_requests_return_validation_errors(self):
        for change in [
            {"as_of": "2026-02-30"}, {"as_of": 0}, {"required": [" "]},
            {"documents": [{"kind": "insurance"}]}, {"unexpected": True},
            {"documents": [{"kind": "tax", "expires_on": "2026-11-20", "expiry": "typo"}]},
        ]:
            with self.subTest(change=change):
                response = await self.client.post("/assessments", json={**self.payload, **change})
                self.assertEqual(response.status_code, 422)
