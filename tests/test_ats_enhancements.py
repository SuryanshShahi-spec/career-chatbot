from Assets.ats_analyzer import build_keyword_optimization, analyze_skills_gap


def test_keyword_optimization_prioritizes_missing_job_keywords():
    resume = "Python developer with SQL, pandas, and REST APIs. Built dashboards using Streamlit."
    job_description = "Looking for a Python developer with FastAPI, Docker, Kubernetes, AWS, and SQL experience."

    optimization = build_keyword_optimization(resume, job_description)

    assert "fastapi" in optimization["recommended_keywords"]
    assert optimization["score"] >= 0
    assert optimization["missing_keywords"]


def test_skills_gap_analysis_returns_actionable_recommendations():
    resume = "Python, SQL, Excel, and basic statistics."
    job_description = "Data Analyst with Python, SQL, Tableau, A/B testing, and machine learning pipeline experience."

    gap = analyze_skills_gap(resume, job_description)

    assert "skills_missing" in gap
    assert isinstance(gap["learning_recommendations"], list)
    assert gap["learning_recommendations"]
