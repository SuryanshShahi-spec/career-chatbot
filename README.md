<<<<<<< HEAD
# Job Search Assistant

A Streamlit-based job search assistant with authentication, a monitoring dashboard, and tools for chatbot job search, company lookup, and resume parsing/analyzing.

## What the app includes
- Login and sign-up flow
- Dashboard with monitoring metrics
- Sidebar navigation for:
  - Account
  - Chatbot
  - Company lookup
  - Resume analyzer
  - Resume parser

## Main entry point
Run the app with:
- .\.venv\Scripts\python.exe -m streamlit run app.py

## Project structure
- Assets/: reusable job search tools and helpers
- Data/: sample data and uploaded resume files
- metrics/: SQLite monitoring database

## Notes
- Keep sensitive environment variables in a local .env file.
- The app uses the existing modules in Assets as the underlying tools without modifying them.
=======
# AI Job Search Chatbot — Repository Analysis

This repository contains a Python-based job search assistant project with several related components:
- an AI-powered job search UI
- a local semantic search / retrieval pipeline
- custom LangChain tools for jobs, company research, and resume parsing
- a backend agent API that binds those tools into a single conversational agent
- auxiliary data scraping, Redis caching, and database helpers

---

## Project Overview

The codebase is organized into several main areas:

1. `ai_job_s/` — primary application code and Streamlit UI
2. `tools/` — self-contained LangChain tools for use by an agent
3. `job-agent-backend/` — a separate agent API project that imports the tools and exposes a ReAct-style agent
4. `authenti/` — an authentication helper module
5. `data/` — job data CSV source
6. `chroma_db/` — persisted vector database folder used by the semantic search agent
7. `test/` — test files for validating the cache, tools, and database tooling

---

## Root Files

- `README.md`
  - existing repository readme with installation and feature notes.
  - currently contains merged or duplicated content from multiple variants.

- `requirements.txt`
  - dependency list required by the repository.
  - includes Streamlit, LangChain, ChromaDB, Groq, Google Generative AI, Redis, and related libraries.

---

## `ai_job_s/` Directory

This directory contains the main application modules and a simple UI.

### `ai_job_s/app.py`
- Defines `JobSearchUI`, a basic Streamlit UI for job search.
- Provides inputs for query, location, experience, and salary.
- Displays a hard-coded example results table.
- Acts as a lightweight UI-only entry point when run directly.

### `ai_job_s/backend.py`
- Implements the `Correct` class, a job search agent using LangGraph.
- Uses `ChatGroq`, `GoogleGenerativeAIEmbeddings`, and `TavilySearch`.
- Builds a workflow that reformulates queries, retrieves ChromaDB documents, grades relevance, optionally performs web search fallback, and generates answers.
- Includes `run_ui()` for a Streamlit frontend connected to the backend.

### `ai_job_s/chatbot.py`
- Implements `JobSearchAgent`, a corrective RAG chatbot with query reformulation.
- Creates or loads a Chroma vector store from `data/jobs.csv`.
- Retrieves top-k job documents, grades relevance, and optionally falls back to Tavily web search.
- Generates an answer with a Groq LLM prompt using retrieved context.

### `ai_job_s/search.py`
- Provides Redis-backed caching for search queries.
- Defines `get_search_results(query)` and `database_search_simulation(query)`.
- Demonstrates cache hit/miss semantics with a simple simulated database.

### `ai_job_s/scraper.py`
- Contains an Adzuna scraper to collect job listings and save them to CSV.
- Supports CLI flags for query, location, country, page count, and output path.
- Maps raw Adzuna API fields into a normalized CSV schema.

### `ai_job_s/database.py`
- Connects to PostgreSQL using `psycopg2` and environment variables.
- Serves as a simple DB connectivity example.

### `ai_job_s/my_redis.py`
- Creates a Redis client configured for `localhost:6379`.
- Used by `ai_job_s/search.py` for caching examples.

### `ai_job_s/redis_test.py`
- Tests Redis connectivity by setting and reading a temporary key.

---

## `authenti/` Directory

### `authenti/register.py`
- A placeholder authentication helper module.
- Contains minimal skeleton code and no active web auth service.

---

## `tools/` Directory

This directory contains custom LangChain tools plus a registry used by the backend agent.

### `tools/job_search_tool.py`
- Implements a LangChain tool for live job search using Adzuna and Tavily.
- Accepts structured inputs like title, location, remote, min_salary, max_results, and country.
- Returns JSON-formatted job listings.
- Falls back to Tavily search when Adzuna results are unavailable.

### `tools/company_research_tool.py`
- Implements a company research tool for job seekers.
- Uses Tavily web search to gather information on culture, salary, interview process, tech stack, and news.
- Synthesizes results into a structured JSON report using Groq LLM.

### `tools/resume_parser_tool.py`
- Implements a PDF resume parser tool.
- Extracts text with `pypdf`, performs regex-based contact info extraction, and optionally enriches the resume with a Groq LLM.
- Produces structured JSON containing name, email, phone, skills, experience, education, certifications, projects, and ATS keywords.

### `tools/__init__.py`
- Registers tool exports and provides `ALL_TOOLS` for agent integration.
- Makes the tools easy to import as a single package.

---

## `job-agent-backend/` Directory

This directory houses a separate agent backend that binds all the tools into a single conversational assistant.

### `job-agent-backend/agent_api/agent.py`
- Main entry point for the backend agent.
- Loads environment variables and initializes `ChatGroq`.
- Imports `ALL_TOOLS` and creates a ReAct agent via `create_react_agent()`.
- Provides `run_agent(user_message)` to execute the agent and return the final response.
- Includes a legacy `parse_job_query()` helper for structured job filter extraction.

### `job-agent-backend/agent_core/settings.py`
- Minimal Django-style settings listing installed apps.
- Indicates a planned web backend or Django integration.

---

## `data/` Directory

- `data/jobs.csv`
  - Primary job dataset used by the AI search agents.
  - Contains job listing fields such as title, company, location, salary, description, and optionally apply links.

---

## `chroma_db/` Directory

- Stores persisted Chroma vector database data.
- Used by `ai_job_s/chatbot.py` and `ai_job_s/backend.py` for semantic retrieval.
- Not a Python module but a runtime artifacts directory.

---

## `test/` Directory

### `test/test_search.py`
- Verifies Redis cache behavior for search results.
- Ensures cache miss fetches fresh data and cache hit returns stored data.

### `test/test_tools.py`
- Smoke tests for `job_search_tool`, `company_research_tool`, and `resume_parser_tool`.
- Confirms tool importability, JSON response shape, and error handling.
- Checks registry export of `ALL_TOOLS`.

### `test/test_database.py`
- Validates access to the local `jobs.csv` dataset.
- Tests Google Gemini embeddings and local Chroma vector store retrieval.
- Serves as a health-check for the AI retrieval pipeline.

---

## Key Observations

- The repository includes multiple job search implementations and a reusable toolset.
- `ai_job_s/app.py` is a simple Streamlit frontend demo.
- `ai_job_s/backend.py` and `ai_job_s/chatbot.py` contain the richer AI/LLM retrieval workflows.
- `tools/` is the most reusable package layer, exposing job search, company research, and resume parsing as LangChain tools.
- `job-agent-backend/` is the agent integration layer that combines tools into a single conversational assistant.
- Some files are sample scripts or connectivity tests rather than fully developed production components.

---

## Environment Notes

- The code expects a `.env` file in the project root.
- Useful environment variables include:
  - `GROQ_API_KEY`
  - `GOOGLE_API_KEY`
  - `ADZUNA_APP_ID`
  - `ADZUNA_API_IKEY`
  - `TAVILY_API_KEY`
  - PostgreSQL vars for `ai_job_s/database.py`
- Redis is expected to run locally for `ai_job_s/search.py` and `ai_job_s/redis_test.py`.

---

## Recommended Next Steps

- Choose a single main app entry point and consolidate duplicate modules.
- Replace conflicting README content with this single, consistent documentation.
- Document the `.env` schema and the CSV file structure.
- Add usage examples for the primary agent and each tool.

>>>>>>> 98d70a303e60dd24448c4cbca4f59a10bbf6a43b
