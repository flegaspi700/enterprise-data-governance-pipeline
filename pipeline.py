import os
import re
import shutil
from pypdf import PdfReader

# =====================================================================
# PROGRAM MANAGED CONFIGURATION
# =====================================================================
SOURCE_DIR = "source_documents"
SANITIZED_DIR = "sanitized_output"
REVIEW_DIR = "human_review_queue"

# Risk Threshold: If a file has more than this many total PII leaks, route to review queue
HIGH_RISK_THRESHOLD = 2

# Ensure all local output directories exist
os.makedirs(SANITIZED_DIR, exist_ok=True)
os.makedirs(REVIEW_DIR, exist_ok=True)

# =====================================================================
# EXPANDED GOVERNANCE LAYER (FREE/LOCAL)
# =====================================================================
# High-performance compiled regex patterns for expanded PII detection
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_REGEX = re.compile(r'\b(?:\+?1[-. ]?)?\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})\b')
SSN_REGEX = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')

def mask_sensitive_data(text):
    """
    Advanced Governance Layer: Scans text for multiple PII types, 
    redacts them locally, and computes total compliance risk metrics.
    """
    sanitized_text = text
    
    # Track metrics for audit logging
    emails_found = len(EMAIL_REGEX.findall(sanitized_text))
    phones_found = len(PHONE_REGEX.findall(sanitized_text))
    ssns_found = len(SSN_REGEX.findall(sanitized_text))
    
    total_pii_count = emails_found + phones_found + ssns_found
    
    # Execute local, zero-cost redactions
    sanitized_text = EMAIL_REGEX.sub("[REDACTED_EMAIL]", sanitized_text)
    sanitized_text = PHONE_REGEX.sub("[REDACTED_PHONE]", sanitized_text)
    sanitized_text = SSN_REGEX.sub("[REDACTED_TAX_ID]", sanitized_text)
    
    metrics = {
        "emails": emails_found,
        "phones": phones_found,
        "ssns": ssns_found,
        "total": total_pii_count
    }
    
    return sanitized_text, metrics

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
    """Orchestrates Ingestion, Multi-Pattern Redaction, and Human-in-the-Loop Routing."""
    print("=" * 60)
    print("STARTING RUN: Multi-Layer Governance & Human-in-the-Loop Triage")
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
        
        # 2. Advanced Governance & Metrics Phase
        sanitized_text, metrics = mask_sensitive_data(raw_text)
        print(f"    [GOVERNANCE] Scan metrics: Emails: {metrics['emails']} | Phones: {metrics['phones']} | SSNs: {metrics['ssns']}")
        
        # 3. Human-in-the-Loop Routing Layer (Triage Logic)
        if metrics['total'] > HIGH_RISK_THRESHOLD:
            print(f"    [RISK WARNING] Total PII violations ({metrics['total']}) exceed safety threshold ({HIGH_RISK_THRESHOLD}).")
            review_dest = os.path.join(REVIEW_DIR, file_name)
            try:
                shutil.copy2(file_path, review_dest)
                print(f"    [ROUTED] High-risk original file copied to queue: {review_dest}")
            except Exception as e:
                print(f"    [ERROR] Failed to route file to review queue. Context: {e}")
        else:
            print(f"    [PASS] Low-risk file. Cleaned stream routing to standard output.")
            
        # 4. Storage Phase
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