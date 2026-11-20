import unittest

from compliance import missing_documents


class MissingDocumentsTests(unittest.TestCase):
    def test_supplier_has_all_required_documents(self):
        required = ["insurance", "registration"]
        submitted = ["registration", "insurance", "training_record"]

        self.assertEqual(missing_documents(required, submitted), [])

    def test_supplier_is_missing_insurance(self):
        required = ["insurance", "registration"]
        submitted = ["registration", "training_record"]

        self.assertEqual(missing_documents(required, submitted), ["insurance"])
