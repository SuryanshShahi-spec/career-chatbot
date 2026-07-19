"""
tools/resume_parser_tool.py
---------------------------
Resume Parser Tool — extracts structured text from a PDF resume and
optionally uses an LLM to produce a clean, normalised JSON profile.

Features:
  • PDF → raw text via pypdf (no external service needed)
  • Optional LLM enrichment via Groq to extract structured fields:
    name, email, phone, skills, experience, education, summary
  • Exposed as a LangChain @tool

Dependencies (already in requirements.txt):
  pypdf, langchain-groq, pydantic, python-dotenv
"""

from __future__ import annotations

import os
import io
import json
import logging
import re
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from pypdf import PdfReader

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------
class ResumeParserInput(BaseModel):
    pdf_path: str = Field(
        description="Absolute or relative file-system path to the PDF resume to parse"
    )
    enrich_with_llm: bool = Field(
        default=True,
        description=(
            "If True, send extracted text through Groq LLaMA to produce a "
            "structured JSON profile. If False, return raw extracted text only."
        ),
    )
    job_title_hint: Optional[str] = Field(
        default=None,
        description=(
            "Optional target job title to tailor skill/experience extraction, "
            "e.g. 'Data Scientist' or 'Backend Engineer'"
        ),
    )


# ---------------------------------------------------------------------------
# PDF Extraction helper
# ---------------------------------------------------------------------------
def _extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract all text from a PDF using pypdf.

    Supports both file-system paths and raw bytes (pass bytes as pdf_path
    after writing to a temp BytesIO — see _extract_from_bytes).
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found at: {pdf_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {path.suffix}")

    reader = PdfReader(str(path))
    pages_text: list[str] = []

    for page_num, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
            pages_text.append(text)
            logger.debug("Extracted page %d: %d chars", page_num, len(text))
        except Exception as exc:
            logger.warning("Could not extract page %d: %s", page_num, exc)

    full_text = "\n".join(pages_text).strip()
    logger.info("Total extracted: %d characters from %d pages.", len(full_text), len(reader.pages))
    return full_text


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Convenience wrapper to parse a PDF from raw bytes (e.g., from an HTTP
    upload or Streamlit's file_uploader).
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages_text: list[str] = []
    for page in reader.pages:
        try:
            pages_text.append(page.extract_text() or "")
        except Exception:
            pass
    return "\n".join(pages_text).strip()


# ---------------------------------------------------------------------------
# Quick regex-based field extraction (no LLM needed)
# ---------------------------------------------------------------------------
def _quick_extract(text: str) -> dict:
    """
    Extract common resume fields using simple regex patterns.
    Returns a dict — useful as a cheap pre-filter or fallback.
    """
    email_pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    phone_pattern = r"(?:\+?\d[\d\s\-().]{7,}\d)"
    url_pattern   = r"https?://[^\s]+"
    linkedin_pat  = r"linkedin\.com/in/[\w\-]+"

    emails    = re.findall(email_pattern, text)
    phones    = re.findall(phone_pattern, text)
    urls      = re.findall(url_pattern, text)
    linkedin  = re.findall(linkedin_pat, text, re.IGNORECASE)

    return {
        "emails":    list(set(emails)),
        "phones":    list(set(phones[:3])),   # cap at 3
        "urls":      list(set(urls[:5])),
        "linkedin":  linkedin[0] if linkedin else None,
    }


# ---------------------------------------------------------------------------
# LLM Enrichment helper
# ---------------------------------------------------------------------------
_PARSE_PROMPT = ChatPromptTemplate.from_template(
    """You are an expert resume parser and talent acquisition assistant.

Parse the resume text below and extract key information.
{hint_instruction}

Resume Text:
{resume_text}

---

Return ONLY a valid JSON object with these keys (use null for missing fields):
{{
  "full_name": "<candidate full name>",
  "email": "<primary email>",
  "phone": "<primary phone number>",
  "linkedin": "<LinkedIn URL if present>",
  "location": "<city, state/country>",
  "total_experience_years": <number or null>,
  "current_role": "<most recent job title>",
  "current_company": "<most recent employer>",
  "summary": "<2-3 sentence professional summary>",
  "skills": {{
    "technical": ["<skill1>", "<skill2>"],
    "soft": ["<skill1>", "<skill2>"],
    "tools_and_platforms": ["<tool1>", "<tool2>"]
  }},
  "work_experience": [
    {{
      "title": "<job title>",
      "company": "<company name>",
      "duration": "<e.g. Jan 2021 - Dec 2023>",
      "responsibilities": ["<key point 1>", "<key point 2>"]
    }}
  ],
  "education": [
    {{
      "degree": "<degree name>",
      "institution": "<university/college>",
      "year": "<graduation year or range>",
      "gpa": "<GPA if mentioned, else null>"
    }}
  ],
  "certifications": ["<cert 1>", "<cert 2>"],
  "languages": ["<language 1>"],
  "projects": [
    {{
      "name": "<project name>",
      "description": "<one sentence description>",
      "tech_used": ["<tech1>"]
    }}
  ],
  "ats_keywords": ["<keyword 1>", "<keyword 2>"]
}}

Return ONLY the JSON with no extra text."""
)


def _enrich_with_llm(text: str, job_title_hint: Optional[str] = None) -> dict:
    """Send raw text to Groq LLaMA and return a structured resume dict."""
    if not GROQ_API_KEY:
        return {"error": "GROQ_API_KEY not set — LLM enrichment unavailable."}

    hint_instruction = (
        f"The candidate is applying for a **{job_title_hint}** role, "
        "so pay extra attention to relevant skills and experience."
        if job_title_hint
        else "Extract all information comprehensively."
    )

    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=GROQ_API_KEY)
    chain = _PARSE_PROMPT | llm | StrOutputParser()

    try:
        raw_output = chain.invoke({
            "resume_text": text[:6000],   # ~6k chars stays well within context
            "hint_instruction": hint_instruction,
        })

        # Strip markdown code fences if present
        cleaned = raw_output.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]

        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("LLM returned non-JSON; returning raw text as fallback.")
        return {"raw_llm_output": raw_output}
    except Exception as exc:
        logger.error("LLM enrichment error: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# LangChain Tool
# ---------------------------------------------------------------------------
@tool(args_schema=ResumeParserInput)
def resume_parser_tool(
    pdf_path: str,
    enrich_with_llm: bool = True,
    job_title_hint: Optional[str] = None,
) -> str:
    """
    Parse a PDF resume and extract structured information.

    Steps:
      1. Reads the PDF from the given file path using pypdf.
      2. Runs quick regex extraction to find emails, phones, LinkedIn URLs.
      3. (Optional) Sends the raw text to Groq LLaMA-3.3-70B to produce a
         fully-structured JSON profile including skills, work experience,
         education, certifications, projects, and ATS keywords.

    Returns a JSON string containing the parsed resume data.
    """
    logger.info("Parsing resume: %s", pdf_path)

    # Step 1 — Extract raw text
    try:
        raw_text = _extract_text_from_pdf(pdf_path)
    except (FileNotFoundError, ValueError) as exc:
        return json.dumps({"error": str(exc)})

    if not raw_text.strip():
        return json.dumps({"error": "Could not extract any text from the PDF. The file may be image-based (scanned). Consider using an OCR tool."})

    # Step 2 — Quick regex extraction (always run)
    quick_fields = _quick_extract(raw_text)

    result: dict = {
        "pdf_path":   pdf_path,
        "char_count": len(raw_text),
        "raw_text":   raw_text[:2000] + ("..." if len(raw_text) > 2000 else ""),
        "quick_extract": quick_fields,
    }

    # Step 3 — Optional LLM enrichment
    if enrich_with_llm:
        logger.info("Running LLM enrichment…")
        llm_profile = _enrich_with_llm(raw_text, job_title_hint)
        result["structured_profile"] = llm_profile
    else:
        result["structured_profile"] = None
        result["note"] = "LLM enrichment skipped. Set enrich_with_llm=True for full parsing."

    return json.dumps(result, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python resume_parser_tool.py <path_to_resume.pdf> [job_title_hint]")
        print("\nExample:")
        print("  python resume_parser_tool.py C:/Users/HP/Documents/resume.pdf 'Data Scientist'")
        sys.exit(1)

    pdf = sys.argv[1]
    hint = sys.argv[2] if len(sys.argv) > 2 else None

    output = resume_parser_tool.invoke({
        "pdf_path": pdf,
        "enrich_with_llm": True,
        "job_title_hint": hint,
    })
    print(output)
