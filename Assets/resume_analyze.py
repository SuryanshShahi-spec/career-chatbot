import os
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

class ResumeAnalyzer:
    """Resume analysis helper for parsing PDF resumes and summarizing chunks."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
        )

    def analyze_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text from a PDF file and split it into chunks."""
        loader = PyPDFLoader(pdf_path)
        pages = loader.load()
        chunks = self.splitter.split_documents(pages)

        summary_text = "\n\n".join(chunk.page_content for chunk in chunks[:5])

        return {
            "page_count": len(pages),
            "chunk_count": len(chunks),
            "chunks": chunks,
            "summary_text": summary_text,
        }

    def parse_text(self, text: str) -> str:
        """Optional helper to further process extracted resume text."""
        cleaned = text.strip()
        return cleaned


if __name__ == "__main__":
    analyzer = ResumeAnalyzer()
    result = analyzer.analyze_pdf("Data/Suryansh_Resume.pdf")
    print(f"Parsed {result['page_count']} pages into {result['chunk_count']} chunks.")
    if result["chunks"]:
        print("\n--- SAMPLE CHUNK ---")
        print(result["chunks"][0].page_content)
