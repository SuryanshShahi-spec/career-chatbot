#!/usr/bin/env python3
"""Test script for interview prep tool"""

from Assets.interview_prep import InterviewPrepTool

# Initialize tool
tool = InterviewPrepTool()
print("✓ Interview prep tool imported successfully\n")

# Test 1: Get interview questions
print("=" * 50)
print("TEST 1: Interview Questions")
print("=" * 50)
questions = tool.get_interview_questions('behavioral')
print(f"✓ Loaded {len(questions['behavioral'])} behavioral questions")
print(f"  Sample: {questions['behavioral'][0]}\n")

# Test 2: STAR Framework
print("=" * 50)
print("TEST 2: STAR Framework")
print("=" * 50)
star = tool.get_star_framework_guide('Tell me about a time you overcame a challenge')
print(f"✓ STAR framework loaded: {star['method']}")
print("  Components:")
for k, v in star['components'].items():
    print(f"    • {k}: {v}")
print()

# Test 3: Mock Interview
print("=" * 50)
print("TEST 3: Mock Interview Generation")
print("=" * 50)
mock = tool.generate_mock_interview("Senior Software Engineer", "Google", "senior")
print(f"✓ Generated mock interview for {mock['position']} at {mock['company']}")
print(f"  Experience Level: {mock['experience_level']}")
print("  Interview Sections:")
for category, qs in mock["sections"].items():
    print(f"    • {category}: {len(qs)} questions")
print()

# Test 4: Red Flags
print("=" * 50)
print("TEST 4: Interview Red Flags & Green Flags")
print("=" * 50)
flags = tool.get_red_flags_and_green_flags()
print(f"✓ Loaded {len(flags['green_flags'])} green flags and {len(flags['red_flags'])} red flags")
print("  Sample Green Flags:")
for flag in flags['green_flags'][:2]:
    print(f"    ✓ {flag}")
print("  Sample Red Flags:")
for flag in flags['red_flags'][:2]:
    print(f"    ✗ {flag}")
print()

# Test 5: Job Description Analysis
print("=" * 50)
print("TEST 5: Job Description Analysis")
print("=" * 50)
jd = """
We're hiring a Senior Python Engineer. Required skills: Python, Django, PostgreSQL, Redis.
Leadership experience and team mentoring is important. You should be comfortable working in an agile environment.
Strong communication skills and ability to collaborate with cross-functional teams.
"""
analysis = tool.analyze_job_description_for_prep(jd)
print(f"✓ Analyzed job description")
print(f"  Key Areas: {analysis['key_areas_to_prepare']}")
print(f"  Skills to Highlight: {analysis['skills_to_highlight']}")
print(f"  Suggested Questions: {len(analysis['suggested_questions'])} questions")
print()

print("=" * 50)
print("✓ ALL TESTS PASSED!")
print("=" * 50)
