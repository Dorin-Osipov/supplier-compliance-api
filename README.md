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

## Store supplier documents in PostgreSQL

Point `DATABASE_URL` at a PostgreSQL database where the application can create tables. Run `python -m storage` before starting Uvicorn. The migration records its version in the same transaction as its schema changes and can be run again. The original `POST /assessments` endpoint still runs without a database.

With the API running, store a certificate and assess it from a second request:

```sh
supplier=http://127.0.0.1:8000/suppliers/9fa833d8-270e-40af-9c75-88180786504d
curl -sS "$supplier/documents" -H 'Content-Type: application/json' \
  -d '{"kind":"insurance","valid_from":"2026-01-01","expires_on":"2026-11-20"}'
curl -sS "$supplier/assessments" -H 'Content-Type: application/json' \
  -d '{"required":["insurance"],"as_of":"2026-11-22"}'
```

Each submission without an idempotency key creates a new record and returns its UUID. Renewals preserve previous certificates. Assessments use the coverage dates of all evidence currently recorded for that supplier. A future renewal first counts on its start date. A supplier with no evidence is missing every required type.

To exercise the storage workflow, set `TEST_DATABASE_URL` to a disposable PostgreSQL database and run `python -m unittest -v`. The integration test applies the migration and writes sample rows.

### Retry a submission after a timeout

Generate one UUID per logical submission and reuse it in the `Idempotency-Key` header for every retry. Run this command twice with the same supplier and key:

```sh
curl -i "$supplier/documents" -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: 82af5cd8-4534-49a6-9cf5-b0c8c8bf3b9b' \
  -d '{"kind":"insurance","valid_from":"2026-01-01","expires_on":"2026-11-20"}'
```

Both requests return HTTP 201 and the same document ID. Reusing the key for different certificate details returns HTTP 409. Use a fresh key for a renewal. Keys are scoped to the supplier and retained with the document.
