from pypdf import PdfReader
import re

def text_extractor(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text if text else "No text found in PDF."

def clean_text(text):
    # 1. Remove weird non-ascii characters
    text = re.sub(r'[\u0080-\uFFFF]', '', text)
    
    # 2. Fix the split letter issue (e.g., "P y t h o n" -> "Python")
    # Matches a single letter, followed by a single space, if followed by another letter
    text = re.sub(r'(?<=\b\w)\s(?=\w\b)', '', text)
    
    # 3. Fix double spaces that happen between restored words
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

if __name__ == "__main__":
    print(clean_text(text_extractor("Data/Suryansh_Resume.pdf")))
