# Supplier Compliance API

Check which required document types a supplier still needs to submit. Document types are matched by exact identifier. An empty result means all required types are present.

```python
from compliance import missing_documents

missing_documents(["insurance", "registration"], ["registration"])
# ["insurance"]
```

Run the tests with Python 3.9 or later from the repository root:

```sh
python -m unittest -v
```
