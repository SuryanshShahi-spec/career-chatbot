"""Legacy ATS UI compatibility wrapper.

The canonical implementation lives in Assets.ats_analyzer.
"""

from Assets.ats_analyzer import ATSAnalyzer, analyze_skills_gap, build_keyword_optimization


def _launch_ui():
    import streamlit as st

    st.set_page_config(page_title="ATS Resume Analyzer", page_icon="📄", layout="wide")
    st.title("ATS Resume Analyzer")
    st.caption("This UI is routed to the canonical ATS analyzer in Assets.ats_analyzer.")
    st.info("Use the main Job Search AI Agent ATS tool for the merged job-description scoring and skill-gap analysis.")


if __name__ == "__main__":
    _launch_ui()

    with st.expander("ℹ️ How scoring works"):
        st.markdown(
            """
            The overall score blends five weighted categories:

            | Category | Weight | What it checks |
            |---|---|---|
            | **Keyword Match** | 40% | TF-IDF similarity + literal keyword overlap vs. the job description |
            | **Content Quality** | 20% | Action verbs, quantified achievements, weak phrases, sentence length |
            | **Format & Structure** | 20% | Standard section headers, tables/images/columns that confuse ATS parsers, page count, bullet usage |
            | **Contact Information** | 10% | Email, phone, LinkedIn, location |
            | **Length & Readability** | 10% | Word count in a healthy range |

            All processing happens locally in this app — no data is sent anywhere.
            """
        )
