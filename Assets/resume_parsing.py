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

try:
    import spacy
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
        nlp = spacy.load("en_core_web_sm")
except ImportError:
    nlp = None

def extract_entities(text: str) -> dict:
    if nlp is None:
        return {"error": "spacy not installed"}
    
    doc = nlp(text)
    entities = {
        "organizations": list(set(ent.text for ent in doc.ents if ent.label_ == "ORG")),
        "locations": list(set(ent.text for ent in doc.ents if ent.label_ in ("GPE", "LOC"))),
        "dates": list(set(ent.text for ent in doc.ents if ent.label_ == "DATE")),
        "noun_chunks": list(set(chunk.text.strip() for chunk in doc.noun_chunks if len(chunk.text.strip()) > 3))
    }
    return entities

if __name__ == "__main__":
    text = clean_text(text_extractor("Data/Suryansh_Resume.pdf"))
    print(text[:500])
    print(extract_entities(text))
