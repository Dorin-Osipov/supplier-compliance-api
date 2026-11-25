"""Walk a fresh demo supplier through onboarding against the local Compose API."""

import json
from urllib.request import Request, urlopen
from uuid import UUID, uuid4


def post(url, payload, expected_status, *, key=None):
    headers = {"Content-Type": "application/json"}
    if key is not None:
        headers["Idempotency-Key"] = str(key)
    request = Request(url, data=json.dumps(payload).encode(), headers=headers)
    with urlopen(request, timeout=10) as response:
        if response.status != expected_status:
            raise RuntimeError(f"Expected HTTP {expected_status}, received {response.status}")
        return json.load(response)


def main():
    supplier_id = uuid4()
    supplier = f"http://127.0.0.1:8000/suppliers/{supplier_id}"
    documents = f"{supplier}/documents"
    assessment = {"required": ["insurance", "registration"], "as_of": "2026-11-25"}
    print(f"Assessing demo supplier {supplier_id} on {assessment['as_of']}")

    post(documents, {"kind": "insurance", "valid_from": "2026-01-01", "expires_on": "2026-11-24"}, 201)
    before = post(f"{supplier}/assessments", assessment, 200)
    if before != {"compliant": False, "missing": ["registration"], "expired": ["insurance"]}:
        raise RuntimeError(f"Unexpected initial assessment: {before}")
    print("Blocked: submit registration and renew insurance.")

    post(documents, {"kind": "registration", "valid_from": "2026-11-25", "expires_on": "2027-11-25"}, 201)
    renewal = {"kind": "insurance", "valid_from": "2026-11-25", "expires_on": "2027-11-25"}
    key = uuid4()
    receipt = post(documents, renewal, 201, key=key)
    replay = post(documents, renewal, 201, key=key)
    document_id = UUID(receipt["id"])
    if replay != receipt:
        raise RuntimeError(f"Retry returned a different receipt: {replay}")
    print(f"Renewal recorded. Retry returned the same document ID: {document_id}")

    after = post(f"{supplier}/assessments", assessment, 200)
    if after != {"compliant": True, "missing": [], "expired": []}:
        raise RuntimeError(f"Unexpected final assessment: {after}")
    print("Eligible: all required documents cover the assessment date.")


if __name__ == "__main__":
    main()
