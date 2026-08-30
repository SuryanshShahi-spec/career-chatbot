"""Compatibility wrapper for the canonical ATS analyzer.

This module preserves the older import names used by the UI and legacy scripts,
while delegating all real work to Assets.ats_analyzer.
"""

from Assets.ats_analyzer import (
    ATSAnalyzer,
    analyze_skills_gap,
    build_keyword_optimization,
    extract_technical_keywords,
)


def extract_resume_text(filename: str, file_bytes: bytes):
    from Assets.resume_parsing import text_extractor

    if filename.lower().endswith(".pdf"):
        return text_extractor(filename), {"pages": None, "tables_detected": 0, "images_detected": 0, "columns_suspected": False}
    return text_extractor(filename), {"pages": None, "tables_detected": 0, "images_detected": 0, "columns_suspected": False}


def analyze_resume(resume_text: str, meta: dict, job_description: str = ""):
    from Assets.ats_analyzer import ATSAnalyzer

    analyzer = ATSAnalyzer()
    return analyzer.analyze(resume_text, job_description)


__all__ = [
    "ATSAnalyzer",
    "analyze_resume",
    "extract_resume_text",
    "build_keyword_optimization",
    "analyze_skills_gap",
    "extract_technical_keywords",
]
