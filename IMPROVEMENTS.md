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
| **Streamlit Triage Dashboard** | Phase 4 | **Completed** | 2026-07-27 | Streamlit web panel to review flagged high-risk entities, compare before/after masking, and approve or reject items. |
| **Batch Intake and Multi-File Processing** | Phase 4 | **Completed** | 2026-08-02 | Added dashboard intake for selected files, recursive discovery, process-all processing, and operational summary metrics. |
| **Queue Filters and Bulk Review Actions** | Phase 4 | **Completed** | 2026-08-02 | Added status, risk, and date filtering plus bulk approve/reject workflow support. |
| **Automated Testing Suite** | Phase 5 | **Completed** | 2026-08-02 | Added regression tests for batch intake, dashboard helpers, and review workflow behavior. |

---

## 🛠️ Detailed Roadmap & Implementation Status

## Phase 1 — Foundation and Core Governance

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
* **Status**: **Completed** ✅
* **Details**:
  - Parsed metadata from [human_review_queue](file:///d:/Learn/ag_enterprise_data_governance_pipeline/enterprise-data-governance-pipeline/human_review_queue).
  - Built a Streamlit review experience with before/after masking diff rendering.
  - Implemented Approve and Reject actions that move reviewed items into approved/rejected queues and update the ingestion manifest.

---

## Phase 2 — Polished UI and Operational Review Experience

### 7. UI/UX overhaul
* **Objective**: Transform the current review screen into a more polished, operationally friendly interface.
* **Status**: **Completed** ✅
* **Details**:
  - Improved the layout with a clearer pending-items queue and main detail pane.
  - Added stronger visual hierarchy for document metadata, risk information, and review actions.
  - Refined the before/after diff view for better readability and usability.
  - Added batch intake controls for folder selection, recursive discovery, process-all intake, and operational summary metrics.

### 8. Advanced review workflow
* **Objective**: Make the review experience faster, more scalable, and better suited for team use.
* **Status**: **Completed** ✅
* **Details**:
  - Added filtering by status, risk level, and date to manage large review queues.
  - Added bulk approve/reject actions for efficiency.
  - Added a summary panel to surface operational counts after intake and review.

### 9. Analytics and reporting
* **Objective**: Provide operational visibility into review outcomes and governance performance.
* **Status**: *In progress* ⏳
* **Details**:
  - Added dashboard counts for pending, reviewed, archived, and sanitized items.
  - Next planned step: add charts or summaries for review volume and risk trends.
  - Next planned step: export review decisions and aggregate metrics for governance reporting.
