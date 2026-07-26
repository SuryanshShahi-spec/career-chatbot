"""
test/test_tools.py
------------------
Smoke tests for all three agent tools.
Run with:  pytest test/test_tools.py -v
"""

import sys
import json
from pathlib import Path
import pytest

# Make repo root importable
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================
# Job Search Tool
# ============================================================
class TestJobSearchTool:
    def test_import(self):
        from tools.job_search_tool import job_search_tool
        assert callable(job_search_tool)

    def test_returns_json(self):
        from tools.job_search_tool import job_search_tool
        result = job_search_tool.invoke({
            "title": "Software Engineer",
            "location": "Bangalore",
            "max_results": 3,
            "country": "in",
        })
        data = json.loads(result)
        assert "jobs" in data or "message" in data

    def test_remote_filter(self):
        from tools.job_search_tool import job_search_tool
        result = job_search_tool.invoke({
            "title": "Data Analyst",
            "remote": True,
            "max_results": 2,
        })
        data = json.loads(result)
        assert isinstance(data, dict)


# ============================================================
# Company Research Tool
# ============================================================
class TestCompanyResearchTool:
    def test_import(self):
        from tools.company_research_tool import company_research_tool
        assert callable(company_research_tool)

    def test_returns_json(self):
        from tools.company_research_tool import company_research_tool
        result = company_research_tool.invoke({
            "company_name": "Infosys",
            "focus_areas": ["culture", "salary"],
            "max_web_results": 2,
        })
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_has_expected_keys(self):
        from tools.company_research_tool import company_research_tool
        result = company_research_tool.invoke({
            "company_name": "Wipro",
            "max_web_results": 2,
        })
        data = json.loads(result)
        # Either the full report or an error key
        assert any(k in data for k in ["overview", "error", "raw_report"])


# ============================================================
# Resume Parser Tool
# ============================================================
class TestResumeParserTool:
    def test_import(self):
        from tools.resume_parser_tool import resume_parser_tool
        assert callable(resume_parser_tool)

    def test_missing_file_returns_error(self):
        from tools.resume_parser_tool import resume_parser_tool
        result = resume_parser_tool.invoke({
            "pdf_path": "C:/non_existent_resume.pdf",
            "enrich_with_llm": False,
        })
        data = json.loads(result)
        assert "error" in data

    def test_non_pdf_returns_error(self):
        from tools.resume_parser_tool import resume_parser_tool
        result = resume_parser_tool.invoke({
            "pdf_path": "C:/some_file.docx",
            "enrich_with_llm": False,
        })
        data = json.loads(result)
        assert "error" in data

    def test_bytes_extractor_import(self):
        from tools.resume_parser_tool import extract_text_from_pdf_bytes
        assert callable(extract_text_from_pdf_bytes)


# ============================================================
# Tools Registry
# ============================================================
class TestToolsRegistry:
    def test_all_tools_importable(self):
        from tools import ALL_TOOLS
        assert len(ALL_TOOLS) == 3

    def test_tool_names(self):
        from tools import ALL_TOOLS
        names = [t.name for t in ALL_TOOLS]
        assert "job_search_tool" in names
        assert "company_research_tool" in names
        assert "resume_parser_tool" in names
