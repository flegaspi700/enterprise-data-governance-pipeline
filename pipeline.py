import os
from pypdf import PdfReader

# =====================================================================
# PROGRAM MANAGED CONFIGURATION
# =====================================================================
# These directories map directly to our Technical Architecture Document (TAD)
SOURCE_DIR = "source_documents"
SANITIZED_DIR = "sanitized_output"
REVIEW_DIR = "human_review_queue"

def extract_text_from_pdf(pdf_path):
    """
    Core Ingestion Engine: Reads a local PDF file and extracts raw text.
    Fails gracefully if the file is corrupted or unreadable.
    """
    try:
        reader = PdfReader(pdf_path)
        extracted_text = ""
        
        # Loop through each page and append text
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                extracted_text += page_text + "\n"
                
        return extracted_text.strip()
    except Exception as e:
        print(f"[ERROR] Failed to read PDF file at {pdf_path}. Context: {e}")
        return None

def run_ingestion_pipeline():
    """
    Orchestrates Sprint 1 tracking criteria:
    1. Scans the source directory for incoming files.
    2. Logs file discovery.
    3. Triggers the text extraction pipeline.
    """
    print("=" * 60)
    print("STARTING RUN: Enterprise Data Ingestion Pipeline (Phase 1)")
    print("=" * 60)
    
    # Scan source directory for PDF files
    if not os.path.exists(SOURCE_DIR):
        print(f"[ERROR] Source directory '{SOURCE_DIR}' does not exist.")
        return
        
    incoming_files = [f for f in os.listdir(SOURCE_DIR) if f.endswith('.pdf')]
    
    if not incoming_files:
        print(f"[STATUS] Ingestion pool empty. Place a sample PDF in '{SOURCE_DIR}/' to test.")
        return

    print(f"[INFO] Discovered {len(incoming_files)} pending file(s) for ingestion.\n")

    for file_name in incoming_files:
        file_path = os.path.join(SOURCE_DIR, file_name)
        print(f"--> Processing File: {file_name}")
        
        # Execute text extraction
        raw_text = extract_text_from_pdf(file_path)
        
        if raw_text:
            character_count = len(raw_text)
            print(f"    [SUCCESS] Extraction complete. Captured {character_count} characters.")
            # NOTE FOR SPRINT 2: This raw_text payload will be passed to our local ML classification layer here.
        else:
            print(f"    [FAILED] Skipping file due to extraction errors.")

    print("\n" + "=" * 60)
    print("RUN COMPLETE: Pipeline idling.")
    print("=" * 60)

if __name__ == "__main__":
    run_ingestion_pipeline()