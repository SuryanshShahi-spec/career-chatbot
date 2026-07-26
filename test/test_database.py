import os 
import sys
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv  # <-- New import
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

# Load environment variables from .env file
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

def test_pipeline():
    print("Starting local database connection test...")

    # 1. Test CSV File Access
    csv_path = str(PROJECT_ROOT / "data" / "jobs.csv")
    if not os.path.exists(csv_path):
        print(f"CRITICAL ERROR: '{csv_path}' not found in the current directory.")
        return
    
    try:
        df = pd.read_csv(csv_path)
        print(f"Success: 'jobs.csv' {len(df)} job listings from CSV.")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to load CSV: {e}")
        return
    
    # 2. Test Embeddings connection (Gemini API)
    print("Contacting Google API with gemini-embedding-001...")
    try:
        # LangChain automatically looks for the GOOGLE_API_KEY environment variable
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
        
        # Test an isolated mathematical embedding vector generation
        test_vector = embeddings.embed_query("Test connection to jobs database")
        print(f"Success: Gemini API connected. Generated vector with {len(test_vector)} dimensions")
    except Exception as e:
        print(f"Error connecting to Gemini Embeddings API: {e}")
        print("Hint: Double-check your GOOGLE_API_KEY environment variable inside the .env file.")
        return
    
    # 3. Test Vector Store Retrieval
    print("Testing local Vector DB path and querying engine...")
    persist_directory = str(PROJECT_ROOT / "chroma_db")
    if not os.path.exists(persist_directory):
        print("Warning: './chroma_db' folder does not exist yet. You must run your indexing script first.")
        return

    try:
        vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings
        )
        retriever = vectorstore.as_retriever(search_kwargs={"k": 1})
        
        # Pull a test sample query 
        sample_results = retriever.invoke("Software Engineer development")

        if sample_results:
            print(f"Success: Retrieved data from vector store matching query.")
            # Note: sample_results is a list, so we pull index [0] before reading page_content
            print(f"Sample Document Preview:\n--- \n{sample_results[0].page_content[:150]}...\n--- ")
            print("\nALL DATABASE CONNECTION TESTS PASSED SUCCESSFULLY!")
        else:
            print("DB Connected, but search returned 0 results. Ensure documents were loaded properly.")

    except Exception as e:
        print(f"Error connecting to Vector DB: {e}")
        print("Hint: If you changed your model, delete './chroma_db' manually and rebuild it.")

if __name__ == "__main__":
    test_pipeline()
