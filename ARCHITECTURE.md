# TECHNICAL ARCHITECTURE DOCUMENT (TAD)
**System:** Automated Data Governance Pipeline
**Target Architecture:** Localized Secure Ingestion Pattern

## 1. System Topology Overview
The architecture is structured across three distinct execution domains to enforce logical separation of concerns. This mirrors a standard corporate staging-to-production lifecycle layout.

            [ Local File System / Corporate Drive ]
                             │
                             ▼
  ┌─────────────────────────────────────────────────────┐
  │ Phase 1: Ingestion Engine                           │
  │ (Directory Sweeps, Hash Tracking, Raw Extractor)    │
  └──────────────────────────┬──────────────────────────┘
                             │ (Raw Text Payload)
                             ▼
  ┌─────────────────────────────────────────────────────┐
  │ Phase 2: ML Compliance Layer                        │
  │ (spaCy NER Processing, PII Masking, Evaluation)      │
  └──────────────────────────┬──────────────────────────┘
                             │ (Confidence Score Matrix)
                             ▼
  ┌─────────────────────────────────────────────────────┐
  │ Phase 3: Route & Escalation Engine                  │
  │ (Threshold Assessment, Dual-Destination Forwarding) │
  └──────────────┬───────────────────────────┬──────────┘
                 │ (Score >= 0.90)           │ (Score < 0.90)
                 ▼                           ▼
    [ Sanitized Storage Pool ]     [ Human Review Directory ]
                                   (Triggers Automated JSON Payload)

## 2. Component Specifications
* **Data Sources:** Unstructured local storage directories acting as mock enterprise file shares.
* **Processing Core:** Python 3.x processing daemon operating file system IO operations. 
* **Classification Engine:** `spaCy` NLP core framework running the optimized `en_core_web_sm` pipeline for zero-latency local tokenization and entity validation.

## 3. Security, Risk, & Fault Domains
* **Data Privacy Vaulting:** No external network requests are permitted within the processing framework. All processing occurs strictly within the local loopback memory stack to preserve complete data isolation.
* **Pipeline Throttling:** The Phase 1 loop limits ingestion batching cycles to prevent compute degradation on localized infrastructure, simulating enterprise token/rate management controls.
