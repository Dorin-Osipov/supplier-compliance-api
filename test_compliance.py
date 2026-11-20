import unittest

from datetime import date

from compliance import Assessment, Document, assess_supplier, missing_documents


class MissingDocumentsTests(unittest.TestCase):
    def test_supplier_has_all_required_documents(self):
        required = ["insurance", "registration"]
        submitted = ["registration", "insurance", "training_record"]

        self.assertEqual(missing_documents(required, submitted), [])

    def test_supplier_is_missing_insurance(self):
        required = ["insurance", "registration"]
        submitted = ["registration", "training_record"]

        self.assertEqual(missing_documents(required, submitted), ["insurance"])


class AssessmentTests(unittest.TestCase):
    today = date(2026, 11, 20)
    expired = Document("insurance", date(2026, 11, 19))
    renewal = Document("insurance", date(2027, 11, 19))

    def test_reports_expired_and_missing_requirements_separately(self):
        report = assess_supplier(
            ["tax", "registration", "tax", "insurance"],
            [self.expired, Document("training", self.today)],
            self.today,
        )
        self.assertEqual(report, Assessment(("registration", "tax"), ("insurance",)))
        self.assertFalse(report.compliant)

    def test_expiry_day_is_inclusive(self):
        report = assess_supplier(["insurance"], [self.expired], self.expired.expires_on)
        self.assertTrue(report.compliant)

    def test_valid_renewal_satisfies_requirement_in_either_order(self):
        for records in ([self.renewal, self.expired], [self.expired, self.renewal]):
            with self.subTest(records=records):
                self.assertTrue(assess_supplier(["insurance"], records, self.today).compliant)

    def test_empty_requirements_are_satisfied(self):
        self.assertTrue(assess_supplier([], [self.expired], self.today).compliant)
