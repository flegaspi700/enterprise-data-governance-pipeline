# Future Improvements & Roadmap: Data Ingestion Governance Pipeline

This document captures architectural and functional recommendations to transition the local governance pipeline from a prototype to an enterprise-ready production system.

---

## 1. Externalized Rule Configuration (`config.json` / `config.yaml`)
* **Objective**: Separate governance policy settings from the core python execution logic.
* **Details**:
  * Create a `config.yaml` to specify folder structures, `HIGH_RISK_THRESHOLD`, and lists of regex pattern rules.
  * Enable/disable specific PII classes dynamically.
* **Value**: Allows security teams to adjust compliance rules (e.g., adding credit card numbers or local tax identifiers) without touching the deployment codebase.

---

## 2. OCR Fallback for Scanned Documents
* **Objective**: Guard against empty text extractions in image-only or scanned PDFs.
* **Details**:
  * Add checks to detect zero-character text extractions.
  * Integrate an open-source OCR tool (like `pytesseract` or `ocrmypdf`) as a fallback stream.
  * Route files that fail OCR directly to the `human_review_queue/`.
* **Value**: Closes a security loophole where raw text is empty but the image contains highly sensitive information.

---

## 3. Machine Learning Named Entity Recognition (NER)
* **Objective**: Introduce context-aware entity masking alongside strict pattern-based matching.
* **Details**:
  * Implement `spaCy` NLP core with the optimized `en_core_web_sm` pipeline.
  * Detect dynamic, context-specific tokens: `PERSON` (names), `ORG` (companies), `GPE` (locations), and custom entity mappings.
  * Assign confidence score matrices to entities to guide threshold decisions.
* **Value**: Protects sensitive unstructured text fields (such as narrative fields in contracts or letters) that regex patterns cannot cover.

---

## 4. Background Ingestion Daemon (File-Watching)
* **Objective**: Change from batch-oriented manual execution to a continuous background process.
* **Details**:
  * Implement Python's `watchdog` library to monitor `source_documents/`.
  * Trigger processing events dynamically as soon as a new file lands.
  * Write execution status to a centralized local log file.
* **Value**: Operates similarly to standard cloud ingestion buckets (e.g., AWS S3 event triggers or Azure Blob triggers) inside the local infrastructure.

---

## 5. Streamlit Administrative Triage Dashboard
* **Objective**: Provide a simple visual interface for the "Human-in-the-Loop" review step.
* **Details**:
  * Build a lightweight, local Streamlit dashboard.
  * Parse files inside `human_review_queue/` and render their corresponding `_review.json` files.
  * Display a diff viewer showing highlighted PII tags.
  * Provide "Approve" (move to sanitized output pool) and "Reject" (delete or isolate) actions.
* **Value**: Democratizes the auditing process, allowing compliance officers to easily manage and clear the triage queue.
