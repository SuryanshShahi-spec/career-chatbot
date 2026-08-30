import json
import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv

# For extracting text from documents
import pypdf
import docx2txt

load_dotenv()

# 1. Initialize the GenAI Client
client = genai.Client()

# 2. Define our bulletproof Pydantic schemas
class ProfileStructure(BaseModel):
    education:List[str] =Field(description="Degrees, schools, and graduation years found.")
    technical_skills:List[str] =Field(description="Programming languages, frameworks, software tools.")
    soft_skills:List[str] =Field(description="Interpersonal traits like leadership, communication.")
    projects:List[str] =Field(description="Academic, personal, or professional projects listed.")
    experience:List[str] =Field(description="Previous roles, companies, and responsibilities.")
    certifications:List[str] =Field(description="Professional certificates or licenses.")
    strengths:List[str] =Field(description="Evident professional strengths.")
    weaknesses:List[str] =Field(description="Evident gaps or areas for development.")
    current_career_level: Optional[str] = Field(description="Entry-level, Mid-level, Senior, Lead, etc.")

class GoalStructure(BaseModel):
    target_role: Optional[str] = Field(default=None)
    target_industry: Optional[str] = Field(default=None)
    timeline: Optional[str] = Field(default=None)
    preferred_location: Optional[str] = Field(default=None)
    salary_expectation: Optional[str] = Field(default=None)
    desired_experience_level: Optional[str] = Field(default=None)
    main_career_objective: Optional[str] = Field(default=None)
    important_constraints: Optional[str] = Field(default=None)
    
# 3. Prompts
PROFILE_ANALYZER_PROMPT = " You are a career profile analyzer. Analyze the user's resume text and the extracted NLP entities to generate structured information. DO NOT generate information that does not exist in the resume text or entities."
GOAL_ANALYZER_PROMPT = "You are a career goal analyzer. Analyze the user's career goal and provide details. DO NOT generate information. If not provided, career goal and provide details. DO NOT generate information. If not provided, return null."

GAP_ANALYZER_PROMPT = """You are an experienced career coach. Analyze the 
Extracted Resume Data and Target Goals. 
Write a detailed and professional analysis, which should include: 
1. The comparison of the current skills and experience with the target goals. 
2. Identification of major gaps that will prevent the user from reaching her target.
3. Recommendation on how to get there.

Please present your recommendation in an orderly fashion with headings. """

# 4. Document Helper Function to extract raw text
def extract_text_from_file(file_path:str) -> str:
    """ Extracts raw text from .txt, .pdf, or .docx files."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Could not find the file at: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".txt":
        with open (file_path,"r",encoding="utf-8")as f:
            return f.read()

    elif ext == ".pdf":
        text = ""
        with open (file_path,"rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text() or ""
                text += page_text
        return text
    
    elif ext == ".docx":
        return docx2txt.process(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Please use .txt, .pdf, or .docx")

# 5. Core Execution Pipeline
def analyze_resume_versus_goals(resume_file_path: str, raw_goal_text: str):
    print(f"Reading file: {resume_file_path}……")
    try:
        resume_text = extract_text_from_file(resume_file_path)
        print(f"Successfully extracted {len(resume_text)} characters from resume")
    except Exception as e:
        print(f"Error reading file: {str(e)}")
        return

    if not resume_text.strip():
        print("Error: The extracted resume text is empty.")
        return

    try:
        from Assets.resume_parsing import clean_text, extract_entities
        cleaned_text = clean_text(resume_text)
        nlp_entities = extract_entities(cleaned_text)
        print("Successfully extracted NLP entities from resume.")
    except Exception as e:
        print(f"NLP entity extraction failed: {e}")
        cleaned_text = resume_text
        nlp_entities = {}

    print("--- Step 1: Parsing Resume into Structured JSON ---")
    try:
        profile_response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=f"{PROFILE_ANALYZER_PROMPT}\n\nNLP Entities: {json.dumps(nlp_entities)}\n\nResume Document Text: \n{cleaned_text}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ProfileStructure,
            )
        )
        profile_json = json.loads(profile_response.text)
        print(json.dumps(profile_json, indent=2))
    except Exception as e:
        print(f"Error in profile analysis: {e}")
        return

    print("\n--- Step 2: Analyzing Career Goals ---")
    try:
        goals_response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=f"{GOAL_ANALYZER_PROMPT}\n\nUser's Goal Description: \n{raw_goal_text}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GoalStructure,
            )
        )
        goal_json = json.loads(goals_response.text)
        print(json.dumps(goal_json, indent=2))
    except Exception as e:
        print(f"Error in goal analysis: {e}")
        return

    print("\n--- Step 3: Generating Gap Analysis and Recommendation ---")
    analysis_input = f"Resume Data:\n{json.dumps(profile_json)}\n\nGoal Data:\n{json.dumps(goal_json)}"
    
    try:
        analysis_response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=f"{GAP_ANALYZER_PROMPT}\n\nData: \n{analysis_input}"
        )
        print("\n=== FINAL COACHING ANALYSIS ===")
        print(analysis_response.text)
    except Exception as e:
        print(f"Error in gap analysis: {e}")

# --- Sample Usage ---
if __name__ == "__main__":
    # Use the absolute path with raw string (r"")
    sample_resume = r"C:\Users\admin\Downloads\Job_search_assistant-20260810T173757Z-1-001\Job_search_assistant\Data\Suryansh_Resume.pdf"
    
    sample_goal = """
    I plan to move into a career as a Python Developer in the AI 
domain in the coming 18 months
    I would like to work from home in India or in Jalgaon 
locally.
    My target annual income is Rs. 276000.
    I plan to become a mid-level engineer."""
    
    analyze_resume_versus_goals(sample_resume, sample_goal)