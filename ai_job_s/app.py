import streamlit as st

class JobSearchUI:
    def __init__(self):
        """Initialize the Job Search Agent UI"""
        self.title = "💼 Job Search Agent"
        self.sidebar_title = "🔍 Filters"

    def run(self):
        # Page title
        st.title(self.title)
        st.write("Welcome to the Job Search Agent! Enter your query below to explore job listings.")

        # Sidebar filters
        st.sidebar.header(self.sidebar_title)
        location = st.sidebar.text_input("Location")
        experience = st.sidebar.text_input("Experience (e.g., 2 years)")
        salary = st.sidebar.text_input("Salary (e.g., 5 LPA)")

        # Main input
        query = st.text_input("Ask about jobs (e.g., 'Show jobs in Pune')")

        # Action button
        if st.button("Search Jobs"):
            # Placeholder output (UI only, no backend)
            st.subheader("📋 Search Results")
            st.write(f"Showing results for query: **{query}**")
            st.write(f"- Location filter: {location or 'None'}")
            st.write(f"- Experience filter: {experience or 'None'}")
            st.write(f"- Salary filter: {salary or 'None'}")

            # Example table
            sample_data = {
                "Job Title": ["Software Engineer", "Data Analyst"],
                "Company": ["TechCorp", "DataWorks"],
                "Location": ["Pune", "Mumbai"],
                "Salary": ["6 LPA", "5 LPA"]
            }
            st.table(sample_data)


# Run the app
if __name__ == "__main__":
    ui = JobSearchUI()
    ui.run()
