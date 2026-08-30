"""
demo.py

Reproduces the Company A vs Company B comparison from the plan
(sections 8 & 9) using parse_benefits() end to end, to sanity-check the
MVP pipeline: text in -> normalized fields + evidence out -> comparison table.

Run: python3 demo.py
"""

from benefits_parser import CORE_FIELDS, parse_benefits
from evidence import SourceType

COMPANY_A_JD = """
Company A is hiring a Software Engineer. CTC: 10 LPA.
We offer medical insurance, PF contribution, performance bonuses,
hybrid working, and a learning budget for every employee.
"""

COMPANY_B_JD = """
Company B is hiring a Software Engineer. CTC: 11 LPA.
PF and performance bonus included. Work from office role.
"""

DISPLAY_LABELS = {
    "provident_fund": "PF",
    "health_insurance": "Health Insurance",
    "bonus": "Bonus",
    "esop": "ESOP",
    "remote_work": "Remote",
    "hybrid_work": "Hybrid",
    "onsite_work": "On-site",
    "five_day_week": "5-Day Week",
    "six_day_week": "6-Day Week",
    "flexible_hours": "Flexible Hours",
    "learning_budget": "Learning Budget",
}


def render_comparison(name_a, parsed_a, name_b, parsed_b):
    all_keys = sorted(set(parsed_a["fields"]) | set(parsed_b["fields"]))
    print(f"| Category          | {name_a:<10} | {name_b:<10} |")
    print("|" + "-" * 20 + "|" + "-" * 12 + "|" + "-" * 12 + "|")
    for key in all_keys:
        label = DISPLAY_LABELS.get(key, key)
        a_val = "✓" if parsed_a["fields"].get(key) else "Unknown"
        b_val = "✓" if parsed_b["fields"].get(key) else "Unknown"
        print(f"| {label:<18} | {a_val:<10} | {b_val:<10} |")
    print()
    print(f"{name_a} evidence coverage: {parsed_a['evidence_coverage_pct']}%")
    print(f"{name_b} evidence coverage: {parsed_b['evidence_coverage_pct']}%")


if __name__ == "__main__":
    parsed_a = parse_benefits(COMPANY_A_JD, source=SourceType.JOB_DESCRIPTION)
    parsed_b = parse_benefits(COMPANY_B_JD, source=SourceType.JOB_DESCRIPTION)

    render_comparison("Company A", parsed_a, "Company B", parsed_b)

    print()
    print("Note: fields marked 'Unknown' were not mentioned in the source")
    print("text — this is NOT the same as the company not offering them.")
