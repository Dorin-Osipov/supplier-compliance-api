# Supplier Compliance API

A Python rules engine for supplier onboarding. Given the required documents, submitted evidence and an assessment date, it reports which documents to request, which to renew and whether the supplier is eligible.

The FastAPI endpoint delegates to a standard-library rules engine. Read the [assessment rules](compliance.py) or inspect the [tests for expiry dates, renewals and single blockers](test_compliance.py).

## Run the API

With Python 3.11+ in an active virtual environment, run:

```sh
python -m pip install -r requirements-dev.txt
python -m uvicorn api:app
```

Open [interactive API docs](http://127.0.0.1:8000/docs) or submit this request from another terminal:

```sh
curl -sS http://127.0.0.1:8000/assessments -H 'Content-Type: application/json' \
  -d '{"as_of":"2026-11-21","required":["insurance","registration"],"documents":[{"kind":"insurance","expires_on":"2026-11-20"}]}'
```

```json
{"compliant":false,"missing":["registration"],"expired":["insurance"]}
```

A completed assessment returns HTTP 200, including when a supplier is blocked. Invalid requests return HTTP 422. Supply calendar dates as YYYY-MM-DD and evidence already in effect on the assessment date. Requests are evaluated independently and are not stored.

## Try the Python rules directly

From the repository root, start Python 3.9 or later and run this example.

```pycon
>>> from datetime import date
>>> from compliance import Document, assess_supplier
>>> required = ["insurance", "registration"]
>>> evidence = [Document("insurance", date(2026, 11, 19))]
>>> today = date(2026, 11, 20)
>>> assess_supplier(required, evidence, today)
Assessment(missing=('registration',), expired=('insurance',))
>>> evidence.extend([Document("insurance", date(2027, 11, 19)), Document("registration", today)])
>>> assess_supplier(required, evidence, today).compliant
True

```

Supply the evidence already available on the assessment date. A certificate covers its final calendar day. Any current certificate satisfies its document type, so the order of renewals has no effect. Extra types are ignored and each outstanding requirement appears once, in alphabetical order.

For a presence-only check, `missing_documents(required, submitted_types)` returns a sorted list of absent types.

## Run the checks

```sh
python -m unittest -v
python -m doctest README.md
```
