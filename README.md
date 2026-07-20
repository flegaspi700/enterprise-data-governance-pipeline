# Enterprise Data Ingestion Governance & Guardrail Framework
**Technical Project Lead:** Frederick
**Role Framework:** Data Engineering & AI Infrastructure Governance
**Status:** Core Framework Live | Local Loopback Active

A robust, zero-cost automated data ingestion pipeline designed for regulated enterprise environments. This framework scans unstructured documentation, executes local pattern-matching tokenization to sanitize multi-class PII, evaluates structural compliance metrics, and enforces automated, threshold-based "Human-in-the-Loop" triage routing to prevent data leakage into downstream LLM vector databases.

---

## SYSTEM TOPOLOGY OVERVIEW

```text
            [ Local File System / Corporate Drive ]
                             │
                             ▼
  ┌─────────────────────────────────────────────────────┐
  │ Phase 1: Ingestion Engine                           │
  │ (Directory Sweeps, File System IO, Raw Extractor)   │
  └──────────────────────────┬──────────────────────────┘
                             │ (Raw Text Payload)
                             ▼
  ┌─────────────────────────────────────────────────────┐
  │ Phase 2: Local Governance Layer                     │
  │ (High-Performance Regex Compilation, Multi-PII)     │
  └──────────────────────────┬──────────────────────────┘
                             │ (Confidence & Risk Matrix)
                             ▼
  ┌─────────────────────────────────────────────────────┐
  │ Phase 3: Automated Triage Engine                    │
  │ (Threshold Assessment, Dual-Destination Forwarding) │
  └──────────────┬───────────────────────────┬──────────┘
                 │ (Score <= Threshold)      │ (Score > Threshold)
                 ▼                           ▼
    [ Sanitized Storage Pool ]     [ Human Review Directory ]
    (Cleaned Text Artifacts)       (Isolated Raw PDF Source)
```

## PROGRAM ROADMAP & TRACKING

### Sprint 1: Phase 1 — Ingestion Pipeline (Completed)
**Objective:** Establish a stable local ingestion pattern to scan source directories and convert unstructured files into accessible text streams.

**Execution:** Implemented local pypdf extraction daemons with integrated validation error handlers to cleanly parse multi-page document payloads without computing degradation.

### Sprint 2: Phase 2 — Multi-Class Governance Layer (Completed)
**Objective:** Integrate zero-cost, localized data-masking mechanisms to sanitize sensitive corporate data streams.

**Execution:** Built high-performance, pre-compiled regular expression patterns to scrub multi-class PII identifiers (Emails, Phone Numbers, and Social Security / Tax IDs), dynamically substituting them with secure redaction tokens (`[REDACTED_EMAIL]`, `[REDACTED_PHONE]`, `[REDACTED_TAX_ID]`).

### Sprint 3: Phase 3 — Risk Thresholding & Human-in-the-Loop Triage (Completed)
**Objective:** Enforce programmatic safety guardrails based on real-time data risk scoring.

**Execution:** Engineered an automated validation layer that totals policy violations per file. Documents exceeding the safety threshold are automatically flagged as high-risk, triggering a defensive copy of the raw source file into an isolated `human_review_queue` folder for administrator auditing.

## CORE ARCHITECTURAL BENEFITS

- **Data Isolation:** Operating 100% within the local system loopback memory stack. Zero data leaves the boundary network, ensuring ironclad compliance with corporate info-sec standards.
- **Cost Efficiency ($0 Budget):** Accomplished end-to-end extraction, governance, and data triage routing without dependencies on paid external APIs or vendor licenses.
- **Programmatic Flexibility:** Easily expanded to incorporate advanced Named Entity Recognition (NER) libraries or custom corporate taxonomy rules by modifying the localized classification engine.

## PROJECT SETUP & LOCAL EXECUTION

### 1. Prerequisites
Ensure you have Python 3.x installed on your local machine.

### 2. Environment Initialization
Clone the repository and install the open-source parsing engine:

```bash
git clone https://github.com/<your-username>/enterprise-data-governance-pipeline.git
cd enterprise-data-governance-pipeline
pip install pypdf
```

### 3. Pipeline Ingestion & Triage Verification
Drop an unstructured PDF document containing mock sensitive details into the `source_documents/` folder.

Run the main processing execution daemon:

```bash
python pipeline.py
```

Audit your local execution outputs:
- **Clean Data:** View the sanitized files inside `sanitized_output/`.
- **Escalated Audit Files:** Check `human_review_queue/` for isolated files that tripped the risk safety threshold.