# Supplier Compliance API

A procurement team needs to know whether a supplier can be onboarded and, if blocked, which documents to request or renew. The Python assessment below is the core of that decision.

## Try an assessment

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
