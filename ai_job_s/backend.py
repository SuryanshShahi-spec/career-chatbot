
import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from typing import List, TypedDict, Annotated
import operator

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch


# --- Define Graph State ---
class GraphState(TypedDict):
    question: str
    generation: str
    documents: List[Document]
    messages: Annotated[list, operator.add]
    is_relevant: str


# --- Define Grader Model ---
class GradeDocuments(BaseModel):
    score: str = Field(description="Document relevance: 'yes' or 'no'")


class Correct:
    def __init__(self, csv_path: str, persist_directory: str = "./chroma_db"):
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
        self.csv_path = csv_path
        self.persist_directory = persist_directory

        # ✅ Use a valid Groq model
        self.llm = ChatGroq(model="llama-3.1-70b-versatile", temperature=0)
        self.embedding_model = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
        self.tavily_tool = TavilySearch(max_results=5)

        # Setup vector store
        self.vectorstore = self._setup_vectorstore()
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})

        # Build workflow
        self.app = self._build_graph()

    def _setup_vectorstore(self) -> Chroma:
        if os.path.exists(self.persist_directory):
            return Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embedding_model
            )
        else:
            df = pd.read_csv(self.csv_path)
            docs = [
                Document(
                    page_content=f"Job Title: {row['Job Title']}\nCompany: {row['Company']}\nLocation: {row['Location']}\nJob Description: {row['Job Description']}",
                    metadata={
                        "title": row["Job Title"],
                        "company": row["Company"],
                        "location": row["Location"],
                        "description": row["Job Description"]
                    }
                )
                for _, row in df.iterrows()
            ]
            vectorstore = Chroma.from_documents(
                documents=docs,
                embedding=self.embedding_model,
                persist_directory=self.persist_directory
            )
            return vectorstore

    def _reformulate_query(self, state: GraphState) -> dict:
        question = state["question"]
        messages = state["messages"]

        if not messages or len(messages) <= 1:
            return {"question": question}

        prompt = ChatPromptTemplate.from_template(
            "Reformulate the follow-up question into a standalone search query.\n\n"
            "History:\n{history}\n\n"
            "Follow-up Question: {question}\n\n"
            "Standalone Query:"
        )
        history_str = "\n".join([f"{type(msg).__name__}: {msg.content}" for msg in messages[:-1]])
        chain = prompt | self.llm | StrOutputParser()
        reformulated = chain.invoke({"history": history_str, "question": question})
        return {"question": reformulated}

    def _retrieve_documents(self, state: GraphState) -> dict:
        question = state["question"]
        documents = self.retriever.invoke(question)
        return {"documents": documents, "question": question}

    def _grade_documents(self, state: GraphState) -> dict:
        question = state["question"]
        documents = state["documents"]

        structured_llm_grader = self.llm.with_structured_output(GradeDocuments)
        prompt = ChatPromptTemplate.from_template(
            "You are a grader assessing relevance of a job listing.\n"
            "Document:\n{document}\n\n"
            "User Question: {question}\n\n"
            "Relevant? ('yes' or 'no')"
        )
        grader_chain = prompt | structured_llm_grader

        is_relevant = "no"
        for d in documents:
            score = grader_chain.invoke({"question": question, "document": d.page_content})
            if score.score.lower() == "yes":
                is_relevant = "yes"
                break
        return {"is_relevant": is_relevant}

    def _web_search(self, state: GraphState) -> dict:
        question = state["question"]
        web_results = self.tavily_tool.invoke({"query": question})

        docs = []
        if isinstance(web_results, dict) and 'results' in web_results:
            for r in web_results['results']:
                content = f"Title: {r.get('title', '')}\nURL: {r.get('url', '')}\nSnippet: {r.get('content', '')}"
                docs.append(Document(page_content=content, metadata={"url": r.get("url", "")}))
        return {"documents": docs}

    def _generate_answer(self, state: GraphState) -> dict:
        question = state["question"]
        documents = state["documents"]

        prompt = ChatPromptTemplate.from_template(
            "You are a helpful career assistant.\n"
            "Answer the user's question using only the retrieved job listings.\n\n"
            "Context:\n{context}\n\n"
            "Question: {question}\n\n"
            "Answer:"
        )
        generation_chain = prompt | self.llm | StrOutputParser()
        context_str = "\n\n---\n\n".join([d.page_content for d in documents])
        generation = generation_chain.invoke({"context": context_str, "question": question})
        return {"generation": generation, "documents": documents}

    def _decide_action(self, state: GraphState) -> str:
        return "generate" if state["is_relevant"] == "yes" else "web_search"

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(GraphState)
        workflow.add_node("reformulate", self._reformulate_query)
        workflow.add_node("retrieve", self._retrieve_documents)
        workflow.add_node("grade_documents", self._grade_documents)
        workflow.add_node("generate", self._generate_answer)
        workflow.add_node("web_search", self._web_search)

        workflow.set_entry_point("reformulate")
        workflow.add_edge("reformulate", "retrieve")
        workflow.add_edge("retrieve", "grade_documents")
        workflow.add_conditional_edges("grade_documents", self._decide_action,
            {"web_search": "web_search", "generate": "generate"})
        workflow.add_edge("web_search", "generate")
        workflow.add_edge("generate", END)

        return workflow.compile()


# --- Streamlit UI connected to backend ---
def run_ui():
    st.title("💼 Job Search Agent")
    st.write("Ask me about jobs and I’ll search the database + web if needed.")

    query = st.text_input("Enter your job search query:")
    if st.button("Search") and query:
        agent = Correct(csv_path="data/jobs.csv")
        result = agent.app.invoke({
            "question": query,
            "messages": [HumanMessage(content=query)]
        })

        st.subheader("📋 Answer")
        st.write(result["generation"])

        with st.expander("Retrieved Context"):
            for doc in result.get("documents", []):
                st.write(doc.page_content)


if __name__ == "__main__":
    run_ui()
