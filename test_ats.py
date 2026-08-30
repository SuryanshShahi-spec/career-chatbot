import json
import os
from Assets.ats_analyzer import ATSAnalyzer
from Assets.resume_parsing import text_extractor

def test():
    resume_path = "Data/Suryansh_Resume.pdf"
    if not os.path.exists(resume_path):
        print("Resume not found.")
        return
        
    jd = "Looking for a Python developer with experience in Streamlit, LLMs, and Generative AI. Must know machine learning."
    
    print("Reading resume...")
    try:
        resume_text = text_extractor(resume_path)
    except Exception as e:
        print("Error reading resume:", e)
        return
        
    print("Analyzing...")
    analyzer = ATSAnalyzer()
    report = analyzer.analyze(resume_text, jd)
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    test()
