import json
import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()
# 1. Initialize the GenAI Client
client = genai.Client()

# 2. Define the exact JSON structures using Pydantic
class ProfileStructure(BaseModel):
    education: List[str] = Field(description="List of educational qualifications")
    technical_skills: List[str] = Field(description="List of technical skills")
    soft_skills: List[str] = Field(description="List of soft skills")
    projects: List[str] = Field(description="List of projects mentioned")
    experience: List[str] = Field(description="List of professional work experience")
    certifications: List[str] = Field(description="List of certifications")
    strengths: List[str] = Field(description="Key strengths identified")
    weaknesses: List[str] = Field(description="Key areas of improvement or weaknesses")
    current_career_level: Optional[str] = Field(description="Current professional level")

class GoalStructure(BaseModel):
    target_role: Optional[str] = Field(default=None)
    target_industry: Optional[str] = Field(default=None)
    timeline: Optional[str] = Field(default=None)
    preferred_location: Optional[str] = Field(default=None)
    salary_expectation: Optional[str] = Field(default=None)
    desired_experience_level: Optional[str] = Field(default=None)
    main_career_objective: Optional[str] = Field(default=None)
    important_constraints: Optional[str] = Field(default=None)

# 3. Text prompts for analysis
PROFILE_ANALYZER_PROMPT = "You are a career profile analyzer. Analyze the user's career profile and return structured information. Do not invent information that is not present in the profile."
GOAL_ANALYZER_PROMPT = "You are a career goal analyzer. Analyze the user's career goal and extract details. Do not invent information. If something is not provided, return null."

GAP_ANALYZER_PROMPT = """You are a senior career coach. Review the following Profile Data and Goal Data. 
Provide a comprehensive, professional analysis that includes:
1. A comparison between the current skills/experience and the target goals.
2. An identification of key "gaps" (missing technical skills, education, or experience).
3. Actionable, step-by-step recommendations on how the user can reach their target role within their desired timeline.

Format the final response nicely with clear headings."""

def analyze_career_path(raw_profile_text: str, raw_goal_text: str):
    print("--- Step 1: Analyzing Career Profile ---")
    # Using response_schema forces the model to follow our Pydantic structure perfectly
    profile_response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=f"{PROFILE_ANALYZER_PROMPT}\n\nUser Profile:\n{raw_profile_text}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ProfileStructure
        )
    )
    # The output is guaranteed to be clean JSON matching our schema
    profile_json = json.loads(profile_response.text)
    print(json.dumps(profile_json, indent=2))
    
    print("\n--- Step 2: Analyzing Career Goals ---")
    goal_response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=f"{GOAL_ANALYZER_PROMPT}\n\nUser Goals:\n{raw_goal_text}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GoalStructure
        )
    )
    goal_json = json.loads(goal_response.text)
    print(json.dumps(goal_json, indent=2))
    
    print("\n--- Step 3: Generating Gap Analysis & Recommendations ---")
    analysis_input = f"Profile Data:\n{json.dumps(profile_json)}\n\nGoal Data:\n{json.dumps(goal_json)}"
    
    analysis_response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=f"{GAP_ANALYZER_PROMPT}\n\nData:\n{analysis_input}"
    )
    
    print(analysis_response.text)

# --- Sample Usage ---
if __name__ == "__main__":
    sample_profile = """
    I am pursuing a Bachelor's degree in Artificial Intelligence & Machine Learning in 3rd year. 
    I have experience working in Hackathon.
    My technical skills include Python and Git. 
    I'm highly collaborative and an eager learner, but I struggle with public speaking and sometimes take too long to debug complex issues.
    I built a library management system and a face recognition system using Python. 
    Various Hackathons certifications .
    """
    
    sample_goal = """
    I want to transition into a Python Developer role within the AI industry over the next 18 months.
    I would prefer to work remotely from the India or locally in Jalgaon.
    I am targeting a salary of 300000 per year. 
    I want to move up to a mid-level engineering position.
    """
    
    analyze_career_path(sample_profile, sample_goal)
