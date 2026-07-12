import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in the project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
from langchain_community.document_loaders import CSVLoader
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter
import operator
from typing import List, TypedDict, Annotated
import pandas as pd
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, END

print("--- Initializing Corrective RAG Application ---")
#---Define the State for our Graph
class GraphState(TypedDict):
    """
    Represents the state of our graph.
    """
    question: str
    generation: str
    documents: List[Document]
    messages: Annotated[list, operator.add]
    is_relevant: str

# --- Define the Pydantic model for Grader ---
class GradeDcuments(BaseModel):
    """Binary score for document relevance"""
    score: str = Field(description="Document are relevant to the question, 'yes' or 'no'")

class Correcti:
    def __init__(self, csv_path: str, persist_directory: str = "./chroma_db"):
         print("--- Initializing Corrective RAG Application ---")
         self.csv_path = csv_path
         self.persist_directory = persist_directory
         # ---Initialize Models and Tools --- 
         self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
         self.embedding_model = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
         self.tavily_tool = TavilySearch(max_results=5)
         # ---Initialize Vector Store --- 
         self.vectorstore = self._setup_vectorstore()
         self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})
         # ---Build the LangGraph Workflow ---
         self.app = self._build_graph()
         print("--- Application Initialized Successfully ---")
         
    def _setup_vectorstore(self) -> Chroma:
        if os.path.exists(self.persist_directory):
            print(f"Loading existing vector store from '{self.persist_directory}'...")
            return Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embedding_model
            )
        else:
            print(f"No existing store found. Creating new vector store from '{self.csv_path}'...")
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
            print(f"Vector store created and saved to '{self.persist_directory}'.")
            return vectorstore


    # Reformulate Query
    def _reformulate_query(self, state: GraphState) -> dict:
        print("--- Node: Reformulating Query ---")
        question = state["question"]
        messages = state["messages"]
        if not messages or len(messages) <= 1:
            return {"question": question}

        prompt = ChatPromptTemplate.from_template(
            "Given the conversation history and a follow-up question, reformulate the follow-up question "
            "into a standalone search query that can be used for retrieving relevant job listings.\n\n"
            "History:\n{history}\n\n"
            "Follow-up Question: {question}\n\n"
            "Standalone Query:"
        )
        history_str = "\n".join([f"{type(msg).__name__}: {msg.content}" for msg in messages[:-1]])
        chain = prompt | self.llm | StrOutputParser()
        reformulated = chain.invoke({"history": history_str, "question": question})
        print(f"--- Original: {question} -> Reformulated: {reformulated} ---")
        return {"question": reformulated}

    # Retrieve Documents
    def _retrieve_documents(self, state: GraphState) -> dict:
        print("--- NODE: Retrieving Documents ---")
        question = state["question"]
        documents = self.retriever.invoke(question)
        return {"documents": documents, "question": question}

    # Grade Documents
    def _grade_documents(self, state: GraphState) -> dict:
        print("---NODE: Grading Document Relevance ---")
        question = state["question"]
        documents = state["documents"]

        structured_llm_grader = self.llm.with_structured_output(GradeDcuments)
        prompt = ChatPromptTemplate.from_template(
            "You are a grader assessing relevance of a retrieved job listing to a user's question.\n"
            "Retrieved Document:\n{document}\n\n"
            "User Question: {question}\n\n"
            "Does the job listing contain relevant info for the question? Respond with 'yes' or 'no'."
        )
        grader_chain = prompt | structured_llm_grader

        is_relevant = "no"
        for d in documents:
            score = grader_chain.invoke({"question": question, "document": d.page_content})
            grade = score.score
            if grade.lower() == "yes":
                print("--- GRADE: Found a relevant document. ---")
                is_relevant = "yes"
                break

        return {"is_relevant": is_relevant}
        
    # Web Search (Corrective Step)
    def _web_search(self, state: GraphState) -> dict:
        print("--- NODE: Performing Web Search (Corrective Step) ---")
        question = state["question"]
        web_results = self.tavily_tool.invoke({"query": question})
        
        docs = []
        if isinstance(web_results, dict) and 'results' in web_results:
            for r in web_results['results']:
                content = f"Title: {r.get('title', '')}\nURL: {r.get('url', '')}\nSnippet: {r.get('content', '')}"
                docs.append(Document(page_content=content, metadata={"url": r.get("url", "")}))
        elif isinstance(web_results, list):
            for r in web_results:
                if isinstance(r, dict):
                    content = f"Title: {r.get('title', '')}\nURL: {r.get('url', '')}\nSnippet: {r.get('content', '')}"
                    docs.append(Document(page_content=content, metadata={"url": r.get("url", "")}))
        else:
            docs.append(Document(page_content=str(web_results)))
            
        return {"documents": docs}

    # Generate Answer
    def _generate_answer(self, state: GraphState) -> dict:
        print("--- NODE: Generating Answer ---")
        question = state["question"]
        documents = state["documents"]
        prompt = ChatPromptTemplate.from_template(
            "You are a helpful career assistant.\n"
            "Answer the user's question using only the following retrieved job listings and search context.\n"
            "If you do not know the answer or if no listings are relevant, say so politely.\n\n"
            "Retrieved Context:\n{context}\n\n"
            "User Question: {question}\n\n"
            "Answer:"
        )
        generation_chain = prompt | self.llm | StrOutputParser()
        
        context_str = "\n\n---\n\n".join([d.page_content for d in documents])
        generation = generation_chain.invoke({"context": context_str, "question": question})
        return {"generation": generation}

    # Conditional Edge Logic
    def _decide_action(self, state: GraphState) -> str:
        print("--- CONDITIONAL EDGE: Assessing Relevance ---")
        if state["is_relevant"] == "yes":
            print("--- DECISION: Documents are relevant. Proceeding to generation. ---")
            return "generate"
        else:
            print("--- DECISION: Documents not relevant. Proceeding Web Search. ---")
            return "web_search"

    # Graph Building
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(GraphState)
        # Define the nodes
        workflow.add_node("reformulate", self._reformulate_query)
        workflow.add_node("retrieve", self._retrieve_documents)
        workflow.add_node("grade_documents", self._grade_documents)
        workflow.add_node("generate", self._generate_answer)
        workflow.add_node("web_search", self._web_search)
        # Build graph
        workflow.set_entry_point("reformulate")
        workflow.add_edge("reformulate", "retrieve")
        workflow.add_edge("retrieve","grade_documents")
        workflow.add_conditional_edges(
            "grade_documents",
            self._decide_action,
            {
                "web_search": "web_search", 
                "generate": "generate",
            },
        )
        workflow.add_edge("web_search", "generate")
        workflow.add_edge("generate", END)
        # Compile the workflow
        return workflow.compile()  

if __name__ == "__main__":
    # Initialize with your CSV path
    app = Correcti(csv_path="data/jobs.csv")

    # Run the graph with a sample question
    result = app.app.invoke({
        "question": "Show me software engineering jobs in Pune",
        "messages": [HumanMessage(content="Show me software engineering jobs in Pune")]
    })

    print("\n--- Final Answer ---")
    print(result["generation"])
