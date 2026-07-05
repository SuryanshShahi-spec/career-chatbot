import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# For Gemini
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai

# For Groq
from langchain_groq import ChatGroq


class JobSearchAssistant:
    def __init__(self, file_path="jobs.csv", api_type="groq", model=None):
        """
        Initialize the assistant with Gemini or Groq API.
        
        Args:
            file_path: Path to the CSV file
            api_type: "gemini" or "groq"
            model: Specific model to use (optional)
        """
        # 1. Handle .env loading properly
        env_path = Path(".env")
        if env_path.is_dir():
            env_path = env_path / ".env"

        if not env_path.exists():
            raise FileNotFoundError(f"Unable to find the .env file at {env_path.resolve()}")

        load_dotenv(find_dotenv())

        self.api_type = api_type.lower()
        
        # 2. Setup API keys and models
        if self.api_type == "gemini":
            self.api_key = os.getenv("GOOGLE_API_KEY")
            if not self.api_key:
                raise ValueError("Missing GOOGLE_API_KEY in .env file")
            genai.configure(api_key=self.api_key)
            self.model = model or "gemini-1.5-flash"
            
        elif self.api_type == "groq":
            self.api_key = os.getenv("GROQ_API_KEY")
            if not self.api_key:
                raise ValueError("Missing GROQ_API_KEY in .env file")
            # Updated to use a currently supported model
            self.model = model or "llama-3.3-70b-versatile"  # Changed from decommissioned model
        else:
            raise ValueError("api_type must be 'gemini' or 'groq'")

        # 3. Use a free, local embedding model
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

        # 4. Load, chunk, and build the store
        self.vector_store = self._initialize_knowledge_base(file_path)
        
        # Track if we have any documents loaded
        self.has_documents = False

    def _chunk_data(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"The CSV file at '{file_path}' was not found. Please check the path.")

        try:
            loader = CSVLoader(
                file_path=file_path,
                csv_args={'delimiter': ',', 'quotechar': '"'},
                encoding='utf-8'
            )
            documents = loader.load()
        except UnicodeDecodeError:
            loader = CSVLoader(
                file_path=file_path,
                csv_args={'delimiter': ',', 'quotechar': '"'},
                encoding='cp1252'
            )
            documents = loader.load()

        if not documents:
            print("⚠️ Warning: No documents were loaded from the CSV file.")
            return None, []

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        docs = text_splitter.split_documents(documents)
        
        if docs:
            self.has_documents = True
            vector_store = Chroma.from_documents(docs, self.embeddings)
            return vector_store, docs
        else:
            print("⚠️ Warning: No chunks were created from the documents.")
            return None, []

    def _initialize_knowledge_base(self, file_path):
        vector_store, docs = self._chunk_data(file_path)
        
        if docs:
            print(f"✅ Total chunks created: {len(docs)}")
            print("\nFirst chunk example:")
            print(docs[0].page_content[:200] + "...")
            print("\nMetadata details:")
            print(docs[0].metadata)
        else:
            print("⚠️ No data loaded from CSV. The assistant will rely on general knowledge.")
            vector_store = None
            
        return vector_store

    def get_llm(self):
        """Initialize the appropriate LLM based on api_type"""
        if self.api_type == "gemini":
            return ChatGoogleGenerativeAI(
                model=self.model,
                temperature=0.3,
                google_api_key=self.api_key,
                convert_system_message_to_human=True
            )
        else:  # groq
            return ChatGroq(
                model=self.model,
                temperature=0.3,
                groq_api_key=self.api_key
            )

    def generate_response(self, query):
        try:
            llm_model = self.get_llm()
            
            # First, try to find relevant information in the CSV data
            if self.vector_store and self.has_documents:
                # Chroma returns cosine distance (0 means identical, greater values mean less similar)
                results = self.vector_store.similarity_search_with_score(query, k=3)
                
                RELEVANCE_THRESHOLD = 0.5
                relevant_chunks = [doc for doc, score in results if score < RELEVANCE_THRESHOLD]
                
                if relevant_chunks:
                    context = "\n\n".join([doc.page_content for doc in relevant_chunks])
                    prompt = f"""You are an assistant answering questions strictly based on the provided job listings context.
If the answer is not in the context, respond with: "I can't find relevant information for this query in the job listings."

Context from job listings:
{context}

Question: {query}
Answer:"""
                    
                    response = llm_model.invoke(prompt)
                    
                    # Check if the answer indicates no information found
                    if "I can't find relevant information" in response.content:
                        print("ℹ️ No relevant information in CSV. Falling back to general knowledge...")
                        return self._generate_general_answer(query, llm_model)
                    
                    return response.content
                else:
                    print("ℹ️ No relevant chunks found in CSV. Falling back to general knowledge...")
                    return self._generate_general_answer(query, llm_model)
            else:
                # No data in CSV, use general knowledge
                return self._generate_general_answer(query, llm_model)

        except Exception as e:
            # If there's an error with the CSV/vector search, try general knowledge
            print(f"⚠️ Error with CSV data: {str(e)}. Falling back to general knowledge...")
            try:
                return self._generate_general_answer(query, self.get_llm())
            except:
                return f"❌ Error: {str(e)}"

    def _generate_general_answer(self, query, llm_model):
        """Generate answer using general knowledge when CSV data is insufficient"""
        prompt = f"""The user asked a question that is outside the scope of our job listings.
Answer the question accurately using your general pre-trained knowledge.

Question: {query}
Answer:"""
        
        response = llm_model.invoke(prompt)
        return response.content


def run_assistant(api_type="groq", model=None):
    try:
        # Validate model choice
        if api_type == "groq" and not model:
            model = "llama-3.3-70b-versatile"  # Default to supported model
            
        assistant = JobSearchAssistant("data/jobs.csv", api_type=api_type, model=model)
        
        model_display = model or ("gemini-1.5-flash" if api_type == "gemini" else "llama-3.3-70b-versatile")
        print(f"\n✅ Using {api_type.upper()} API with model: {model_display}")
        print("ℹ️ Assistant will first search job listings, then fall back to general knowledge if needed.")
        print("Type 'exit' to quit\n")
        
        while True:
            user_query = input("\nAsk a question: ")
            if user_query.lower() == 'exit':
                break

            answer = assistant.generate_response(user_query)
            print(f"\nAnswer: {answer}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    # Using a currently supported Groq model
    run_assistant(api_type="groq", model="llama-3.3-70b-versatile")