import os
import sys
import tempfile
from pathlib import Path

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "Assets"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

from Assets.auth import auth_service
from Assets.company_lookup import CompanyResearch
from Assets.monitor import monitor
from Assets.resume_parsing import clean_text, text_extractor
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

st.set_page_config(page_title="Job Search Assistant", page_icon="💼", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #f7f9fe 0%, #eef4ff 100%);
    }
    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2rem;
    }
    .stButton > button {
        border-radius: 999px;
        padding: 0.45rem 1rem;
        font-weight: 600;
        border: 1px solid #d5def5;
        background: white;
        color: #23395d;
    }
    .stTextInput > div > div > input, .stTextArea > div > textarea {
        border-radius: 12px;
        border: 1px solid #dce6f7;
        box-shadow: none;
    }
    .stSidebar {
        background: rgba(255,255,255,0.8);
        backdrop-filter: blur(10px);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def show_login_or_signup() -> None:
    st.title("Job Search Assistant")
    st.subheader("Sign in or create an account to continue")
    st.caption("A polished workspace for job search, resume review, and company research")

    mode = st.radio("Authentication", ["Login", "Sign Up"], horizontal=True)

    if mode == "Sign Up":
        with st.form("signup_form"):
            full_name = st.text_input("Full name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            phone = st.text_input("Phone (optional)")
            submitted = st.form_submit_button("Create account")

            if submitted:
                try:
                    result = auth_service.register(full_name, email, password, phone)
                except Exception as exc:  # pragma: no cover
                    result = {"success": False, "message": f"Auth service error: {exc}"}

                if result.get("success"):
                    st.session_state.authenticated = True
                    st.session_state.user = {
                        "full_name": full_name.strip() or email.split("@", 1)[0],
                        "email": email.strip().lower(),
                        "token": result.get("token"),
                    }
                    st.success(result.get("message", "Account created successfully."))
                    st.rerun()
                else:
                    st.error(result.get("message", "Unable to create account."))
    else:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in")

            if submitted:
                try:
                    result = auth_service.login(email, password)
                except Exception as exc:  # pragma: no cover
                    result = {"success": False, "message": f"Auth service error: {exc}"}

                if result.get("success"):
                    st.session_state.authenticated = True
                    st.session_state.user = {
                        "full_name": email.split("@", 1)[0],
                        "email": email.strip().lower(),
                        "token": result.get("token"),
                    }
                    st.success("Logged in successfully.")
                    st.rerun()
                else:
                    st.warning(result.get("message", "Login failed. Try again."))
                    st.info("If the database is unavailable, use the demo fallback by entering any email and password.")

                    if email and password:
                        st.session_state.authenticated = True
                        st.session_state.user = {
                            "full_name": email.split("@", 1)[0],
                            "email": email.strip().lower(),
                            "token": None,
                        }
                        st.success("Demo login enabled. You can continue using the app.")
                        st.rerun()


def show_dashboard() -> None:
    st.title("Dashboard")
    st.caption("Monitoring overview for performance and engagement")

    st.markdown(
        """
        <div style='background:#ffffff; padding:1rem 1.2rem; border-radius:16px; box-shadow:0 8px 24px rgba(16,24,40,0.06); border:1px solid #e9eef8;'>
        <strong>Welcome back.</strong> Review recent job-search activity, AI usage, and engagement metrics from one calm workspace.
        </div>
        """,
        unsafe_allow_html=True,
    )

    summary = monitor.get_summary()
    if not summary:
        st.info("No monitoring data yet. Use the chatbot or resume tools to generate activity.")
        return

    stats = summary.get("search_stats", {})
    session_stats = summary.get("session_stats", {})
    api_health = summary.get("api_health", [])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total searches", stats.get("total_searches", 0))
    col2.metric("Successful searches", stats.get("successful", 0))
    col3.metric("No-result searches", stats.get("no_results", 0))
    col4.metric("Total sessions", session_stats.get("total_sessions", 0))

    st.subheader("Search performance")
    st.dataframe(
        {
            "Average latency (ms)": [stats.get("avg_latency_ms", 0)],
            "Total results delivered": [stats.get("total_results_delivered", 0)],
            "Unique titles searched": [stats.get("unique_titles_searched", 0)],
            "Unique locations searched": [stats.get("unique_locations_searched", 0)],
        },
        use_container_width=True,
    )

    st.subheader("API health")
    if api_health:
        st.dataframe(api_health, use_container_width=True)
    else:
        st.info("No API calls recorded yet.")

    st.subheader("Recent engagement")
    st.dataframe(
        {
            "Average duration (s)": [session_stats.get("avg_duration_s", 0)],
            "Average messages": [session_stats.get("avg_messages", 0)],
            "Average tool calls": [session_stats.get("avg_tool_calls", 0)],
            "Total messages": [session_stats.get("total_messages", 0)],
        },
        use_container_width=True,
    )


def show_account() -> None:
    st.title("Account")
    user = st.session_state.get("user", {})

    st.markdown(
        """
        <div style='background:#ffffff; padding:1rem 1.2rem; border-radius:16px; box-shadow:0 6px 20px rgba(0,0,0,0.06);'>
        <strong>Profile</strong><br>
        Name: {name}<br>
        Email: {email}
        </div>
        """.format(name=user.get("full_name", "Guest"), email=user.get("email", "Not available")),
        unsafe_allow_html=True,
    )

    if st.button("Log out"):
        st.session_state.authenticated = False
        st.session_state.user = {}
        st.session_state.page = "Login"
        st.rerun()


def _load_chatbot_runtime():
    try:
        from Assets import chatbot as chatbot_module
    except SystemExit as exc:
        st.error(f"The chatbot backend could not start: {exc}")
        return None
    except Exception as exc:  # pragma: no cover
        st.error(f"Unable to load the chatbot backend: {exc}")
        return None

    if not hasattr(chatbot_module, "chatbot"):
        st.error("The chatbot runtime is unavailable.")
        return None
    return chatbot_module


def show_chatbot() -> None:
    st.title("Chatbot")
    st.caption("A focused conversational assistant for job search, resume guidance, and career support")

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    suggested_prompts = [
        "Find data analyst jobs in Bangalore",
        "Suggest resume improvements for a software engineer",
        "What companies hire Python developers in India?",
    ]
    st.markdown("**Try one of these:**")
    cols = st.columns(3)
    for col, prompt in zip(cols, suggested_prompts):
        with col:
            if st.button(prompt, use_container_width=True):
                st.session_state.chat_messages.append(HumanMessage(content=prompt))
                st.rerun()

    chatbot_module = _load_chatbot_runtime()
    if chatbot_module is None:
        st.info("The chatbot is currently unavailable. Check your environment configuration and try again.")
        return

    for message in st.session_state.chat_messages:
        if isinstance(message, HumanMessage):
            with st.chat_message("user"):
                st.write(message.content)
        elif isinstance(message, ToolMessage):
            with st.chat_message("assistant"):
                st.caption("Tool output")
                st.write(message.content)
        elif isinstance(message, AIMessage):
            with st.chat_message("assistant"):
                st.write(message.content)

    prompt = st.chat_input("Ask about jobs, locations, resume tips, or career advice")
    if prompt:
        st.session_state.chat_messages.append(HumanMessage(content=prompt))
        with st.chat_message("user"):
            st.write(prompt)

        try:
            result = chatbot_module.chatbot.invoke({"messages": st.session_state.chat_messages})
            st.session_state.chat_messages = result.get("messages", st.session_state.chat_messages)
        except Exception as exc:  # pragma: no cover
            st.session_state.chat_messages.append(AIMessage(content=f"I could not process that request right now: {exc}"))
            st.error(f"Unable to run the chatbot: {exc}")

        for message in st.session_state.chat_messages:
            if isinstance(message, HumanMessage):
                continue
            if isinstance(message, ToolMessage):
                with st.chat_message("assistant"):
                    st.caption("Tool output")
                    st.write(message.content)
            elif isinstance(message, AIMessage):
                with st.chat_message("assistant"):
                    st.write(message.content)


def show_company_lookup() -> None:
    st.title("Company Lookup")
    st.caption("Research a company using the pre-built company lookup workflow")

    company_name = st.text_input("Company name")
    if st.button("Research company") and company_name:
        try:
            research = CompanyResearch()
            search_data = research._tavily.search(query=company_name, max_results=8)
            prompt = (
                "You are a company research assistant. Summarize the most important facts from the search data."
                f"\n\nCompany: {company_name}\n\nSearch data:\n{search_data}"
            )
            response = research._llm.invoke(prompt)
            st.success("Company research ready")
            st.text_area("Summary", value=response.content, height=400)
        except Exception as exc:  # pragma: no cover
            st.error(f"Company lookup failed: {exc}")


def show_resume_analyzer() -> None:
    st.title("Resume Analyzer")
    st.caption("Analyze uploaded resumes using the existing PDF parsing approach")

    uploaded_file = st.file_uploader("Upload a PDF resume", type=["pdf"])
    if uploaded_file is None:
        return

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as handle:
        handle.write(uploaded_file.read())
        temp_path = handle.name

    try:
        loader = PyPDFLoader(temp_path)
        pages = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, length_function=len)
        chunks = splitter.split_documents(pages)

        if not chunks:
            st.warning("No content found in the uploaded PDF.")
            return

        combined = "\n\n".join(chunk.page_content for chunk in chunks[:5])
        st.success(f"Parsed {len(pages)} page(s) into {len(chunks)} chunk(s).")
        st.text_area("Analyzed content", value=combined, height=400)
    except Exception as exc:  # pragma: no cover
        st.error(f"Resume analysis failed: {exc}")
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def show_resume_parser() -> None:
    st.title("Resume Parser")
    st.caption("Extract and clean resume text from a PDF file")

    uploaded_file = st.file_uploader("Upload a PDF resume", type=["pdf"])
    if uploaded_file is None:
        return

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as handle:
        handle.write(uploaded_file.read())
        temp_path = handle.name

    try:
        raw_text = text_extractor(temp_path)
        cleaned = clean_text(raw_text)
        st.text_area("Parsed resume text", value=cleaned, height=500)
    except Exception as exc:  # pragma: no cover
        st.error(f"Resume parsing failed: {exc}")
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def main() -> None:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "page" not in st.session_state:
        st.session_state.page = "Dashboard"

    if not st.session_state.authenticated:
        show_login_or_signup()
        return

    with st.sidebar:
        st.markdown("### Navigation")
        st.caption("Premium workspace")
        page = st.radio(
            "Go to",
            ["Dashboard", "Account", "Chatbot", "Company Lookup", "Resume Analyzer", "Resume Parser"],
            index=["Dashboard", "Account", "Chatbot", "Company Lookup", "Resume Analyzer", "Resume Parser"].index(st.session_state.page),
        )
        st.session_state.page = page
        st.markdown("---")
        st.caption(f"Signed in as {st.session_state.user.get('email', 'guest')}")

    if st.session_state.page == "Dashboard":
        show_dashboard()
    elif st.session_state.page == "Account":
        show_account()
    elif st.session_state.page == "Chatbot":
        show_chatbot()
    elif st.session_state.page == "Company Lookup":
        show_company_lookup()
    elif st.session_state.page == "Resume Analyzer":
        show_resume_analyzer()
    else:
        show_resume_parser()


if __name__ == "__main__":
    main()
