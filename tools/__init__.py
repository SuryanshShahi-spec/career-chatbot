"""
tools/__init__.py
-----------------
Central registry of all agent tools.

Import from here to keep the agent clean:

    from tools import ALL_TOOLS
    from tools import job_search_tool, company_research_tool, resume_parser_tool
"""

from tools.job_search_tool import job_search_tool
from tools.company_research_tool import company_research_tool
from tools.resume_parser_tool import resume_parser_tool, extract_text_from_pdf_bytes

# Ordered list for binding to an LLM agent
ALL_TOOLS = [
    job_search_tool,
    company_research_tool,
    resume_parser_tool,
]

__all__ = [
    "job_search_tool",
    "company_research_tool",
    "resume_parser_tool",
    "extract_text_from_pdf_bytes",
    "ALL_TOOLS",
]
