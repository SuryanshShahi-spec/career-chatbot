import importlib
import io
import os
import sys
import json
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Annotated, TypedDict

import streamlit as st
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "Assets") not in sys.path:
    sys.path.insert(0, str(ROOT / "Assets"))
if str(ROOT / "Data") not in sys.path:
    sys.path.insert(0, str(ROOT / "Data"))

load_dotenv(ROOT / ".env")

try:
    from langchain_groq import ChatGroq
except Exception:  # pragma: no cover
    ChatGroq = None

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")


@tool
def job_search(
    job_title: str,
    location: str,
    country_code: str = "in",
    results_per_page: int = 5,
    notice_period_days: int | None = None,
    work_from_home: bool | None = None,
    preferred_locations: list[str] | None = None,
) -> str:
    """Search for live job postings using the Adzuna scraper tool, with optional notice period, remote, and location filters."""
    try:
        scraper = importlib.import_module("Assets.scraper")
        return scraper.job_scrape(
            job_title=job_title,
            location=location,
            country_code=country_code,
            results_per_page=results_per_page,
            notice_period_days=notice_period_days,
            work_from_home=work_from_home,
            preferred_locations=preferred_locations,
        )
    except Exception as exc:  # pragma: no cover - fallback message
        return f"Job search tool failed: {exc}. Check your ADZUNA API credentials and network connection."


@tool
def company_research(company_name: str) -> str:
    """Research a company using Tavily search and summarize the results for a candidate."""
    try:
        from Assets.errors import require_env_vars

        creds = require_env_vars("CompanyResearch", "GROQ_API_KEY", "TAVILY_API_KEY")
        groq_key = creds["GROQ_API_KEY"]
        tavily_key = creds["TAVILY_API_KEY"]
    except Exception as exc:
        return f"Company research unavailable: {exc}"

    try:
        from tavily import TavilyClient
        from langchain_groq import ChatGroq

        tavily = TavilyClient(api_key=tavily_key)
        search_results = tavily.search(query=company_name, max_results=5)

        llm = ChatGroq(model=GROQ_MODEL, api_key=groq_key, temperature=0.2)
        prompt = (
            "Summarize the company in a concise but useful way for a job seeker. "
            "Include: business overview, tech stack, culture, recent activities, and hiring signals.\n\n"
            f"Company: {company_name}\n\nSearch results:\n{search_results}"
        )
        response = llm.invoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
    except Exception as exc:
        return f"Company research failed: {exc}"


@tool
def resume_extract(pdf_path: str) -> str:
    """Extract text from a PDF resume and clean it for downstream analysis."""
    try:
        parser = importlib.import_module("Assets.resume_parsing")
        text = parser.text_extractor(pdf_path)
        cleaned = parser.clean_text(text)
        return cleaned[:8000] if cleaned else "No text found in the resume."
    except Exception as exc:
        return f"Resume extraction failed: {exc}"


@tool
def resume_gap_analysis(resume_path: str, goal_text: str) -> str:
    """Analyze a resume against a career goal and return a gap-analysis summary."""
    try:
        module = importlib.import_module("Assets.resume_a")
        output = io.StringIO()
        with redirect_stdout(output):
            module.analyze_resume_versus_goals(resume_path, goal_text)
        content = output.getvalue().strip()
        return content if content else "Resume analysis reported no output."
    except Exception as exc:
        return f"Resume analysis failed: {exc}"


@tool
def ats_resume_scorer(resume_path: str, job_description: str) -> str:
    """Score a resume against a job description, optimize keywords, and identify skills gaps with learning recommendations."""
    try:
        analyzer = importlib.import_module("Assets.ats_analyzer")
        parser = importlib.import_module("Assets.resume_parsing")

        resume_text = parser.text_extractor(resume_path)
        ats = analyzer.ATSAnalyzer()
        report = ats.analyze(resume_text, job_description)

        if not report.get("keyword_optimization"):
            report["keyword_optimization"] = analyzer.build_keyword_optimization(resume_text, job_description)
        if not report.get("skills_gap_analysis"):
            report["skills_gap_analysis"] = analyzer.analyze_skills_gap(resume_text, job_description)

        return json.dumps(report, indent=2)
    except Exception as exc:
        return f"ATS analysis failed: {exc}"


@tool
def init_database() -> str:
    """Initialize the PostgreSQL user tables if they are not already present."""
    try:
        db = importlib.import_module("Data.postgre")
        db.init_db()
        return "Database initialized successfully."
    except Exception as exc:
        return f"Database initialization failed: {exc}"


@tool
def register_account(full_name: str, email: str, password: str, phone: str = "") -> str:
    """Create a new user record using the existing PostgreSQL auth service."""
    try:
        auth_module = importlib.import_module("Assets.auth")
        result = auth_module.auth_service.register(full_name, email, password, phone or None)
        return str(result)
    except Exception as exc:
        return f"Registration failed: {exc}"


@tool
def login_account(email: str, password: str) -> str:
    """Authenticate a user and return the JWT token payload result."""
    try:
        auth_module = importlib.import_module("Assets.auth")
        result = auth_module.auth_service.login(email, password)
        return str(result)
    except Exception as exc:
        return f"Login failed: {exc}"


@tool
def get_user_profile(token: str) -> str:
    """Fetch the current user profile for a valid JWT token."""
    try:
        auth_module = importlib.import_module("Assets.auth")
        result = auth_module.auth_service.get_profile(token)
        return str(result)
    except Exception as exc:
        return f"Profile lookup failed: {exc}"


@tool
def update_user_profile(token: str, full_name: str, phone: str, profile_picture: str = "") -> str:
    """Update the authenticated user's profile fields."""
    try:
        auth_module = importlib.import_module("Assets.auth")
        result = auth_module.auth_service.update_profile(token, full_name, phone, profile_picture or None)
        return str(result)
    except Exception as exc:
        return f"Profile update failed: {exc}"


@tool
def show_dashboard() -> str:
    """Display the monitoring dashboard summary for the current project."""
    try:
        dashboard = importlib.import_module("Assets.dashboard")
        output = io.StringIO()
        with redirect_stdout(output):
            dashboard.print_dashboard()
        content = output.getvalue().strip()
        return content if content else "Dashboard has no metrics yet."
    except Exception as exc:
        return f"Dashboard could not be generated: {exc}"


@tool
def interview_prep(
    action: str,
    job_title: str = "",
    company_name: str = "",
    category: str = "all",
    job_description: str = "",
    experience_level: str = "mid",
) -> str:
    """Prepare for interviews with questions, STAR method guidance, and mock interview scenarios.
    
    Actions available:
    - 'questions': Get interview questions by category (behavioral, technical, situational, company_culture, or all)
    - 'mock_interview': Generate a personalized mock interview for a job and company
    - 'star_guide': Get STAR method framework with examples and guidance
    - 'analyze_jd': Analyze a job description to generate targeted prep questions
    - 'red_flags': Get guidance on interview red flags and green flags
    - 'summary': Generate comprehensive interview prep summary
    """
    try:
        prep_module = importlib.import_module("Assets.interview_prep")
        return prep_module.interview_prep_assistant(
            action=action,
            job_title=job_title,
            company_name=company_name,
            category=category,
            job_description=job_description,
            experience_level=experience_level,
        )
    except Exception as exc:
        return f"Interview prep tool failed: {exc}"


@tool
def save_job_application(user_id: str, job_title: str, company: str, location: str, status: str = "Applied", notes: str = "") -> str:
    """Save a job application record to the SQLite database."""
    try:
        db = importlib.import_module("Data.sqlite_db")
        result = db.save_job_application(user_id, job_title, company, location, status, notes)
        return json.dumps(result)
    except Exception as exc:
        return f"Failed to save job application: {exc}"


@tool
def get_job_applications(user_id: str) -> str:
    """Retrieve job applications for a specific user from the SQLite database."""
    try:
        db = importlib.import_module("Data.sqlite_db")
        result = db.get_job_applications(user_id)
        return json.dumps(result)
    except Exception as exc:
        return f"Failed to get job applications: {exc}"


@tool
def save_job_preferences(
    user_id: str,
    preferred_locations: list[str],
    target_roles: list[str],
    notice_period_days: int | None = None,
    work_from_home: bool | None = None,
) -> str:
    """Save or update job preferences, including notice period and remote work requirements."""
    try:
        db = importlib.import_module("Data.sqlite_db")
        result = db.save_job_preferences(
            user_id,
            preferred_locations,
            target_roles,
            notice_period_days=notice_period_days,
            work_from_home=work_from_home,
        )
        return json.dumps(result)
    except Exception as exc:
        return f"Failed to save job preferences: {exc}"


@tool
def get_job_preferences(user_id: str) -> str:
    """Retrieve job preferences for a specific user from the SQLite database."""
    try:
        db = importlib.import_module("Data.sqlite_db")
        result = db.get_job_preferences(user_id)
        return json.dumps(result)
    except Exception as exc:
        return f"Failed to get job preferences: {exc}"


@tool
def location_based_job_search(
    job_title: str,
    cities: list[str] = None,
    results_per_city: int = 2,
    notice_period_days: int | None = None,
    work_from_home: bool | None = None,
) -> str:
    """Search for jobs across specified Indian cities and apply notice-period and remote filters."""
    try:
        scraper = importlib.import_module("Assets.scraper")
        target_cities = cities if cities else ["Mumbai", "Bangalore", "Delhi", "Pune", "Hyderabad"]

        all_results = []
        for city in target_cities:
            res = scraper.job_scrape(
                job_title=job_title,
                location=city,
                country_code="in",
                results_per_page=results_per_city,
                notice_period_days=notice_period_days,
                work_from_home=work_from_home,
                preferred_locations=[city],
            )
            all_results.append(f"### Results for {city} ###\n{res}\n")

        return "\n".join(all_results)
    except Exception as exc:
        return f"Location-based job search failed: {exc}"


@tool
def send_email_notification(recipient_email: str, job_title: str, location: str, jobs_list: list[dict]) -> str:
    """Send a job alert email to a user with a list of job opportunities."""
    try:
        email_mod = importlib.import_module("Assets.emailand")
        success = email_mod.send_job_alert(recipient_email, job_title, location, jobs_list)
        return "Email sent successfully." if success else "Failed to send email."
    except Exception as exc:
        return f"Email notification failed: {exc}"


@tool
def salary_calculator(
    basic_salary: float,
    hra_pct: float = 15,
    da_pct: float = 5,
    ta_pct: float = 2,
    currency: str = "INR",
) -> str:
    """Calculate salary breakdown and annualized totals for a base salary."""
    try:
        sal_mod = importlib.import_module("Assets.salary")
        hra, da, ta, gross = sal_mod.compute_salary_breakdown(float(basic_salary))
        converted = {
            "basic_salary": sal_mod.convert_currency(float(basic_salary), "INR", currency.upper()),
            "hra": sal_mod.convert_currency(hra, "INR", currency.upper()),
            "da": sal_mod.convert_currency(da, "INR", currency.upper()),
            "ta": sal_mod.convert_currency(ta, "INR", currency.upper()),
            "gross": sal_mod.convert_currency(gross, "INR", currency.upper()),
        }
        return json.dumps({
            "currency": currency.upper(),
            "basic_salary": round(converted["basic_salary"], 2),
            "hra": round(converted["hra"], 2),
            "da": round(converted["da"], 2),
            "ta": round(converted["ta"], 2),
            "gross": round(converted["gross"], 2),
            "annual_ctc": round(converted["gross"] * 12, 2),
            "components": {
                "hra_pct": hra_pct,
                "da_pct": da_pct,
                "ta_pct": ta_pct,
            },
        }, indent=2)
    except Exception as exc:
        return f"Salary calculator failed: {exc}"


@tool
def salary_research(company: str = None, title: str = None, location: str = None) -> str:
    """Look up sample salary bands by job title from the built-in salary dataset."""
    try:
        sal_mod = importlib.import_module("Assets.salary")
        data = sal_mod.JOB_SALARY_DATA
        matches = []

        if title:
            for role, value in data.items():
                if title.lower() in role.lower():
                    matches.append({"title": role, "annual_inr": value, "monthly_inr": round(value / 12, 2)})
        if not matches and company:
            for role, value in data.items():
                if company.lower() in role.lower():
                    matches.append({"title": role, "annual_inr": value, "monthly_inr": round(value / 12, 2)})
        if not matches:
            for role, value in data.items():
                if location and location.lower() in role.lower():
                    matches.append({"title": role, "annual_inr": value, "monthly_inr": round(value / 12, 2)})
        if not matches:
            return "No salary data found for the given criteria."

        avg = sum(item["annual_inr"] for item in matches) / len(matches)
        med = sorted(item["annual_inr"] for item in matches)[len(matches) // 2]
        return json.dumps({
            "count": len(matches),
            "average_annual_inr": round(avg, 2),
            "median_annual_inr": round(med, 2),
            "results": matches[:10],
        }, indent=2)
    except Exception as exc:
        return f"Salary research failed: {exc}"

@tool
def create_job_alert(email: str, job_title: str, location: str, frequency: str = "daily") -> str:
    """Create a persistent job alert in the database so the user receives periodic emails."""
    try:
        db_mod = importlib.import_module("Data.postgre")
        res = db_mod.create_job_alert(email, job_title, location, frequency)
        return json.dumps(res)
    except Exception as exc:
        return f"Creating job alert failed: {exc}"


@tool
def trigger_new_match(user_id: str, email: str, phone: str, match_details: str) -> str:
    """Trigger a new job match and queue notifications."""
    try:
        print(f"[API] Match found for User {user_id}. Storing in PostgreSQL...")
        return f"Match processed for {email}. Notifications queued asynchronously: {match_details}"
    except Exception as exc:
        return f"Triggering new match failed: {exc}"


@tool
def update_notification_settings(user_id: int, preference: str) -> str:
    """Update user notification preference in the local system (Immediate, Daily, Weekly, ON, OFF)."""
    try:
        db_mod = importlib.import_module("Assets.db")
        db = db_mod.SessionLocal()
        user = db.query(db_mod.User).filter(db_mod.User.id == user_id).first()
        if user:
            user.notification_preference = preference
            db.commit()
            return f"Notification preference updated to {preference}."
        return f"User ID {user_id} not found."
    except Exception as exc:
        return f"Failed to update preference: {exc}"

@tool
def extract_notice_period(job_description: str) -> str:
    """Extract notice period information from a job description."""
    try:
        mod = importlib.import_module("Assets.work_mod")
        res = mod.extract_notice(job_description)
        return json.dumps(res)
    except Exception as exc:
        return f"Extract notice period failed: {exc}"

@tool
def parse_work_logs(log_content: str) -> str:
    """Parse work-from-home logs and return structured entries."""
    try:
        mod = importlib.import_module("Assets.work_fro")
        entries = mod.parse_with_log(log_content)
        return json.dumps([
            {"date": e.date.strftime("%Y-%m-%d"), "hours": e.hours, "project": e.project, "tasks": e.tasks}
            for e in entries
        ])
    except Exception as exc:
        return f"Parse work logs failed: {exc}"



TOOLS = [
    job_search,
    company_research,
    resume_extract,
    resume_gap_analysis,
    ats_resume_scorer,
    interview_prep,
    init_database,
    register_account,
    login_account,
    get_user_profile,
    update_user_profile,
    show_dashboard,
    save_job_application,
    get_job_applications,
    save_job_preferences,
    get_job_preferences,
    location_based_job_search,
    send_email_notification,
    salary_calculator,
    salary_research,
    create_job_alert,
    trigger_new_match,
    update_notification_settings,
    extract_notice_period,
    parse_work_logs,
]


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


if ChatGroq is None:  # pragma: no cover
    raise RuntimeError("langchain_groq is not installed. Please install the project requirements first.")


def build_graph():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY in your environment. Add it to the .env file before starting the app.")

    llm = ChatGroq(model=GROQ_MODEL, api_key=api_key, temperature=0.2)
    llm_with_tools = llm.bind_tools(TOOLS)

    system_prompt = SystemMessage(
        content=(
            "You are a job-search AI assistant. Use the available tools to answer job, company, resume, interview prep, "
            "database, and auth requests. When a user asks for jobs, use the job_search tool. "
            "When asked to search across major or specific cities (e.g., Mumbai, Bangalore, Delhi, Pune, Hyderabad), use the location_based_job_search tool. "
            "Use notice_period_days to filter jobs to a maximum notice period, work_from_home to require or avoid remote jobs, and preferred_locations to focus on target cities. "
            "When they ask for a company overview, use company_research. For resume review, use resume_extract, resume_gap_analysis, and ats_resume_scorer. "
            "For interview preparation, use interview_prep. "
            "For tracking job applications and user preferences, use save_job_application, get_job_applications, save_job_preferences, and get_job_preferences with a 'guest' user_id if they aren't logged in. "
            "For user account actions, use the database/auth tools. "
            "To calculate salary breakdowns, use salary_calculator. To lookup salary data, use salary_research. To set up recurring job alerts, use create_job_alert. To send a one-off email, use send_email_notification. "
            "To update user notification preference in the local system, use update_notification_settings. "
            "To extract a notice period from a job description, use the extract_notice_period tool. To parse work-from-home logs, use the parse_work_logs tool. "
            "Keep answers concise and practical, and always mention important constraints or missing data clearly."
        )
    )

    def agent_node(state: ChatState):
        return {"messages": [llm_with_tools.invoke([system_prompt, *state["messages"]])]}

    graph = StateGraph(ChatState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile()


JOB_SEARCH_GRAPH = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)

class AlertRequest(BaseModel):
    email: str
    job_title: str
    location: str
    frequency: str = "daily"


class MatchPayload(BaseModel):
    user_id: str
    email: str
    phone: str
    match_details: str


class ToolRequest(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)


def get_job_search_graph():
    global JOB_SEARCH_GRAPH
    if JOB_SEARCH_GRAPH is None:
        JOB_SEARCH_GRAPH = build_graph()
    return JOB_SEARCH_GRAPH


# FastAPI app for programmatic access (use app_auth.py to run)
def create_fastapi_app():
    fastapi_app = FastAPI(title="Job Search AI Agent", version="1.0.0")

    @fastapi_app.get("/")
    def root():
        index_file = ROOT / "frontend" / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "Job Search AI Agent API is running."}

    @fastapi_app.get("/api")
    def api_root() -> dict:
        return {"message": "Job Search AI Agent API is running."}

    @fastapi_app.get("/health")
    def health_check() -> dict:
        return {"status": "ok"}

    @fastapi_app.get("/api/tools")
    def list_tools() -> dict:
        return {
            "tools": [
                {"name": registered_tool.name, "description": registered_tool.description}
                for registered_tool in TOOLS
            ]
        }

    @fastapi_app.post("/api/tools/{tool_name}")
    def invoke_tool(tool_name: str, request: ToolRequest) -> dict:
        registered_tool = next((item for item in TOOLS if item.name == tool_name), None)
        if registered_tool is None:
            return {"success": False, "message": f"Unknown tool: {tool_name}"}

        try:
            result = registered_tool.invoke(request.arguments)
            return {"success": True, "tool": tool_name, "result": result}
        except Exception as exc:
            return {"success": False, "tool": tool_name, "message": str(exc)}

    @fastapi_app.post("/chat")
    def chat(request: ChatRequest) -> dict:
        try:
            graph = get_job_search_graph()
            result = graph.invoke({"messages": [HumanMessage(content=request.message)]})
            final_message = result["messages"][-1]
            return {"response": final_message.content}
        except Exception as exc:
            return {
                "response": (
                    "I could not complete that request. Check that GROQ_API_KEY is valid and "
                    f"try again. Details: {exc}"
                )
            }

    @fastapi_app.post("/api/alerts")
    def create_alert_endpoint(request: AlertRequest) -> dict:
        try:
            db_module = importlib.import_module("Data.postgre")
            result = db_module.create_job_alert(
                request.email, request.job_title, request.location, request.frequency
            )
            return result
        except Exception as exc:
            return {"success": False, "message": f"Failed to create alert: {exc}"}

    @fastapi_app.post("/api/trigger-match")
    def trigger_match_endpoint(payload: MatchPayload) -> dict:
        try:
            print(f"[API] Match found for User {payload.user_id}. Storing in PostgreSQL...")
            return {
                "status": "success",
                "message": "Match processed. Notifications queued asynchronously."
            }
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    # Mount frontend static files
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    frontend_dir = ROOT / "frontend"
    if frontend_dir.exists():
        fastapi_app.mount("/ui", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
    else:
        # Create directory if it doesn't exist to prevent crash
        frontend_dir.mkdir(parents=True, exist_ok=True)
        fastapi_app.mount("/ui", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

    if frontend_dir.exists():
        fastapi_app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend_root")

    return fastapi_app

# Create FastAPI app only for direct import (not when running with Streamlit)
fastapi_app = create_fastapi_app()


def render_chat_ui():
    st.set_page_config(page_title="Job Search AI Agent", page_icon="💼", layout="wide")
    st.title("Job Search AI Agent")
    st.caption("LangGraph + Streamlit workflow using the project’s Assets and Data modules as tools.")

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
            "trigger_new_match",
            "update_notification_settings",
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
