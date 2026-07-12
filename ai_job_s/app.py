import os
import sys
import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

# Force UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(dotenv_path=os.path.join(project_root, ".env"))

# Import the chatbot class
from chatbot import Correcti

# Set page config with modern title and icon
st.set_page_config(
    page_title="AI Job Search Assistant",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        color: #ffffff;
    }
    .stChatInput {
        border-radius: 12px;
    }
    .job-card {
        background-color: #1e222b;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
        border-left: 5px solid #00f2fe;
    }
    .job-title {
        color: #00f2fe;
        font-size: 1.2rem;
        font-weight: bold;
    }
    .job-meta {
        color: #a3a8b4;
        font-size: 0.9rem;
    }
    .job-link {
        color: #4facfe;
        text-decoration: none;
    }
    .job-link:hover {
        text-decoration: underline;
    }
    </style>
""", unsafe_allow_html=True)

# App Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/clouds/200/search-in-list.png", width=120)
    st.title("Settings")
    st.markdown("---")
    
    # Allow tweaking some options
    csv_path = st.text_input("CSV Jobs Dataset", value=os.path.join(project_root, "jobs.csv"))
    db_path = st.text_input("Chroma DB Directory", value=os.path.join(project_root, "chroma_db"))
    
    st.markdown("---")
    st.markdown("### Active Configuration")
    st.info("Using Adzuna Indian Jobs dataset & Google Generative AI Embeddings.")

# Initialize the chatbot application
@st.cache_resource
def load_chatbot(csv_file, db_dir):
    try:
        return Correcti(csv_path=csv_file, persist_directory=db_dir)
    except Exception as e:
        st.error(f"Failed to initialize chatbot application: {e}")
        return None

chatbot = load_chatbot(csv_path, db_path)

# Main Dashboard UI
st.title("💼 AI Career & Job Finder Assistant")
st.write("Ask questions like *'Find me a high paying React Developer job in Pune'* or *'Are there any HR opportunities?'*")
st.markdown("---")

if chatbot is None:
    st.warning("⚠️ Chatbot application failed to load. Please verify your environment settings and API keys.")
else:
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    # Display chat history
    for msg in st.session_state.messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        with st.chat_message(role):
            st.write(msg.content)
            
    # Chat input
    if prompt := st.chat_input("Enter your career or job search query..."):
        # Display user query
        with st.chat_message("user"):
            st.write(prompt)
            
        # Add to message state
        user_msg = HumanMessage(content=prompt)
        st.session_state.messages.append(user_msg)
        
        # Display assistant thinking & response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing job opportunities & searching context..."):
                try:
                    # Invoke Corrective RAG LangGraph application
                    state_input = {
                        "question": prompt,
                        "messages": st.session_state.messages,
                        "documents": [],
                        "generation": ""
                    }
                    
                    response_state = chatbot.app.invoke(state_input)
                    ans = response_state.get("generation", "Sorry, I couldn't find a matching response.")
                    
                    st.write(ans)
                    
                    # Store assistant message
                    st.session_state.messages.append(AIMessage(content=ans))
                    
                    # Optionally display sources/links
                    retrieved_docs = response_state.get("documents", [])
                    if retrieved_docs:
                        with st.expander("🔍 Scraped Job Sources"):
                            for idx, doc in enumerate(retrieved_docs):
                                metadata = doc.metadata
                                title = metadata.get("title", "Job Listing")
                                company = metadata.get("company", "N/A")
                                location = metadata.get("location", "N/A")
                                salary = metadata.get("salary", "N/A")
                                url = metadata.get("url", "#")
                                
                                st.markdown(f"""
                                <div class="job-card">
                                    <div class="job-title">{idx+1}. {title}</div>
                                    <div class="job-meta">
                                        🏢 <b>Company:</b> {company} | 📍 <b>Location:</b> {location} | 💰 <b>Salary:</b> {salary}
                                    </div>
                                    <a class="job-link" href="{url}" target="_blank">🔗 Apply Here</a>
                                </div>
                                """, unsafe_allow_html=True)
                                
                except Exception as e:
                    st.error(f"An error occurred while answering your query: {e}")
                    import traceback
                    st.code(traceback.format_exc())
