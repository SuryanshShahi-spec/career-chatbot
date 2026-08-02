import os 
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 1. Load the PDF file path
pdf_path = "Data\Suryansh_Resume.pdf"  # Replace with your actual PDF filename
loader = PyPDFLoader(pdf_path)

# 2. Extract and load pages into memory
# This reads page content along with metadata like page numbers
pages = loader.load()
print(f"Successfully loaded {len(pages)} pages from the PDF.")

# 3. Configure the Recursive Text Splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,      # Maximum characters per chunk (good default for RAG pipelines)
    chunk_overlap=200,    # 20% overlap protects context at boundaries
    length_function=len
)

# 4. Split the loaded PDF pages into smaller chunks
# This preserves metadata like {'source': 'your_document.pdf', 'page': 0} for each chunk
chunks = text_splitter.split_documents(pages)

# 5. Review the chunk outputs
print(f"Generated {len(chunks)} total text chunks.")

# Print an example chunk to verify structure
if chunks:
    sample_chunk = chunks[0]
    print("\n--- SAMPLE CHUNK METADATA ---")
    print(sample_chunk.metadata)
    print("\n--- SAMPLE CHUNK CONTENT ---")
    print(sample_chunk.page_content)
