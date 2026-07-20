import os
import re
from pypdf import PdfReader

# =====================================================================
# PROGRAM MANAGED CONFIGURATION
# =====================================================================
SOURCE_DIR = "source_documents"
SANITIZED_DIR = "sanitized_output"
REVIEW_DIR = "human_review_queue"

# Ensure output directories exist locally
os.makedirs(SANITIZED_DIR, exist_ok=True)
os.makedirs(REVIEW_DIR, exist_ok=True)

# =====================================================================
# SPRINT 2: GOVERNANCE & MASKING REGEX PATTERNS (FREE/LOCAL)
# =====================================================================
# High-performance compiled regex patterns for zero-cost PII detection
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

def mask_sensitive_data(text):
    """
    Governance Layer: Scans text for PII patterns and redacts them.
    Tracks compliance metrics via local substitution counters.
    """
    sanitized_text = text
    
    # Count how many emails we find for logging purposes
    email_matches = EMAIL_REGEX.findall(sanitized_text)
    redaction_count = len(email_matches)
    
    # Perform the local redaction
    sanitized_text = EMAIL_REGEX.sub("[REDACTED_EMAIL]", sanitized_text)
    
    return sanitized_text, redaction_count

def extract_text_from_pdf(pdf_path):
    """Core Ingestion Engine: Reads a local PDF file and extracts raw text."""
    try:
        reader = PdfReader(pdf_path)
        extracted_text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                extracted_text += page_text + "\n"
        return extracted_text.strip()
    except Exception as e:
        print(f"[ERROR] Failed to read PDF file at {pdf_path}. Context: {e}")
        return None

def run_ingestion_pipeline():
    """Orchestrates Sprint 1 & 2: Ingests, redacts, and saves sanitized output."""
    print("=" * 60)
    print("STARTING RUN: Enterprise Data Governance Pipeline (Phase 1 & 2)")
    print("=" * 60)
    
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
        
        # 1. Ingestion Phase
        raw_text = extract_text_from_pdf(file_path)
        
        if not raw_text:
            print(f"    [FAILED] Skipping file due to extraction errors.")
            continue
            
        print(f"    [SUCCESS] Ingested {len(raw_text)} characters.")
        
        # 2. Governance & Masking Phase
        print(f"    [GOVERNANCE] Scanning text for sensitive PII data...")
        sanitized_text, emails_found = mask_sensitive_data(raw_text)
        
        if emails_found > 0:
            print(f"    [WARNING] Detected and masked {emails_found} instance(s) of Email PII.")
        else:
            print(f"    [CLEAN] No obvious Email PII patterns detected.")
            
        # 3. Output/Storage Phase
        output_file_name = file_name.replace(".pdf", "_sanitized.txt")
        output_path = os.path.join(SANITIZED_DIR, output_file_name)
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(sanitized_text)
            print(f"    [SAVED] Secure output written to: {output_path}")
        except Exception as e:
            print(f"    [ERROR] Failed to write sanitized file. Context: {e}")

    print("\n" + "=" * 60)
    print("RUN COMPLETE: Pipeline idling.")
    print("=" * 60)

if __name__ == "__main__":
    run_ingestion_pipeline()