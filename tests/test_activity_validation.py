import tempfile
import unittest
from pathlib import Path

import database


_test_database_directory = tempfile.TemporaryDirectory(
    prefix="daily-work-log-validation-tests-"
)
database.DATABASE_PATH = Path(_test_database_directory.name) / "test.sqlite3"

from app import app, _spreadsheet_safe_cell, validate_activity_form


class ActivityValidationTests(unittest.TestCase):
    def make_form(self, **overrides):
        form = {
            "activity_date": "2026-11-12",
            "activity_time": "09:30",
            "title": "Test activity",
            "notes": "",
            "priority": "Medium",
            "status": "Pending",
        }
        form.update(overrides)
        return form

    def test_accepts_canonical_date_and_time(self):
        _, error = validate_activity_form(self.make_form())

        self.assertIsNone(error)

    def test_rejects_noncanonical_iso_date(self):
        _, error = validate_activity_form(
            self.make_form(activity_date="2026-1-2")
        )

        self.assertEqual(error, "Please enter a valid activity date.")

    def test_rejects_compact_date_format(self):
        _, error = validate_activity_form(
            self.make_form(activity_date="20261112")
        )

        self.assertEqual(error, "Please enter a valid activity date.")

    def test_rejects_noncanonical_time(self):
        _, error = validate_activity_form(
            self.make_form(activity_time="9:30")
        )

        self.assertEqual(error, "Please enter a valid activity time.")

    def test_rejects_out_of_range_time(self):
        _, error = validate_activity_form(
            self.make_form(activity_time="24:00")
        )

        self.assertEqual(error, "Please enter a valid activity time.")

    def test_neutralizes_spreadsheet_formula_prefixes(self):
        for value in ("=1+1", " +1", "-1+1", " @SUM(A1:A2)"):
            with self.subTest(value=value):
                self.assertEqual(_spreadsheet_safe_cell(value), "'" + value)

    def test_leaves_non_formula_text_unchanged(self):
        value = "Regular activity notes"

        self.assertEqual(_spreadsheet_safe_cell(value), value)

    def test_work_history_ignores_noncanonical_date_filter(self):
        response = app.test_client().get(
            "/activities?filter_date=2026-1-2"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'name="filter_date"\n                   value=""', response.data)


if __name__ == "__main__":
    unittest.main()
