# Roadmap & Improvements Tracker: Data Ingestion Governance Pipeline

This document tracks the architectural enhancements, security compliance steps, and feature additions for the enterprise data governance pipeline.

---

## 📊 Feature Status Tracker

| Feature / Improvement | Target Phase | Status | Completed Date | Description |
| :--- | :---: | :---: | :---: | :--- |
| **Externalized Config (`config.json`)** | Phase 1 | **Completed** | 2026-07-22 | Moved folder settings and regex rule patterns to external config. |
| **spaCy ML NER Integration** | Phase 1 | **Completed** | 2026-07-22 | Local Named Entity Recognition using spaCy's `en_core_web_sm` pipeline. |
| **Dependency Standardization** | Phase 1 | **Completed** | 2026-07-22 | Pin project dependencies in `requirements.txt`. |
| **OCR Fallback (Scanned PDFs)** | Phase 2 | **Completed** | 2026-07-22 | OCR stream extraction using Tesseract or similar for non-readable PDFs. |
| **Background Watchdog Daemon** | Phase 3 | **Completed** | 2026-07-22 | Continuous local ingestion via watchdog daemon on `source_documents/`. |
| **Streamlit Triage Dashboard** | Phase 4 | *Pending* | - | Streamlit web panel to approve or reject flagged high-risk entities. |
| **Automated Testing Suite** | Phase 5 | *Pending* | - | Unit and integration testing for pipeline components. |

---

## 🛠️ Detailed Roadmap & Implementation Status

### 1. Externalized Rule Configuration (`config.json`)
* **Objective**: Separate governance policy settings from core logic.
* **Status**: **Completed** ✅
* **Details**: 
  - Implemented dynamic loading from [config.json](file:///d:/Learn/ag_enterprise_data_governance_pipeline/enterprise-data-governance-pipeline/config.json).
  - Configurable regex compliance rules, high risk counts, and engine states.
  - Graceful default config fallback behavior when file is missing or corrupt.

### 2. spaCy Machine Learning NER Integration
* **Objective**: Context-aware entity masking to supplement pattern regex.
* **Status**: **Completed** ✅
* **Details**: 
  - Integrated `spaCy` NLP core with the optimized `en_core_web_sm` model.
  - Enabled detection of names (`PERSON`), organizations (`ORG`), and locations (`GPE`).
  - Added token substitutions without character offset drift during sequence modification.

### 3. Dependency Standardization
* **Objective**: Pin versions and outline setup procedures.
* **Status**: **Completed** ✅
* **Details**: 
  - Created [requirements.txt](file:///d:/Learn/ag_enterprise_data_governance_pipeline/enterprise-data-governance-pipeline/requirements.txt) pinning `pypdf==6.14.2` and `spacy==3.8.14`.
  - Documented setup instructions to download required language assets.

### 4. OCR Fallback for Scanned Documents
* **Objective**: Guard against empty text extraction from scanned/image-only PDFs.
* **Status**: **Completed** ✅
* **Details**:
  - Add text-length evaluation checks (character count == 0).
  - Implement OCR engine integration using PyMuPDF and `pytesseract` configured via `config.json`.
  - Route OCR failures or files with empty OCR output to the human review queue.

### 5. Background Ingestion Daemon (File-Watching)
* **Objective**: Continuous execution pattern instead of batch-oriented manual execution.
* **Status**: **Completed** ✅
* **Details**:
  - Integrate `watchdog` to monitor the file system directory [source_documents](file:///d:/Learn/ag_enterprise_data_governance_pipeline/enterprise-data-governance-pipeline/source_documents) in real-time.
  - Auto-trigger ingestion sequence on file creation and move events.
  - Added safety debounce and delay mechanisms in `watcher.py` to prevent processing partial writes.

### 6. Streamlit Administrative Triage Dashboard
* **Objective**: Lightweight "Human-in-the-Loop" administrative approval/rejection panel.
* **Status**: *Pending* ⏳
* **Details**:
  - Parse metadata from [human_review_queue](file:///d:/Learn/ag_enterprise_data_governance_pipeline/enterprise-data-governance-pipeline/human_review_queue).
  - Build simple comparison diff showing before/after text masking.
  - Implement Approve (archive & save sanitized) and Reject actions.
