"""
Interview Preparation Tool - Provides interview questions, STAR method guidance,
and mock interview scenarios for job candidates.
"""

import json
import os
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class InterviewPrepTool:
    """Comprehensive interview preparation assistant."""

    # Common interview question categories
    QUESTION_CATEGORIES = {
        "behavioral": [
            "Tell me about a time you overcame a challenge.",
            "Describe a situation where you had to work with a difficult team member.",
            "Share an example of how you demonstrated leadership.",
            "Tell me about a time you failed and what you learned.",
            "Describe a time you went above and beyond your job responsibilities.",
            "Give an example of when you had to adapt to a significant change.",
            "Tell me about a time you improved a process at work.",
            "Describe a situation where you had to meet a tight deadline.",
            "Tell me about a time you had to handle multiple priorities.",
            "Share an example of how you handled constructive criticism.",
        ],
        "technical": [
            "Walk me through your most complex technical project.",
            "How do you stay current with new technologies?",
            "Explain your experience with version control and CI/CD pipelines.",
            "What's your experience with cloud platforms (AWS, Azure, GCP)?",
            "How do you approach debugging and troubleshooting?",
            "Describe your experience with databases and data management.",
            "Tell me about your API design and integration experience.",
            "How do you write scalable and maintainable code?",
            "What testing strategies do you use?",
            "Explain your experience with containerization and Docker.",
        ],
        "situational": [
            "How would you approach this hypothetical scenario?",
            "What would you do if you disagreed with your manager's decision?",
            "How would you handle a project that's falling behind schedule?",
            "What's your approach to learning a new technology quickly?",
            "How would you prioritize if given multiple urgent tasks?",
            "What would you do if you found a security vulnerability in production?",
            "How would you handle a situation where you don't know the answer?",
            "What's your strategy for collaborating with remote teams?",
            "How would you approach mentoring a junior developer?",
            "What would you do if a client complained about your work?",
        ],
        "company_culture": [
            "Why are you interested in our company?",
            "What do you know about our products/services?",
            "How do you align with our company values?",
            "What attracts you to this specific role?",
            "Where do you see yourself in 5 years?",
            "What's your ideal work environment?",
            "How do you contribute to a positive team culture?",
            "What are your salary expectations?",
            "Why are you leaving your current role?",
            "What questions do you have about the company or role?",
        ],
    }

    # STAR method template
    STAR_TEMPLATE = {
        "Situation": "Set the context - what was the scenario? When did it happen?",
        "Task": "What was your responsibility? What needed to be done?",
        "Action": "What specific actions did you take? How did you approach it?",
        "Result": "What was the outcome? What did you learn? Use metrics if possible.",
    }

    def __init__(self):
        """Initialize the interview prep tool."""
        self.questions = self.QUESTION_CATEGORIES
        self.star_method = self.STAR_TEMPLATE

    def get_interview_questions(self, category: str = "all") -> Dict[str, Any]:
        """
        Retrieve interview questions by category.

        Args:
            category: Question category ('behavioral', 'technical', 'situational', 'company_culture', or 'all')

        Returns:
            Dictionary containing the requested questions
        """
        if category == "all":
            return self.questions
        elif category in self.questions:
            return {category: self.questions[category]}
        else:
            return {"error": f"Category '{category}' not found. Available: {list(self.questions.keys())}"}

    def generate_mock_interview(self, job_title: str, company_name: str, experience_level: str = "mid") -> Dict[str, Any]:
        """
        Generate a personalized mock interview based on job and company.

        Args:
            job_title: The position title (e.g., "Software Engineer", "Product Manager")
            company_name: The company name
            experience_level: Candidate's experience level ('entry', 'mid', 'senior')

        Returns:
            Dictionary containing personalized interview questions
        """
        interview = {
            "position": job_title,
            "company": company_name,
            "experience_level": experience_level,
            "sections": {},
        }

        # Determine question distribution based on experience level
        if experience_level == "entry":
            distribution = {"behavioral": 3, "technical": 2, "company_culture": 2}
        elif experience_level == "senior":
            distribution = {"behavioral": 2, "technical": 4, "situational": 2, "company_culture": 2}
        else:  # mid
            distribution = {"behavioral": 3, "technical": 3, "situational": 1, "company_culture": 2}

        for category, count in distribution.items():
            interview["sections"][category] = self.questions[category][:count]

        interview["tips"] = self._get_interview_tips(job_title, experience_level)
        return interview

    def _get_interview_tips(self, job_title: str, experience_level: str) -> List[str]:
        """Generate interview tips based on role and experience level."""
        tips = [
            "Research the company thoroughly before the interview.",
            "Prepare specific examples using the STAR method.",
            "Arrive 10-15 minutes early (or login early for virtual interviews).",
            "Bring copies of your resume and a notepad.",
            "Make eye contact and maintain good posture.",
            "Listen carefully to questions before answering.",
            "Use the 'STAR' method for behavioral questions.",
            "Quantify your achievements with metrics when possible.",
            "Ask thoughtful questions about the role and company.",
            "Send a thank you message within 24 hours.",
        ]

        if "engineer" in job_title.lower():
            tips.extend([
                "Be ready to discuss technical problems and your approach.",
                "Practice coding or system design questions if applicable.",
                "Explain your thought process out loud during technical discussions.",
            ])

        if "manager" in job_title.lower():
            tips.extend([
                "Prepare examples of how you've led and developed teams.",
                "Discuss your management philosophy and leadership style.",
            ])

        if experience_level == "entry":
            tips.extend([
                "Emphasize your learning ability and eagerness.",
                "Talk about relevant projects or internships.",
                "Be honest about what you don't know but show willingness to learn.",
            ])

        if experience_level == "senior":
            tips.extend([
                "Focus on impact and strategic thinking.",
                "Discuss how you've mentored others and grown teams.",
                "Be prepared to discuss compensation and negotiation.",
            ])

        return tips

    def get_star_framework_guide(self, question: str = "") -> Dict[str, Any]:
        """
        Provide the STAR method framework with guidance.

        Args:
            question: Specific question to practice with

        Returns:
            Dictionary with STAR framework and example
        """
        guide = {
            "method": "STAR (Situation, Task, Action, Result)",
            "description": "A structured framework for answering behavioral interview questions.",
            "components": self.STAR_TEMPLATE,
            "tips": [
                "Use the STAR method to structure your response clearly.",
                "Prepare 5-7 good stories from your work experience.",
                "Focus on YOUR actions, not the team's.",
                "Include quantifiable results whenever possible.",
                "Keep each story to 2-3 minutes.",
                "Practice out loud to improve delivery and timing.",
            ],
            "example_story": {
                "Situation": "Our team was struggling with slow API response times affecting user experience.",
                "Task": "As the lead backend engineer, I was responsible for identifying and fixing the performance bottleneck.",
                "Action": "I analyzed our database queries, identified N+1 query problems, implemented Redis caching, and optimized our ORM usage. I also set up monitoring to track improvements.",
                "Result": "Reduced API response time by 60% (from 2s to 800ms), improved user retention by 15%, and the solution became part of our standard optimization toolkit.",
            },
        }

        if question:
            guide["your_question"] = question
            guide["guidance"] = f"Think about a time from your experience that relates to: {question}. Use STAR to structure your answer."

        return guide

    def analyze_job_description_for_prep(self, job_description: str) -> Dict[str, Any]:
        """
        Analyze a job description to generate targeted interview prep.

        Args:
            job_description: The full job description text

        Returns:
            Dictionary with key skills, responsibilities, and suggested prep questions
        """
        prep_analysis = {
            "job_description_summary": "Extract key requirements and prepare for related questions.",
            "key_areas_to_prepare": [],
            "suggested_questions": [],
            "skills_to_highlight": [],
        }

        # Keywords to look for in job description
        technical_keywords = [
            "python", "javascript", "java", "go", "rust", "c++",
            "react", "angular", "vue", "sql", "nosql", "docker",
            "kubernetes", "aws", "azure", "gcp", "api", "microservices",
        ]

        soft_skill_keywords = [
            "leadership", "communication", "collaboration", "problem-solving",
            "adaptability", "critical thinking", "project management",
        ]

        jd_lower = job_description.lower()

        # Extract technical skills mentioned
        for keyword in technical_keywords:
            if keyword in jd_lower:
                prep_analysis["skills_to_highlight"].append(keyword)

        # Extract soft skills mentioned
        for keyword in soft_skill_keywords:
            if keyword in jd_lower:
                prep_analysis["key_areas_to_prepare"].append(keyword)

        # Suggest relevant questions
        if "leadership" in jd_lower:
            prep_analysis["suggested_questions"].extend([
                "Tell me about a time you led a team or took initiative.",
                "How do you handle conflicts within a team?",
            ])

        if "collaborate" in jd_lower:
            prep_analysis["suggested_questions"].extend([
                "Describe your experience working with cross-functional teams.",
                "Tell me about a successful collaboration.",
            ])

        if any(tech in jd_lower for tech in ["python", "javascript", "java"]):
            prep_analysis["suggested_questions"].extend([
                "Walk me through your most complex technical project.",
                "How do you approach learning new programming languages?",
            ])

        prep_analysis["preparation_checklist"] = [
            "✓ Research the company and its products",
            "✓ Prepare 5-7 STAR method stories",
            "✓ Practice technical questions if required",
            "✓ Prepare questions to ask the interviewer",
            "✓ Do a practice mock interview",
            "✓ Get a good night's sleep before interview",
        ]

        return prep_analysis

    def get_red_flags_and_green_flags(self) -> Dict[str, List[str]]:
        """
        Provide guidance on interview red flags and green flags.

        Returns:
            Dictionary with interviewer behaviors to watch for
        """
        return {
            "green_flags": [
                "Interviewers ask about your growth and learning opportunities",
                "They're eager to answer your questions about the company",
                "Clear communication about role expectations and success metrics",
                "Structured interview process with clear next steps",
                "Team members seem engaged and positive",
                "They ask about your career goals and long-term plans",
            ],
            "red_flags": [
                "Disorganized interview with unclear questions",
                "Interviewers seem unengaged or dismissive",
                "Vague or changing job descriptions",
                "No clear timeline communicated",
                "Questions that feel discriminatory or inappropriate",
                "High employee turnover mentioned casually",
                "Salary and compensation seem negotiable only downward",
            ],
            "after_interview": [
                "Send thank you emails within 24 hours",
                "Reference specific conversations from the interview",
                "Reiterate your interest in the position",
                "Ask about next steps and timeline",
                "Follow up if you don't hear back within the stated timeframe",
            ],
        }

    def generate_prep_summary(self, job_title: str, company_name: str, jd: str = "") -> str:
        """
        Generate a comprehensive interview prep summary.

        Args:
            job_title: Position title
            company_name: Company name
            jd: Optional job description for analysis

        Returns:
            Formatted summary string
        """
        summary = f"""
INTERVIEW PREPARATION SUMMARY
{'='*50}

Position: {job_title}
Company: {company_name}

PREPARATION CHECKLIST:
1. Research Phase
   - Company mission, values, and recent news
   - Product/service offerings
   - Company culture and team structure
   - Key competitors and market position

2. Self-Preparation Phase
   - Prepare 5-7 STAR method stories from your experience
   - Practice answers to common questions
   - Prepare thoughtful questions for the interviewer
   - Review your resume and be ready to discuss everything

3. Technical Preparation (if applicable)
   - Review relevant technical concepts
   - Practice coding/design problems
   - Be ready to explain your technical background

4. Day Before
   - Get all interview details (time, location, interviewer names)
   - Prepare outfit and materials
   - Get good sleep
   - Plan your commute/tech setup

5. Day Of
   - Arrive 10-15 minutes early
   - Take deep breaths and relax
   - Bring energy, enthusiasm, and positive attitude
   - Follow the STAR method for behavioral questions

KEY INTERVIEW TIPS:
- Listen carefully before answering
- Use specific examples with metrics
- Ask thoughtful questions
- Be honest if you don't know something
- Send thank you notes within 24 hours

Good luck! 🚀
"""
        return summary


def interview_prep_assistant(
    action: str,
    job_title: str = "",
    company_name: str = "",
    category: str = "all",
    job_description: str = "",
    experience_level: str = "mid",
) -> str:
    """
    Main interface for interview preparation tool.

    Args:
        action: Action to perform ('questions', 'mock_interview', 'star_guide', 'analyze_jd', 'red_flags', 'summary')
        job_title: Position title
        company_name: Company name
        category: Question category
        job_description: Job description text
        experience_level: Experience level ('entry', 'mid', 'senior')

    Returns:
        JSON string with results
    """
    tool = InterviewPrepTool()

    try:
        if action == "questions":
            result = tool.get_interview_questions(category)
        elif action == "mock_interview":
            result = tool.generate_mock_interview(job_title, company_name, experience_level)
        elif action == "star_guide":
            result = tool.get_star_framework_guide(job_title)
        elif action == "analyze_jd":
            result = tool.analyze_job_description_for_prep(job_description)
        elif action == "red_flags":
            result = tool.get_red_flags_and_green_flags()
        elif action == "summary":
            result = tool.generate_prep_summary(job_title, company_name, job_description)
        else:
            result = {"error": f"Unknown action: {action}"}

        return json.dumps(result, indent=2) if isinstance(result, dict) else result
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


if __name__ == "__main__":
    tool = InterviewPrepTool()

    print("=== SAMPLE INTERVIEW QUESTIONS ===\n")
    questions = tool.get_interview_questions("behavioral")
    print("Behavioral Questions:")
    for q in questions["behavioral"][:3]:
        print(f"  - {q}")

    print("\n=== STAR METHOD FRAMEWORK ===\n")
    star_guide = tool.get_star_framework_guide("Tell me about a time you overcame a challenge")
    print(f"Method: {star_guide['method']}")
    print("Framework:")
    for component, description in star_guide['components'].items():
        print(f"  {component}: {description}")

    print("\n=== MOCK INTERVIEW ===\n")
    mock = tool.generate_mock_interview("Senior Software Engineer", "TechCorp", "senior")
    print(f"Position: {mock['position']} at {mock['company']}")
    print("Interview Sections:")
    for category, questions_list in mock["sections"].items():
        print(f"  {category.upper()}: {len(questions_list)} questions")

    print("\n=== INTERVIEW RED FLAGS ===\n")
    flags = tool.get_red_flags_and_green_flags()
    print("Green Flags:")
    for flag in flags["green_flags"][:3]:
        print(f"  ✓ {flag}")
    print("\nRed Flags:")
    for flag in flags["red_flags"][:3]:
        print(f"  ✗ {flag}")

    print("\n=== PREP SUMMARY ===\n")
    summary = tool.generate_prep_summary("Software Engineer", "TechCorp")
    print(summary)
