import os 
import pypdf # Standard PDF text extractor

# Define your directories and tracking files
RESUME_DIR ="./resumes"
TRACKING_FILE = "processed_files.txt"
OUTPUT_LOG = "extracted_text.txt"

def get_processed_files():
    """Read the processed files list if exists."""
    if not os.path.exists(TRACKING_FILE):
        return set()
    with open(TRACKING_FILE, "r", encoding="utf-8") as f:
            #return set(f.read().splitlines())  # Using a set provides 0(1) Lookups
            return set(line.strip() for line in f if line.strip())

def mark_as_processed(file_path):
    """Log the fil path so it is skipped next time."""
    if filename in processed_files:
        return False # Already processed
    with open(TRACKING_FILE, "a", encoding="utf-8") as f:
        f.write(file_path + "\n")

def extract_text_from_pdf(file_path):
    """Basic PDF text extraction logic."""
    text = ""
    with open(file_path, "rb") as f:
      reader = pypdf.PdfReader(f)
      for page in reader.pages:
        text += page_text + "\n"
    return text

def main():
   # 1. load progress
   processed_files = get_processed_files()

   # 2. Gather all files to process
   all_files = [
      os.path.join(RESUME_DIR, f) 
      for f in os.listdir(RESUME_DIR)
      if f.lower().endswith(".pdf")
   ]

   print(f"Processing: {os.path.basename(file_path)}...")

   try:
      # Run your extraction logic
      extracted_text = extracted_text_from_pdf(file_path)

      # Save your results somewhere (database, append file, etc.)
      with open(OUTPUT_LOG, "a", encoding="utf-8") as out:
         out.write(f"--START: {file_path} --\n{extracted_text}\n\n")

      # CRITICAL: Successfully processed, save progress now
      mark_as_processed(file_path)

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        print("Script will more to next file. Progress safely tracked.")

if __name__ == "__main__":
    main()      