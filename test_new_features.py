import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "Data") not in sys.path:
    sys.path.insert(0, str(ROOT / "Data"))

from Data.sqlite_db import save_job_application, get_job_applications, save_job_preferences, get_job_preferences

def run_tests():
    print("Testing SQLite tools...")
    
    # Preferences
    print("\n--- Saving preferences ---")
    res = save_job_preferences("test_user_1", ["Mumbai", "Pune"], ["Data Scientist", "Software Engineer"])
    print(res)
    
    print("\n--- Getting preferences ---")
    res = get_job_preferences("test_user_1")
    print(res)
    
    # Applications
    print("\n--- Saving applications ---")
    res1 = save_job_application("test_user_1", "Software Engineer", "Google", "Bangalore", "Applied", "Referral")
    print(res1)
    res2 = save_job_application("test_user_1", "Data Scientist", "Microsoft", "Hyderabad", "Interviewing", "Round 1")
    print(res2)
    
    print("\n--- Getting applications ---")
    apps = get_job_applications("test_user_1")
    print(apps)

if __name__ == "__main__":
    run_tests()
