import json
import re
from typing import Dict, Any

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    TfidfVectorizer = None
    cosine_similarity = None

try:
    from Assets.resume_parsing import extract_entities, clean_text, nlp
except ImportError:
    clean_text = lambda x: x
    extract_entities = lambda x: {}
    nlp = None

STOP_WORDS = {
    "and", "the", "with", "for", "from", "that", "this", "your", "will", "are", "have",
    "should", "must", "into", "about", "their", "them", "have", "been", "would", "could",
    "experience", "experience", "job", "role", "work", "skills", "team", "teams", "candidate",
    "looking", "strong", "using", "years", "year"
}


def normalize_keyword_token(token: str) -> str:
    return re.sub(r"[^a-z0-9+#./-]", "", token.lower().strip())


def extract_technical_keywords(text: str) -> set[str]:
    if not text:
        return set()
    words = set(re.findall(r"[a-zA-Z][a-zA-Z0-9+#./-]{2,}", text.lower()))
    return {normalize_keyword_token(w) for w in words if normalize_keyword_token(w) and normalize_keyword_token(w) not in STOP_WORDS}


def build_keyword_optimization(resume_text: str, job_description: str) -> dict:
    resume_keywords = extract_technical_keywords(resume_text)
    jd_keywords = extract_technical_keywords(job_description)
    missing = sorted(jd_keywords - resume_keywords)
    matched = sorted(jd_keywords & resume_keywords)

    if not jd_keywords:
        return {"score": 0.0, "missing_keywords": [], "recommended_keywords": [], "matched_keywords": []}

    score = round((len(matched) / len(jd_keywords)) * 100, 2)
    recommended = missing[:15]
    return {
        "score": score,
        "missing_keywords": missing,
        "recommended_keywords": recommended,
        "matched_keywords": matched,
    }


def analyze_skills_gap(resume_text: str, job_description: str) -> dict:
    resume_keywords = extract_technical_keywords(resume_text)
    jd_keywords = extract_technical_keywords(job_description)
    missing = sorted(jd_keywords - resume_keywords)

    recommendations = []
    if missing:
        for keyword in missing[:8]:
            recommendations.append(f"Learn or add proficiency in {keyword} to improve alignment with the target role.")

    return {
        "skills_missing": missing,
        "learning_recommendations": recommendations,
        "resume_coverage": round((len(jd_keywords & resume_keywords) / max(len(jd_keywords), 1)) * 100, 2),
    }


class ATSAnalyzer:
    """Analyzes a resume against a job description using NLP and TF-IDF."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english', lowercase=True)

    def extract_keywords(self, text: str) -> set:
        """Extract keywords using Spacy noun chunks and entities."""
        if nlp is None:
            return extract_technical_keywords(text)

        doc = nlp(text)
        keywords = set()
        for ent in doc.ents:
            if ent.label_ not in ("DATE", "TIME", "PERCENT", "MONEY", "QUANTITY", "ORDINAL", "CARDINAL"):
                keywords.add(ent.text.lower())

        for chunk in doc.noun_chunks:
            cleaned = chunk.text.strip().lower()
            if len(cleaned) > 2 and not all(c in '0123456789' for c in cleaned):
                keywords.add(cleaned)

        return {normalize_keyword_token(k) for k in keywords if normalize_keyword_token(k)}

    def calculate_match_score(self, resume_text: str, jd_text: str) -> float:
        """Calculate TF-IDF cosine similarity between resume and JD."""
        if TfidfVectorizer is None:
            return 0.0

        try:
            tfidf_matrix = self.vectorizer.fit_transform([resume_text, jd_text])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return round(similarity * 100, 2)
        except Exception:
            return 0.0

    def analyze(self, resume_text: str, jd_text: str) -> Dict[str, Any]:
        """Perform full ATS analysis and return a structured report."""
        cleaned_resume = clean_text(resume_text)
        cleaned_jd = clean_text(jd_text)

        score = self.calculate_match_score(cleaned_resume, cleaned_jd)

        resume_keywords = self.extract_keywords(cleaned_resume)
        jd_keywords = self.extract_keywords(cleaned_jd)

        resume_words = set(w for kw in resume_keywords for w in kw.split())
        jd_words = set(w for kw in jd_keywords for w in kw.split())

        missing_words = jd_words - resume_words
        found_words = jd_words.intersection(resume_words)

        missing_words = {w for w in missing_words if w not in STOP_WORDS and len(w) > 3}
        found_words = {w for w in found_words if w not in STOP_WORDS and len(w) > 3}

        format_issues = []
        if len(cleaned_resume.split()) < 100:
            format_issues.append("Resume is too short. It should have more detail.")
        if not re.search(r'\b(education|university|college|degree)\b', cleaned_resume, re.IGNORECASE):
            format_issues.append("Missing clear Education section.")
        if not re.search(r'\b(experience|work|employment|history)\b', cleaned_resume, re.IGNORECASE):
            format_issues.append("Missing clear Experience section.")

        keyword_optimization = build_keyword_optimization(cleaned_resume, cleaned_jd)
        skills_gap = analyze_skills_gap(cleaned_resume, cleaned_jd)

        return {
            "ats_match_percentage": score,
            "found_keywords_count": len(found_words),
            "missing_keywords_count": len(missing_words),
            "important_missing_keywords": list(missing_words)[:20],
            "format_issues": format_issues,
            "keyword_optimization": keyword_optimization,
            "skills_gap_analysis": skills_gap,
        }


if __name__ == "__main__":
    sample_resume = "Software Engineer with 5 years of Python, Django, and React experience. B.S. in Computer Science."
    sample_jd = "Looking for a Senior Software Engineer with strong Python and React skills. Must have experience with AWS and CI/CD pipelines. Education: Bachelor's degree."

    analyzer = ATSAnalyzer()
    report = analyzer.analyze(sample_resume, sample_jd)
    print(json.dumps(report, indent=2))
