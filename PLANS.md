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

---

## Phase 2 — Polished UI and Operational Review Experience

### 7. UI/UX overhaul
**Goal**
- Make the review experience feel more like a polished operations tool.

**Implementation steps**
1. Rework the dashboard layout into a clearer two-panel experience.
2. Add a structured pending review queue with metadata and status indicators.
3. Improve the detail view for the selected document.
4. Refine the before/after diff presentation for readability.
5. Add visual polish with spacing, badges, and clearer button hierarchy.

**Success criteria**
- Reviewers can quickly scan pending items.
- The selected document view is clear and easy to interpret.
- The approve/reject workflow feels intuitive.

### 8. Advanced review workflow
**Goal**
- Improve the efficiency and manageability of review operations.

**Implementation steps**
1. Add filtering by status, risk level, and date.
2. Support bulk approve/reject actions.
3. Capture reviewer comments and preserve richer decision history.
4. Improve queue navigation for larger sets of documents.

**Success criteria**
- Reviewers can manage larger queues without friction.
- Decisions are logged in a useful and auditable way.

### 9. Analytics and reporting
**Goal**
- Provide operational visibility into governance outcomes.

**Implementation steps**
1. Add dashboard summary metrics for pending, approved, and rejected items.
2. Show simple charts or trend summaries for review activity.
3. Export review results and metrics for reporting purposes.

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
