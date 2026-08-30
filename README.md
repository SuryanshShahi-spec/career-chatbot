# AI Job Search Agent & Interview Prep Tool

A comprehensive Python-based AI-powered job search assistant with interview preparation, resume analysis, company research, job alerts, and account tools. The application uses a FastAPI backend, a browser frontend, and a LangGraph agent.

## Overview

This project provides a complete job search and career development platform with:
- **Job Search**: Search for live job postings using the Adzuna API
- **Company Research**: AI-powered research and summaries using Tavily Search
- **Resume Tools**: Extract, analyze, and score resumes against job descriptions
- **Interview Preparation**: Mock interviews, STAR method guidance, and question banks
- **User Accounts**: Authentication and profile management with PostgreSQL
- **Dashboard**: Monitoring metrics and project analytics
- **AI Agent**: LangGraph-based conversational agent with multiple tools
- **Browser UI**: Chat, job alerts, and a Tool Desk for direct tool execution

## Key Features

### 🔍 Job Search
- Search live job postings by title, location, and country
- Filter by experience level and results per page
- Integrated with Adzuna API for real-time job data
- Supports multiple country codes (in, uk, us, etc.)

### 🏢 Company Research
- AI-powered company research summaries
- Analyze business overview, tech stack, culture, and hiring signals
- Tavily search integration for up-to-date information
- Practical summaries tailored for job seekers

### 📄 Resume Analysis
- **Resume Extraction**: Extract and clean text from PDF resumes
- **Gap Analysis**: Compare resume against career goals
- **ATS Scoring**: Score resume against job descriptions and identify missing keywords
- **PDF Processing**: Support for multi-page PDFs with text chunking

### 🎤 Interview Preparation (NEW!)
- **Interview Questions**: 40+ questions across 4 categories:
  - Behavioral Questions (tell me about a time...)
  - Technical Questions (for engineers and technical roles)
  - Situational Questions (how would you handle...)
  - Company Culture Questions (why this company, salary expectations, etc.)
  
- **STAR Method Framework**: 
  - Structured guidance for answering behavioral questions
  - Situation, Task, Action, Result components
  - Example stories with metrics
  - Tips for effective delivery
  
- **Mock Interviews**: 
  - Personalized interview questions based on job title and company
  - Tailored distribution by experience level (entry, mid, senior)
  - Role-specific tips and preparation guidance
  
- **Job Description Analysis**: 
  - Extract key skills and responsibilities from job postings
  - Generate targeted interview prep questions
  - Identify critical competencies to emphasize
  
- **Interview Red Flags & Green Flags**:
  - Recognize positive company signals
  - Identify warning signs during interviews
  - Post-interview best practices
  
- **Comprehensive Prep Summaries**:
  - Research phase guidance
  - Self-preparation checklist
  - Day-before and day-of tips
  - Key interview strategies

### 👤 User Accounts
- User registration and authentication
- JWT-based token authentication
- Profile management with contact information
- Secure password handling

## Installation

### Prerequisites
- Python 3.9+
- PostgreSQL (for user accounts)
- pip (Python package manager)

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Job_Search_AI_Agent
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate  # On Windows
   # or
   source .venv/bin/activate  # On Linux/Mac
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file in the root directory with:
   ```env
  GROQ_API_KEY=your_groq_api_key
  GROQ_MODEL=openai/gpt-oss-20b
  ADZUNA_APP_ID=your_adzuna_id
   ADZUNA_API_KEY=your_adzuna_key
   TAVILY_API_KEY=your_tavily_key
   DATABASE_URL=postgresql://user:password@localhost:5432/job_search_db
   ```

5. **Start PostgreSQL** if you use account features or recurring job alerts. The job-alert table is created automatically when the first alert is saved.

## Usage

### Running the Browser App

```bash
\.\.venv\Scripts\python.exe -m uvicorn Agent.app:fastapi_app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` in a browser. If port 8000 is already in use, choose another port, for example `8766`, and open `http://127.0.0.1:8766`.

The browser UI includes:
- Interactive chat with the LangGraph agent
- Job-alert subscription form
- Tool Desk for discovering and invoking every registered tool with JSON arguments

### FastAPI Backend

Run the backend API server:
```bash
.\.venv\Scripts\python.exe -m uvicorn Agent.app:fastapi_app --reload --host 0.0.0.0 --port 8000
```

API endpoints:
- `GET /` - Browser frontend
- `GET /api` - API welcome message
- `GET /health` - Health check
- `POST /chat` - Send message to agent
- `GET /api/tools` - List all registered tools
- `POST /api/tools/{tool_name}` - Invoke a registered tool
- `POST /api/alerts` - Create a recurring job alert

Example request:
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Find Python jobs in Bangalore"}'
```

Invoke a tool directly:
```bash
curl -X POST "http://localhost:8000/api/tools/interview_prep" \\
  -H "Content-Type: application/json" \\
  -d '{"arguments":{"action":"questions","category":"behavioral"}}'
```

### Interview Prep Tool Usage Examples

#### Get Interview Questions
```
"Give me behavioral interview questions"
"Show me technical questions for a software engineer"
"What are common company culture questions?"
```

#### STAR Method Guidance
```
"Explain the STAR method for interviews"
"Help me structure an answer using STAR"
"Show me an example of a good STAR story"
```

#### Mock Interview
```
"Generate a mock interview for Senior Software Engineer at Google"
"Prepare me for a Product Manager interview at Microsoft"
"Create interview questions for a Data Scientist role at entry level"
```

#### Job Description Analysis
```
"Analyze this job description and prepare me for the interview: [paste JD]"
"What should I focus on for this role? [paste job description]"
```

#### Interview Preparation Checklist
```
"Give me a full interview prep guide for Software Engineer at TechCorp"
"What are red flags and green flags I should watch for?"
```

## Project Structure

```
Job_Search_AI_Agent/
├── Agent/
│   ├── app.py              # Main Streamlit + FastAPI application
│   └── app_auth.py         # Authentication helpers
├── Assets/
│   ├── job_search.py       # Job search integration
│   ├── company_lookup.py   # Company research tools
│   ├── resume_parsing.py   # PDF resume extraction
│   ├── resume_analyze.py   # Resume gap analysis
│   ├── resume_a.py         # Resume analyzer helper
│   ├── ats_analyzer.py     # ATS scoring and analysis
│   ├── interview_prep.py   # Interview preparation tool (NEW!)
│   ├── chatbot.py          # Chatbot implementation
│   ├── auth.py             # Authentication service
│   ├── dashboard.py        # Monitoring dashboard
│   ├── monitor.py          # Metrics collection
│   ├── postgre.py          # PostgreSQL connections
│   ├── profile.py          # User profile management
│   ├── scraper.py          # Job scraping
│   ├── errors.py           # Error handling utilities
│   ├── templates/          # HTML templates for login/signup
│   └── __init__.py
├── Data/
│   ├── postgre.py          # Database utilities
│   └── test.py             # Sample test data
├── tests/
│   └── test_fastapi_setup.py
├── logs/                   # Application logs
├── metrics/                # SQLite metrics database
├── requirements.txt        # Project dependencies
├── .env                    # Environment variables (create this)
├── README.md              # This file
├── AUTHENTICATION.md      # Auth documentation
└── LICENSE
```

## Tools Available in Agent

| Tool | Description |
|------|-------------|
| `job_search` | Search for live job postings |
| `company_research` | Research companies and get AI summaries |
| `resume_extract` | Extract text from PDF resumes |
| `resume_gap_analysis` | Analyze resume against career goals |
| `ats_resume_scorer` | Score resume match against job descriptions |
| `interview_prep` | Get interview questions, STAR guidance, and mock interviews |
| `init_database` | Initialize PostgreSQL tables |
| `register_account` | Create new user accounts |
| `login_account` | Authenticate users |
| `get_user_profile` | Retrieve user profile information |
| `update_user_profile` | Update user profile details |
| `show_dashboard` | Display monitoring metrics |
| `save_job_application` | Save a job application |
| `get_job_applications` | Retrieve saved applications |
| `save_job_preferences` | Save job-search preferences |
| `get_job_preferences` | Retrieve job-search preferences |
| `location_based_job_search` | Search across multiple cities |
| `send_email_notification` | Send a one-off job-alert email |
| `salary_research` | Look up salary bands |
| `create_job_alert` | Create a recurring job alert |

## Interview Prep Tool API

### interview_prep() Function

```python
interview_prep(
    action: str,              # Action to perform
    job_title: str = "",      # Position title (for mock interviews)
    company_name: str = "",   # Company name (for mock interviews)
    category: str = "all",    # Question category
    job_description: str = "", # JD text for analysis
    experience_level: str = "mid"  # Experience level (entry/mid/senior)
) -> str
```

**Available Actions**:
- `questions` - Get interview questions by category
- `mock_interview` - Generate personalized mock interview
- `star_guide` - Get STAR method framework
- `analyze_jd` - Analyze job description for prep
- `red_flags` - Get interview red flags & green flags
- `summary` - Generate comprehensive prep summary

## Testing

Run tests to verify setup:
```bash
python -m pytest tests/
```

Run specific test:
```bash
python test_ats.py
```

## Architecture

The application uses:
- **LangGraph**: Agent orchestration and tool management
- **HTML/CSS/JavaScript**: Browser user interface
- **Streamlit**: Optional legacy user interface via `Agent/app.py`
- **FastAPI**: REST API backend
- **Groq LLM**: Language model for AI responses
- **ChromaDB/Vector Search**: Semantic search (if enabled)
- **PostgreSQL**: User data and authentication
- **Tavily**: Web search for company research
- **Adzuna API**: Live job listings

## Environment Variables

Key environment variables needed:

```env
# LLM and Search APIs
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-20b
TAVILY_API_KEY=your_tavily_api_key

# Job Search API
ADZUNA_APP_ID=your_adzuna_id
ADZUNA_API_KEY=your_adzuna_key

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/job_search_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=job_search_db

# Optional: Brightdata for additional job sources
BRIGHTDATA_API_KEY=your_brightdata_key
```

See [AUTHENTICATION.md](AUTHENTICATION.md) for detailed auth setup.

## FAQ

**Q: How do I get API keys?**
- Groq: https://console.groq.com/
- Adzuna: https://developer.adzuna.com/
- Tavily: https://tavily.com/
- Brightdata: https://brightdata.com/

**Q: Can I use this with other job APIs?**
- Yes, the scraper module is extensible. Add new scrapers to `Assets/scraper.py`

**Q: How do I customize interview questions?**
- Edit `Assets/interview_prep.py` and modify `QUESTION_CATEGORIES` dictionary

**Q: Does the STAR method work for all questions?**
- The STAR method works best for behavioral questions. Situational and technical questions may need different approaches.

**Q: Can I export interview prep summaries?**
- Yes, copy the output from the chat interface or use the FastAPI backend to programmatically access results

## Notes

- Keep sensitive environment variables in `.env` file (never commit this)
- Resume PDFs should be in the `Data/` directory
- Job search API calls consume credits - monitor your usage
- The app uses PostgreSQL for user authentication - ensure it's running
- LangGraph agent provides conversational access to all tools
- Interview prep tool works with or without a resume/job description

## License

See [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues, questions, or feature requests, please create an issue in the repository.

---

**Built with ❤️ for job seekers and career development**
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
