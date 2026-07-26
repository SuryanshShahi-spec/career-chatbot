import os
import operator
from pathlib import Path
from typing import List, TypedDict, Annotated

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, END

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CSV_PATH = str(Path(__file__).parent.parent / "data" / "jobs.csv")
CHROMA_DIR = str(Path(__file__).parent.parent / "chroma_db")


# ---------------------------------------------------------------------------
# Graph State
# ---------------------------------------------------------------------------
class GraphState(TypedDict):
    question: str
    generation: str
    documents: List[Document]
    messages: Annotated[list, operator.add]
    is_relevant: str


# ---------------------------------------------------------------------------
# Grader Schema
# ---------------------------------------------------------------------------
class GradeDocuments(BaseModel):
    """Binary score for document relevance."""
    score: str = Field(description="Relevance of the job listing: 'yes' or 'no'")


# ---------------------------------------------------------------------------
# Corrective RAG Agent
# ---------------------------------------------------------------------------
class JobSearchAgent:
    """
    A Corrective RAG job-search chatbot that:
      1. Reformulates follow-up questions using conversation history.
      2. Retrieves job listings from a local ChromaDB vector store.
      3. Grades their relevance.
      4. Falls back to a Tavily web search when local results are not relevant.
      5. Generates a final answer with ChatGroq (LLaMA 3.1 70B).
    """

    def __init__(self, csv_path: str = CSV_PATH, persist_directory: str = CHROMA_DIR):
        self.csv_path = csv_path
        self.persist_directory = persist_directory

        # --- Models & Tools ---
        self.llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        self.embedding_model = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
        self.tavily_tool = TavilySearch(max_results=5)

        # --- Vector Store ---
        self.vectorstore = self._setup_vectorstore()
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})

        # --- LangGraph Workflow ---
        self.graph = self._build_graph()

    # ------------------------------------------------------------------
    # Vector Store
    # ------------------------------------------------------------------
    def _setup_vectorstore(self) -> Chroma:
        if os.path.exists(self.persist_directory) and os.listdir(self.persist_directory):
            return Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embedding_model,
            )

        df = pd.read_csv(self.csv_path)
        docs = [
            Document(
                page_content=(
                    f"Job Title: {row['Job Title']}\n"
                    f"Company: {row['Company']}\n"
                    f"Location: {row['Location']}\n"
                    f"Salary: {row.get('Salary', 'Not specified')}\n"
                    f"Job Description: {row['Job Description']}"
                ),
                metadata={
                    "title": str(row["Job Title"]),
                    "company": str(row["Company"]),
                    "location": str(row["Location"]),
                    "salary": str(row.get("Salary", "Not specified")),
                    "applying_link": str(row.get("Applying Link", "")),
                },
            )
            for _, row in df.iterrows()
        ]
        vectorstore = Chroma.from_documents(
            documents=docs,
            embedding=self.embedding_model,
            persist_directory=self.persist_directory,
        )
        return vectorstore

    # ------------------------------------------------------------------
    # Graph Nodes
    # ------------------------------------------------------------------
    def _reformulate_query(self, state: GraphState) -> dict:
        """Rewrite a follow-up question into a standalone query."""
        question = state["question"]
        messages = state.get("messages", [])

        if len(messages) <= 1:
            return {"question": question}

        history_str = "\n".join(
            [f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
             for m in messages[:-1]]
        )
        prompt = ChatPromptTemplate.from_template(
            "Given the conversation history below, reformulate the follow-up question "
            "into a clear, standalone job-search query.\n\n"
            "Conversation History:\n{history}\n\n"
            "Follow-up Question: {question}\n\n"
            "Standalone Query:"
        )
        chain = prompt | self.llm | StrOutputParser()
        reformulated = chain.invoke({"history": history_str, "question": question})
        return {"question": reformulated.strip()}

    def _retrieve_documents(self, state: GraphState) -> dict:
        """Retrieve top-k job listings from the vector store."""
        question = state["question"]
        documents = self.retriever.invoke(question)
        return {"documents": documents, "question": question}

    def _grade_documents(self, state: GraphState) -> dict:
        """Grade each retrieved document for relevance to the question."""
        question = state["question"]
        documents = state["documents"]

        grader_llm = self.llm.with_structured_output(GradeDocuments)
        prompt = ChatPromptTemplate.from_template(
            "You are a grader assessing whether a retrieved job listing is relevant "
            "to the user's query.\n\n"
            "Job Listing:\n{document}\n\n"
            "User Query: {question}\n\n"
            "Is this listing relevant? Answer strictly 'yes' or 'no'."
        )
        grader_chain = prompt | grader_llm

        is_relevant = "no"
        for doc in documents:
            result = grader_chain.invoke({"question": question, "document": doc.page_content})
            if result.score.strip().lower() == "yes":
                is_relevant = "yes"
                break

        return {"is_relevant": is_relevant}

    def _web_search(self, state: GraphState) -> dict:
        """Fall back to Tavily web search when local docs are not relevant."""
        question = state["question"]
        raw = self.tavily_tool.invoke({"query": question})

        docs: List[Document] = []
        results = (
            raw.get("results", []) if isinstance(raw, dict)
            else (raw if isinstance(raw, list) else [])
        )
        for r in results:
            if isinstance(r, dict):
                content = (
                    f"Title: {r.get('title', '')}\n"
                    f"URL: {r.get('url', '')}\n"
                    f"Summary: {r.get('content', '')}"
                )
                docs.append(Document(page_content=content, metadata={"url": r.get("url", "")}))

        if not docs:
            docs.append(Document(page_content=str(raw)))

        return {"documents": docs}

    def _generate_answer(self, state: GraphState) -> dict:
        """Generate a final answer using the retrieved context."""
        question = state["question"]
        documents = state["documents"]
        messages = state.get("messages", [])

        context_str = "\n\n---\n\n".join([d.page_content for d in documents])
        history_str = (
            "\n".join(
                [f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
                 for m in messages[:-1]]
            )
            if len(messages) > 1 else "None"
        )

        prompt = ChatPromptTemplate.from_template(
            "You are an expert job search assistant helping users find suitable job listings.\n"
            "Use the retrieved context below to answer the user's question.\n"
            "If the context includes job listings, present them clearly with:\n"
            "  - Job Title, Company, Location, Salary (if available), and Apply link.\n"
            "If no relevant listings are found, say so politely and offer suggestions.\n\n"
            "Conversation History:\n{history}\n\n"
            "Retrieved Context:\n{context}\n\n"
            "User Question: {question}\n\n"
            "Answer:"
        )
        chain = prompt | self.llm | StrOutputParser()
        generation = chain.invoke({
            "history": history_str,
            "context": context_str,
            "question": question,
        })
        return {"generation": generation, "documents": documents}

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------
    def _decide_action(self, state: GraphState) -> str:
        return "generate" if state["is_relevant"] == "yes" else "web_search"

    # ------------------------------------------------------------------
    # Graph Assembly
    # ------------------------------------------------------------------
    def _build_graph(self):
        workflow = StateGraph(GraphState)

        workflow.add_node("reformulate", self._reformulate_query)
        workflow.add_node("retrieve", self._retrieve_documents)
        workflow.add_node("grade_documents", self._grade_documents)
        workflow.add_node("web_search", self._web_search)
        workflow.add_node("generate", self._generate_answer)

        workflow.set_entry_point("reformulate")
        workflow.add_edge("reformulate", "retrieve")
        workflow.add_edge("retrieve", "grade_documents")
        workflow.add_conditional_edges(
            "grade_documents",
            self._decide_action,
            {"generate": "generate", "web_search": "web_search"},
        )
        workflow.add_edge("web_search", "generate")
        workflow.add_edge("generate", END)

        return workflow.compile()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def chat(self, question: str, history: List[BaseMessage]) -> tuple[str, str]:
        """
        Run the full RAG pipeline.
        Returns (answer_text, source_label) where source_label is 'local' or 'web'.
        """
        new_msg = HumanMessage(content=question)
        state = {
            "question": question,
            "generation": "",
            "documents": [],
            "messages": history + [new_msg],
            "is_relevant": "",
        }
        result = self.graph.invoke(state)
        docs = result.get("documents", [])
        source = "web" if any("URL:" in d.page_content for d in docs) else "local"
        return result["generation"], source


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="💼 Job Search Assistant",
        page_icon="💼",
        layout="wide",
    )

    # --- Custom CSS ---
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        min-height: 100vh;
    }

    .main-header {
        text-align: center;
        padding: 2rem 0 1rem;
    }
    .main-header h1 {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.4rem;
    }
    .main-header p { color: #94a3b8; font-size: 1.05rem; }

    .chat-message-user {
        background: linear-gradient(135deg, #6d28d9, #4f46e5);
        border-radius: 18px 18px 4px 18px;
        padding: 14px 18px;
        margin: 8px 0;
        color: #fff;
        max-width: 80%;
        margin-left: auto;
        box-shadow: 0 4px 15px rgba(109,40,217,0.3);
        animation: slideInRight 0.3s ease;
    }
    .chat-message-ai {
        background: rgba(255,255,255,0.07);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 18px 18px 18px 4px;
        padding: 14px 18px;
        margin: 8px 0;
        color: #e2e8f0;
        max-width: 85%;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        animation: slideInLeft 0.3s ease;
    }
    .chat-label {
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 6px;
        opacity: 0.7;
    }
    .source-badge {
        display: inline-block;
        background: rgba(52,211,153,0.15);
        border: 1px solid rgba(52,211,153,0.4);
        color: #34d399;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.72rem;
        font-weight: 600;
        margin: 4px 4px 0 0;
    }
    @keyframes slideInRight {
        from { opacity: 0; transform: translateX(20px); }
        to   { opacity: 1; transform: translateX(0); }
    }
    @keyframes slideInLeft {
        from { opacity: 0; transform: translateX(-20px); }
        to   { opacity: 1; transform: translateX(0); }
    }
    .stTextInput > div > div > input {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
        padding: 12px 16px !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #7c3aed !important;
        box-shadow: 0 0 0 3px rgba(124,58,237,0.2) !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 28px !important;
        font-weight: 600 !important;
        font-family: 'Inter', sans-serif !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 15px rgba(124,58,237,0.35) !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(124,58,237,0.5) !important;
    }
    .sidebar-info {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 14px;
        padding: 16px;
        margin-top: 12px;
        color: #94a3b8;
        font-size: 0.88rem;
        line-height: 1.7;
    }
    .stat-chip {
        background: linear-gradient(135deg, #7c3aed22, #4f46e522);
        border: 1px solid #7c3aed55;
        border-radius: 10px;
        padding: 10px 14px;
        text-align: center;
        margin: 6px 0;
    }
    .stat-chip strong { display: block; font-size: 1.4rem; color: #a78bfa; font-weight: 700; }
    .stat-chip span { font-size: 0.78rem; color: #64748b; }
    div[data-testid="stExpander"] {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- Header ---
    st.markdown("""
    <div class="main-header">
        <h1>💼 Job Search Assistant</h1>
        <p>Powered by Groq LLaMA 3.1 &nbsp;·&nbsp; Google Embeddings &nbsp;·&nbsp; Corrective RAG</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Sidebar ---
    with st.sidebar:
        st.markdown("## ⚙️ Assistant Info")
        st.markdown("""
        <div class="stat-chip"><strong>120</strong><span>Jobs in local DB</span></div>
        <div class="stat-chip"><strong>LLaMA 3.1 70B</strong><span>via Groq</span></div>
        <div class="stat-chip"><strong>Gemini Embed</strong><span>Google AI Embeddings</span></div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 💡 Try asking:")
        st.markdown("""
        <div class="sidebar-info">
        • Show me software engineer jobs in Bangalore<br>
        • Find data analyst roles in Mumbai<br>
        • What companies are hiring ML engineers?<br>
        • Jobs with the best salary<br>
        • Remote AI / ML roles<br>
        • Entry-level jobs in Hyderabad
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_messages = []
            st.session_state.lc_history = []
            st.rerun()

    # --- Session State ---
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []    # list of dicts for display
    if "lc_history" not in st.session_state:
        st.session_state.lc_history = []       # list of LangChain BaseMessages
    if "agent" not in st.session_state:
        with st.spinner("🔄 Initialising job search agent…"):
            st.session_state.agent = JobSearchAgent()

    agent: JobSearchAgent = st.session_state.agent

    # --- Display existing messages ---
    if not st.session_state.chat_messages:
        st.markdown("""
        <div style="text-align:center; color:#475569; padding:3rem 0;">
            <div style="font-size:3.5rem">🔍</div>
            <p style="margin-top:0.5rem; font-size:1.1rem">Ask me anything about job openings!</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for msg in st.session_state.chat_messages:
            if msg["role"] == "user":
                st.markdown(f"""
                <div class="chat-message-user">
                    <div class="chat-label">You</div>
                    {msg["content"]}
                </div>
                """, unsafe_allow_html=True)
            else:
                content_html = msg["content"].replace("\n", "<br>")
                badge = (
                    '<span class="source-badge">🌐 Web Search</span>'
                    if msg.get("source") == "web"
                    else '<span class="source-badge">📂 Local DB</span>'
                )
                st.markdown(f"""
                <div class="chat-message-ai">
                    <div class="chat-label">🤖 Assistant &nbsp; {badge}</div>
                    {content_html}
                </div>
                """, unsafe_allow_html=True)

    # --- Input Row ---
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_input(
            label="query",
            placeholder="e.g. Show me data science jobs in Bangalore…",
            label_visibility="collapsed",
            key="chat_input",
        )
    with col2:
        send_clicked = st.button("Send ➤", use_container_width=True)

    # --- Handle Submit ---
    if send_clicked and user_input.strip():
        question = user_input.strip()
        st.session_state.chat_messages.append({"role": "user", "content": question})

        with st.spinner("🔍 Searching for jobs…"):
            try:
                answer, source = agent.chat(question, st.session_state.lc_history)
            except Exception as exc:
                answer = f"❌ An error occurred: {exc}"
                source = ""

        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": answer,
            "source": source,
        })
        st.session_state.lc_history.append(HumanMessage(content=question))
        st.session_state.lc_history.append(AIMessage(content=answer))
        st.rerun()


if __name__ == "__main__":
    main()
