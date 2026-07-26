"""
job-agent-backend/agent_api/agent.py
-------------------------------------
Main agent entry point.

Initialises a ReAct agent (LangGraph) backed by Groq LLaMA-3.3-70B
and binds the three custom tools:
  • job_search_tool       — search live job listings (Adzuna + Tavily)
  • company_research_tool — deep-dive company intelligence
  • resume_parser_tool    — PDF → structured profile
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

# Make the repo root importable so `tools/` can be found
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
def load_env() -> str:
    env_path = REPO_ROOT / ".env"
    load_dotenv(dotenv_path=env_path)
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise ValueError("Missing GROQ_API_KEY. Please set it in your .env file.")
    return groq_key


groq_key = load_env()

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=groq_key,
)

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
from tools import ALL_TOOLS   # noqa: E402  (imported after sys.path setup)

# ---------------------------------------------------------------------------
# ReAct Agent
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are an intelligent Job Search Assistant.

You have access to the following tools:
1. job_search_tool        — find live job listings by title, location, salary, remote etc.
2. company_research_tool  — research a company's culture, salaries, interview process and news.
3. resume_parser_tool     — parse a PDF resume and extract a structured profile.

Guidelines:
- For job searches: use job_search_tool with clear filters.
- For "tell me about <Company>": use company_research_tool.
- For "parse my resume" or when a PDF path is provided: use resume_parser_tool.
- Combine tools when appropriate (e.g. search jobs, then research each company).
- Always present results in a clean, readable format.
- If you don't have enough information to call a tool, ask the user for clarification.
"""

agent_executor = create_react_agent(
    model=llm,
    tools=ALL_TOOLS,
    prompt=SYSTEM_PROMPT,
)

# ---------------------------------------------------------------------------
# Convenience wrapper — kept for backward compatibility
# ---------------------------------------------------------------------------
def parse_job_query(user_prompt: str) -> dict:
    """
    Legacy helper: extract job search filters from a natural-language prompt.
    Calls the agent and returns the first tool result as a dict.
    """
    system_instruction = (
        "Extract job search filters from the user request. "
        "Provide your output as a JSON object with keys: "
        "title, location, remote (boolean), min_salary (integer or null)."
    )
    response = llm.invoke([
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_prompt},
    ])
    return json.loads(response.content)


def run_agent(user_message: str) -> str:
    """
    Run the full ReAct agent with all tools and return the final response text.
    """
    result = agent_executor.invoke({
        "messages": [{"role": "user", "content": user_message}]
    })
    # The last message in the list is the final assistant response
    messages = result.get("messages", [])
    return messages[-1].content if messages else "No response generated."


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_cases = [
        "Find me remote Python developer jobs in Bangalore",
        "Research Google as a company — culture, salary and interview process",
    ]
    for prompt in test_cases:
        print(f"\n{'='*60}")
        print(f"USER: {prompt}")
        print(f"{'='*60}")
        response = run_agent(prompt)
        print(f"AGENT:\n{response}")
