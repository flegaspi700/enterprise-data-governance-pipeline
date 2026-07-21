import os
import re
import shutil
import json
import hashlib
import datetime
from pypdf import PdfReader

# =====================================================================
# CONFIGURATION LOADER & RULE SETS
# =====================================================================
CONFIG = {}
PII_RULES = []

def load_config():
    global CONFIG, PII_RULES
    default_config = {
        "directories": {
            "source": "source_documents",
            "sanitized": "sanitized_output",
            "review": "human_review_queue",
            "archive": "archived_sources"
        },
        "manifest_file": "ingestion_manifest.json",
        "high_risk_threshold": 2,
        "enable_spacy_ner": True,
        "pii_rules": [
            {
                "name": "emails",
                "regex": "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}",
                "redaction_token": "[REDACTED_EMAIL]",
                "enabled": True
            },
            {
                "name": "phones",
                "regex": "\\b(?:\\+?1[-. ]?)?\\(?([0-9]{3})\\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})\\b",
                "redaction_token": "[REDACTED_PHONE]",
                "enabled": True
            },
            {
                "name": "ssns",
                "regex": "\\b\\d{3}-\\d{2}-\\d{4}\\b",
                "redaction_token": "[REDACTED_TAX_ID]",
                "enabled": True
            }
        ]
    }
    
    config_file = "config.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                CONFIG = json.load(f)
        except Exception as e:
            print(f"[WARNING] Failed to read {config_file}. Using default config. Context: {e}")
            CONFIG = default_config
    else:
        CONFIG = default_config
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(CONFIG, f, indent=4)
            print(f"[INFO] Generated default config file: {config_file}")
        except Exception as e:
            print(f"[WARNING] Failed to write default config. Context: {e}")

    # Compile regex rules
    PII_RULES = []
    for rule in CONFIG.get("pii_rules", []):
        if rule.get("enabled", True):
            try:
                compiled = re.compile(rule["regex"])
                PII_RULES.append({
                    "name": rule["name"],
                    "compiled_regex": compiled,
                    "redaction_token": rule["redaction_token"]
                })
            except Exception as e:
                print(f"[ERROR] Failed to compile regex for rule '{rule.get('name')}': {rule.get('regex')}. Context: {e}")

# Load configuration dynamically
load_config()

# Assign module-level constants for backward compatibility
SOURCE_DIR = CONFIG["directories"]["source"]
SANITIZED_DIR = CONFIG["directories"]["sanitized"]
REVIEW_DIR = CONFIG["directories"]["review"]
ARCHIVE_DIR = CONFIG["directories"]["archive"]
MANIFEST_FILE = CONFIG["manifest_file"]
HIGH_RISK_THRESHOLD = CONFIG["high_risk_threshold"]

# Ensure all local output directories exist
os.makedirs(SOURCE_DIR, exist_ok=True)
os.makedirs(SANITIZED_DIR, exist_ok=True)
os.makedirs(REVIEW_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)

def calculate_file_hash(file_path):
    """Computes SHA-256 hash of a file to track ingestion state."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        print(f"[ERROR] Failed to compute hash for {file_path}. Context: {e}")
        return None

def load_manifest():
    """Loads the ingestion manifest from disk."""
    if not os.path.exists(MANIFEST_FILE):
        return {}
    try:
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read manifest {MANIFEST_FILE}. Context: {e}")
        return {}

def save_manifest(manifest):
    """Saves the ingestion manifest to disk."""
    try:
        with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=4)
    except Exception as e:
        print(f"[ERROR] Failed to write manifest {MANIFEST_FILE}. Context: {e}")

# =====================================================================
# EXPANDED GOVERNANCE LAYER (FREE/LOCAL)
# =====================================================================
NLP_ENGINE = None

def load_spacy_engine():
    """Lazily loads the spaCy NLP model to conserve resources on startup."""
    global NLP_ENGINE
    if NLP_ENGINE is None:
        try:
            import spacy
            NLP_ENGINE = spacy.load("en_core_web_sm")
        except Exception as e:
            print(f"[ERROR] Failed to load spaCy model 'en_core_web_sm'. Context: {e}")
            NLP_ENGINE = None
    return NLP_ENGINE

def mask_sensitive_data(text):
    """
    Advanced Governance Layer: Scans text for dynamic PII rules loaded from 
    config.json, runs spaCy NER if enabled, redacts them locally, 
    and computes compliance risk metrics.
    """
    sanitized_text = text
    metrics = {rule["name"]: 0 for rule in PII_RULES}
    total_pii_count = 0
    
    # 1. Run Config Regex Rules
    for rule in PII_RULES:
        found_matches = len(rule["compiled_regex"].findall(sanitized_text))
        metrics[rule["name"]] = found_matches
        total_pii_count += found_matches
        # Execute local, zero-cost redactions
        sanitized_text = rule["compiled_regex"].sub(rule["redaction_token"], sanitized_text)
        
    # 2. Run spaCy NER if enabled in CONFIG
    if CONFIG.get("enable_spacy_ner", True):
        nlp = load_spacy_engine()
        if nlp:
            try:
                doc = nlp(sanitized_text)
                spacy_metrics = {"names": 0, "organizations": 0, "locations": 0}
                
                # Replace entities in reverse order of start_char to prevent offset shifting
                IGNORE_ENTITIES = {"ssn", "phone", "email", "tax id", "id"}
                entities = sorted(doc.ents, key=lambda e: e.start_char, reverse=True)
                for ent in entities:
                    # Ignore common label words to prevent false positives
                    entity_text = ent.text.lower().strip(" :.,")
                    if entity_text in IGNORE_ENTITIES:
                        continue
                        
                    if ent.label_ == "PERSON":
                        token = "[REDACTED_NAME]"
                        spacy_metrics["names"] += 1
                        total_pii_count += 1
                    elif ent.label_ == "ORG":
                        token = "[REDACTED_ORG]"
                        spacy_metrics["organizations"] += 1
                        total_pii_count += 1
                    elif ent.label_ == "GPE":
                        token = "[REDACTED_LOCATION]"
                        spacy_metrics["locations"] += 1
                        total_pii_count += 1
                    else:
                        continue
                        
                    # Replace slice of text
                    sanitized_text = sanitized_text[:ent.start_char] + token + sanitized_text[ent.end_char:]
                    
                # Update metrics dictionary
                for k, v in spacy_metrics.items():
                    metrics[k] = v
            except Exception as e:
                print(f"[ERROR] spaCy NER parsing failed. Context: {e}")
                
    metrics["total"] = total_pii_count
    
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

    manifest = load_manifest()
    manifest_updated = False

    for file_name in incoming_files:
        file_path = os.path.join(SOURCE_DIR, file_name)
        print(f"--> Processing File: {file_name}")
        
        # Calculate file hash for ingestion state tracking
        file_hash = calculate_file_hash(file_path)
        if not file_hash:
            print(f"    [FAILED] Skipping file due to hashing errors.")
            continue
            
        if file_hash in manifest:
            print(f"    [SKIP] Already processed (matching hash: {file_hash}). Moving to archive.")
            # Move to archive directory anyway to clean source directory
            try:
                shutil.move(file_path, os.path.join(ARCHIVE_DIR, file_name))
            except Exception as e:
                print(f"    [ERROR] Failed to move duplicate file to archive. Context: {e}")
            continue

        # 1. Ingestion Phase
        raw_text = extract_text_from_pdf(file_path)
        if raw_text is None:
            print(f"    [FAILED] Skipping file due to extraction errors.")
            continue
            
        if raw_text == "":
            print(f"    [RISK WARNING] File contains 0 characters of text (potential scanned/image PDF). Routing to review queue.")
            is_high_risk = True
            review_dest = os.path.join(REVIEW_DIR, file_name)
            try:
                shutil.copy2(file_path, review_dest)
                print(f"    [ROUTED] High-risk unreadable file copied to queue: {review_dest}")
                
                # Generate automated JSON payload metadata report for unreadable files
                review_metadata = {
                    "file_name": file_name,
                    "file_hash": file_hash,
                    "ingested_at": datetime.datetime.now().isoformat(),
                    "status": "UNREADABLE_IMAGE_PDF",
                    "risk_metrics": {
                        "total": "N/A",
                        "reason": "PDF contains no extractable text characters"
                    }
                }
                json_name = file_name.replace(".pdf", "_review.json")
                json_path = os.path.join(REVIEW_DIR, json_name)
                with open(json_path, "w", encoding="utf-8") as jf:
                    json.dump(review_metadata, jf, indent=4)
                print(f"    [METADATA] Generated review payload JSON: {json_path}")
            except Exception as e:
                print(f"    [ERROR] Failed to route file to review queue or write JSON payload. Context: {e}")
                
            # Update manifest details
            manifest[file_hash] = {
                "file_name": file_name,
                "processed_at": datetime.datetime.now().isoformat(),
                "pii_metrics": {"total": "N/A", "reason": "UNREADABLE_IMAGE_PDF"},
                "routed_to_review": True
            }
            manifest_updated = True
            
            # Housekeeping: Move processed file to archive directory to keep source clean
            try:
                shutil.move(file_path, os.path.join(ARCHIVE_DIR, file_name))
                print(f"    [HOUSEKEEPING] Moved original file to archive: {os.path.join(ARCHIVE_DIR, file_name)}")
            except Exception as e:
                print(f"    [ERROR] Failed to move file to archive. Context: {e}")
            continue
            
        print(f"    [SUCCESS] Ingested {len(raw_text)} characters.")
        
        # 2. Advanced Governance & Metrics Phase
        sanitized_text, metrics = mask_sensitive_data(raw_text)
        print(f"    [GOVERNANCE] Scan metrics: Emails: {metrics['emails']} | Phones: {metrics['phones']} | SSNs: {metrics['ssns']}")
        
        # 3. Human-in-the-Loop Routing Layer (Triage Logic)
        is_high_risk = metrics['total'] > HIGH_RISK_THRESHOLD
        if is_high_risk:
            print(f"    [RISK WARNING] Total PII violations ({metrics['total']}) exceed safety threshold ({HIGH_RISK_THRESHOLD}).")
            review_dest = os.path.join(REVIEW_DIR, file_name)
            try:
                shutil.copy2(file_path, review_dest)
                print(f"    [ROUTED] High-risk original file copied to queue: {review_dest}")
                
                # Generate automated JSON payload metadata report
                review_metadata = {
                    "file_name": file_name,
                    "file_hash": file_hash,
                    "ingested_at": datetime.datetime.now().isoformat(),
                    "status": "FLAGGED_FOR_REVIEW",
                    "risk_metrics": metrics
                }
                json_name = file_name.replace(".pdf", "_review.json")
                json_path = os.path.join(REVIEW_DIR, json_name)
                with open(json_path, "w", encoding="utf-8") as jf:
                    json.dump(review_metadata, jf, indent=4)
                print(f"    [METADATA] Generated review payload JSON: {json_path}")
            except Exception as e:
                print(f"    [ERROR] Failed to route file to review queue or write JSON payload. Context: {e}")
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
            
        # Update manifest details
        manifest[file_hash] = {
            "file_name": file_name,
            "processed_at": datetime.datetime.now().isoformat(),
            "pii_metrics": metrics,
            "routed_to_review": is_high_risk
        }
        manifest_updated = True
        
        # 5. Housekeeping: Move processed file to archive directory to keep source clean
        try:
            shutil.move(file_path, os.path.join(ARCHIVE_DIR, file_name))
            print(f"    [HOUSEKEEPING] Moved original file to archive: {os.path.join(ARCHIVE_DIR, file_name)}")
        except Exception as e:
            print(f"    [ERROR] Failed to move file to archive. Context: {e}")

    if manifest_updated:
        save_manifest(manifest)

    print("\n" + "=" * 60)
    print("RUN COMPLETE: Pipeline idling.")
    print("=" * 60)

if __name__ == "__main__":
    run_ingestion_pipeline()