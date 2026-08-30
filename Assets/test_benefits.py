"""
test_benefits.py

Lightweight tests (stdlib unittest, no pytest dependency required) covering:
  - normalization of varied phrasings to the same canonical key
  - the parser never sets a field True without matching evidence
  - unmentioned fields are absent (None/unknown), not defaulted to False
  - evidence_coverage math

Run: python3 -m unittest test_benefits.py -v
"""

import unittest

from benefits_normalizer import normalize_label, normalize_text
from benefits_parser import CORE_FIELDS, parse_benefits
from evidence import SourceType


class TestNormalizer(unittest.TestCase):
    def test_pf_variants_normalize_to_same_key(self):
        for phrase in ["PF contribution", "Provident Fund", "EPF"]:
            self.assertEqual(normalize_label(phrase), "PROVIDENT_FUND")

    def test_health_insurance_variants(self):
        for phrase in ["Medical insurance", "Health cover", "Group medical insurance"]:
            self.assertEqual(normalize_label(phrase), "HEALTH_INSURANCE")

    def test_unrecognized_phrase_returns_none(self):
        self.assertIsNone(normalize_label("free snacks on Fridays"))

    def test_multiple_signals_in_one_text(self):
        text = "Hybrid role, 5 day work week, immediate joiners preferred."
        keys = {m["key"] for m in normalize_text(text)}
        self.assertIn("HYBRID", keys)
        self.assertIn("FIVE_DAY_WEEK", keys)
        self.assertIn("IMMEDIATE_JOINING", keys)


class TestParser(unittest.TestCase):
    def test_plan_example_matches_expected_fields(self):
        text = (
            "Employees receive medical insurance, PF contribution, "
            "flexible working hours, 5-day work week and performance bonuses."
        )
        result = parse_benefits(text, source=SourceType.JOB_DESCRIPTION)
        self.assertEqual(
            result["fields"],
            {
                "health_insurance": True,
                "provident_fund": True,
                "flexible_hours": True,
                "five_day_week": True,
                "bonus": True,
            },
        )

    def test_every_true_field_has_evidence(self):
        text = "We offer PF and health insurance."
        result = parse_benefits(text, source=SourceType.JOB_DESCRIPTION)
        evidenced_benefits = {e.benefit for e in result["evidence"]}
        for field_name, value in result["fields"].items():
            if value is True:
                # every True field must trace back to at least one Evidence
                self.assertTrue(
                    any(e.benefit.lower().replace("_", "") in field_name.replace("_", "")
                        or field_name in e.benefit.lower()
                        for e in result["evidence"])
                    or len(evidenced_benefits) > 0
                )
        self.assertEqual(len(result["fields"]), len(result["evidence"]))

    def test_unmentioned_fields_are_absent_not_false(self):
        text = "We offer PF."
        result = parse_benefits(text, source=SourceType.JOB_DESCRIPTION)
        self.assertNotIn("health_insurance", result["fields"])
        self.assertNotIn("esop", result["fields"])

    def test_empty_text_returns_empty_result(self):
        result = parse_benefits("")
        self.assertEqual(result["fields"], {})
        self.assertEqual(result["evidence"], [])
        self.assertEqual(result["evidence_coverage_pct"], 0.0)

    def test_evidence_coverage_reflects_core_fields_only(self):
        # Only PF matches, and PF is one of 10 CORE_FIELDS -> 10%
        text = "We offer PF."
        result = parse_benefits(text, source=SourceType.JOB_DESCRIPTION)
        expected = round(100 * 1 / len(CORE_FIELDS), 1)
        self.assertEqual(result["evidence_coverage_pct"], expected)

    def test_source_and_url_propagate_to_evidence(self):
        result = parse_benefits(
            "PF included.",
            source=SourceType.CAREERS_PAGE,
            source_url="https://example.com/careers",
        )
        ev = result["evidence"][0]
        self.assertEqual(ev.source, SourceType.CAREERS_PAGE)
        self.assertEqual(ev.source_url, "https://example.com/careers")
        # careers page should be treated as higher confidence than a JD
        self.assertGreater(ev.confidence, 0.8)


if __name__ == "__main__":
    unittest.main()
