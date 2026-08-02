# Implementation Plans

This document captures the detailed implementation plan for the next phases of the enterprise data governance pipeline.

---

## Phase 1 — Foundation and Core Governance

### Completed items
- Externalized configuration via config.json
- spaCy-based NER masking support
- Standardized dependencies in requirements.txt
- OCR fallback for scanned PDFs
- File-watching ingestion daemon
- Streamlit review dashboard
- Batch-folder ingestion from the dashboard for selected PDFs
- Recursive folder discovery and process-all batch intake from the dashboard
- Queue filtering by status, risk, and date
- Bulk approve/reject actions for review items
- Operational dashboard summary metrics for pending, reviewed, archived, and sanitized items

---

## Phase 2 — Polished UI and Operational Review Experience

### 7. UI/UX overhaul
**Goal**
- Make the review experience feel more like a polished operations tool.

**Status**
- Completed

**Implementation highlights**
1. Reworked the dashboard into a clearer review experience with a sidebar queue and detail view.
2. Added structured queue metadata, status labels, and improved document detail presentation.
3. Refined the before/after diff rendering for readability.
4. Added batch intake controls for folder selection, recursive discovery, process-all intake, and operational summary metrics.

**Success criteria**
- Reviewers can quickly scan pending items.
- The selected document view is clear and easy to interpret.
- The approve/reject workflow feels intuitive.

### 8. Advanced review workflow
**Goal**
- Improve the efficiency and manageability of review operations.

**Status**
- Completed

**Implementation highlights**
1. Added filtering by status, risk level, and date.
2. Added bulk approve/reject actions for multiple pending items.
3. Improved queue navigation for larger sets of documents.
4. Added a processing summary panel to show pending, reviewed, archived, and sanitized counts.

**Success criteria**
- Reviewers can manage larger queues without friction.
- Decisions are logged in a useful and auditable way.

### 9. Analytics and reporting
**Goal**
- Provide operational visibility into governance outcomes.

**Status**
- In progress

**Implementation highlights**
1. Added dashboard summary metrics for pending, reviewed, archived, and sanitized items.
2. Next planned step: show simple charts or trend summaries for review activity.
3. Next planned step: export review results and metrics for reporting purposes.

**Success criteria**
- Administrators can quickly understand review volume and outcomes.
- Reporting can be shared for audit and governance review.

---

## Future phases

### Potential next areas
- Authentication and role-based access
- Configurable governance policies from the UI
- Packaging and deployment improvements
- Expanded PII and compliance rule support
