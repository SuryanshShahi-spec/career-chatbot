"""
Streamlit UI for Job Search AI Agent
This file runs the Streamlit frontend only (no FastAPI).
"""

import importlib
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "Assets") not in sys.path:
    sys.path.insert(0, str(ROOT / "Assets"))
if str(ROOT / "Data") not in sys.path:
    sys.path.insert(0, str(ROOT / "Data"))

load_dotenv(ROOT / ".env")

# Import only the core agent building blocks (not FastAPI)
from Agent.app import build_graph

# Global state
JOB_SEARCH_GRAPH = build_graph()


def render_chat_ui():
    st.set_page_config(page_title="Job Search AI Agent", page_icon="💼", layout="wide")
    st.title("Job Search AI Agent")
    st.caption("LangGraph + Streamlit workflow using the project's Assets and Data modules as tools.")

    with st.sidebar:
        st.subheader("Available tools")
        for tool_name in (
            "job_search",
            "company_research",
            "resume_extract",
            "resume_gap_analysis",
            "ats_resume_scorer",
            "interview_prep",
            "init_database",
            "register_account",
            "login_account",
            "get_user_profile",
            "update_user_profile",
            "show_dashboard",
            "save_job_application",
            "get_job_applications",
            "save_job_preferences",
            "get_job_preferences",
            "location_based_job_search",
        ):
            st.write(f"• {tool_name}")

        st.markdown("---")
        st.write("Examples:")
        st.write("- Find Python jobs in Bangalore")
        st.write("- Search for Data Scientist jobs in top Indian cities")
        st.write("- Save my preference to work in Pune or Hyderabad")
        st.write("- Save that I applied for Software Engineer at Google")
        st.write("- Show me my saved job applications")
        st.write("- Summarize Microsoft")
        st.write("- Analyze resume at Data/Suryansh_Resume.pdf")
        st.write("- Check ATS score for Data/Suryansh_Resume.pdf against a Python Developer JD")
        st.write("- Generate mock interview for Senior Software Engineer at TechCorp")
        st.write("- Give me behavioral interview questions")
        st.write("- Explain the STAR method for interviews")
        st.write("- Analyze job description and prep me for interview questions")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            AIMessage(content="Hi! I can search for jobs, review companies, analyze resumes, and help with account tasks.")
        ]

    for message in st.session_state.messages:
        if isinstance(message, HumanMessage):
            with st.chat_message("user"):
                st.markdown(message.content)
        elif isinstance(message, AIMessage):
            with st.chat_message("assistant"):
                st.markdown(message.content)

    prompt = st.chat_input("Ask the agent about jobs, companies, or your resume...")
    if prompt:
        st.session_state.messages.append(HumanMessage(content=prompt))
        with st.chat_message("user"):
            st.markdown(prompt)

        result = JOB_SEARCH_GRAPH.invoke({"messages": st.session_state.messages})
        final_message = result["messages"][-1]
        st.session_state.messages = result["messages"]

        with st.chat_message("assistant"):
            st.markdown(final_message.content)


if __name__ == "__main__":
    render_chat_ui()
