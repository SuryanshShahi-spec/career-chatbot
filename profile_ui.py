import streamlit as st
import sys
from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "Data") not in sys.path:
    sys.path.insert(0, str(ROOT / "Data"))

from Data.postgre import get_extended_profile, upsert_extended_profile, login_user

def render_profile_ui():
    st.set_page_config(page_title="User Profile", page_icon="👤", layout="wide")
    st.title("User Profile Dashboard")

    if "token" not in st.session_state:
        st.session_state.token = None

    if st.session_state.token is None:
        st.subheader("Login to view/edit your profile")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            res = login_user(email, password)
            if res.get("success"):
                st.session_state.token = res.get("token")
                st.rerun()
            else:
                st.error(res.get("message"))
        return

    def logout():
        st.session_state.token = None
    st.sidebar.button("Logout", on_click=logout)

    # Fetch profile
    res = get_extended_profile(st.session_state.token)
    if not res.get("success"):
        st.error(res.get("message"))
        return

    profile = res.get("profile", {})
    
    st.write("Manage your extended profile information here.")

    # Form
    with st.form("profile_form"):
        st.subheader("Basic Information")
        col1, col2 = st.columns(2)
        with col1:
            location = st.text_input("Location", value=profile.get("location", ""))
            job_role = st.text_input("Current Role", value=profile.get("job_role", ""))
        with col2:
            github = st.text_input("GitHub URL", value=profile.get("github", ""))
            linkedin = st.text_input("LinkedIn URL", value=profile.get("linkedin", ""))
        headline = st.text_input("Headline", value=profile.get("headline", ""))

        st.subheader("Details & Preferences")
        skills = st.text_area("Skills", value=profile.get("skills", ""))
        career_goals = st.text_area("Career Goals", value=profile.get("career_goals", ""))
        job_preferences = st.text_area("Job Preferences", value=profile.get("job_preferences", ""))

        st.subheader("History & Experience")
        education = st.text_area("Education", value=profile.get("education", ""))
        projects = st.text_area("Projects", value=profile.get("projects", ""))
        experience = st.text_area("Experience", value=profile.get("experience", ""))
        certifications = st.text_area("Certifications", value=profile.get("certifications", ""))

        submitted = st.form_submit_button("Save Profile")
        if submitted:
            new_data = {
                "location": location,
                "job_role": job_role,
                "headline": headline,
                "github": github,
                "linkedin": linkedin,
                "skills": skills,
                "career_goals": career_goals,
                "job_preferences": job_preferences,
                "education": education,
                "projects": projects,
                "experience": experience,
                "certifications": certifications
            }
            update_res = upsert_extended_profile(st.session_state.token, new_data)
            if update_res.get("success"):
                st.success("Profile updated successfully!")
            else:
                st.error(update_res.get("message"))

if __name__ == "__main__":
    render_profile_ui()
