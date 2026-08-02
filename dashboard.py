"""
dashboard.py
=====================================================================
Human-in-the-Loop Administrative Triage Dashboard (Streamlit)
=====================================================================
Companion UI for pipeline.py. Reads the review queue that the
ingestion pipeline populates, shows a before/after masking diff for
each flagged document, and lets an administrator Approve (finalize
the sanitized output) or Reject (quarantine it) each item.

Run with:
    streamlit run dashboard.py

Expects pipeline.py to be importable from the same directory (it
reuses CONFIG, directory paths, extraction, and masking functions
from that module so behavior never drifts from the batch pipeline).
"""

import os
import re
import json
import shutil
import difflib
import datetime

import streamlit as st

import pipeline as pl  # reuse config, dirs, extraction & masking logic

# ---------------------------------------------------------------------------
# Derived paths (subfolders of the existing review queue, created on demand)
# ---------------------------------------------------------------------------
APPROVED_DIR = os.path.join(pl.REVIEW_DIR, "_approved")
REJECTED_DIR = os.path.join(pl.REVIEW_DIR, "_rejected")
os.makedirs(APPROVED_DIR, exist_ok=True)
os.makedirs(REJECTED_DIR, exist_ok=True)

REVIEW_LOG_FILE = os.path.join(pl.REVIEW_DIR, "review_decisions.json")


# ---------------------------------------------------------------------------
# Data access helpers
# ---------------------------------------------------------------------------
def list_pending_reviews():
    """Return metadata dicts for every *_review.json still sitting in the
    top level of the review queue (i.e. not yet approved/rejected)."""
    items = []
    if not os.path.isdir(pl.REVIEW_DIR):
        return items

    for fname in sorted(os.listdir(pl.REVIEW_DIR)):
        if not fname.endswith("_review.json"):
            continue
        json_path = os.path.join(pl.REVIEW_DIR, fname)
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as e:
            st.warning(f"Could not parse {fname}: {e}")
            continue

        pdf_name = meta.get("file_name")
        pdf_path = os.path.join(pl.REVIEW_DIR, pdf_name) if pdf_name else None
        meta["_json_path"] = json_path
        meta["_json_name"] = fname
        meta["_pdf_path"] = pdf_path
        meta["_pdf_exists"] = bool(pdf_path and os.path.exists(pdf_path))
        items.append(meta)
    return items


def sanitized_path_for(file_name):
    """Map an original PDF file name to its expected sanitized .txt output."""
    out_name = file_name.replace(".pdf", "_sanitized.txt")
    return os.path.join(pl.SANITIZED_DIR, out_name)


def load_original_text(pdf_path):
    """Re-derive the 'before' text the same way pipeline.py does:
    direct extraction, falling back to OCR if empty."""
    text = pl.extract_text_from_pdf(pdf_path)
    if not text:
        text = pl.extract_text_via_ocr(pdf_path)
    return text or ""


def load_sanitized_text(file_name):
    path = sanitized_path_for(file_name)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read(), path
        except Exception as e:
            st.warning(f"Could not read sanitized file {path}: {e}")
    return None, path


def append_review_log(entry):
    log = []
    if os.path.exists(REVIEW_LOG_FILE):
        try:
            with open(REVIEW_LOG_FILE, "r", encoding="utf-8") as f:
                log = json.load(f)
        except Exception:
            log = []
    log.append(entry)
    try:
        with open(REVIEW_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=4)
    except Exception as e:
        st.warning(f"Could not write review log: {e}")


def get_status_badge(status):
    mapping = {
        "UNREADABLE_IMAGE_PDF": "⚠️",
        "APPROVED": "✅",
        "REJECTED": "❌",
    }
    return mapping.get(status, "●")


def get_status_label(status):
    mapping = {
        "UNREADABLE_IMAGE_PDF": "Unreadable image PDF",
        "PENDING_REVIEW": "Pending review",
        "APPROVED": "Approved",
        "REJECTED": "Rejected",
    }
    return mapping.get(status, (status or "UNKNOWN").replace("_", " ").title())


def get_risk_score(meta):
    risk_metrics = meta.get("risk_metrics", {}) or {}
    if not isinstance(risk_metrics, dict):
        return None

    for key in ("PII hits", "PII Hits", "pii_hits", "PII_HITS", "risk_score"):
        value = risk_metrics.get(key)
        if isinstance(value, (int, float)):
            return int(value)
    return None


def build_queue_summary(pending):
    total = len(pending)
    high_risk = sum(1 for meta in pending if (get_risk_score(meta) or 0) >= pl.HIGH_RISK_THRESHOLD)
    unreadable = sum(1 for meta in pending if meta.get("status") == "UNREADABLE_IMAGE_PDF")
    return {
        "total": total,
        "high_risk": high_risk,
        "unreadable": unreadable,
    }


def filter_pending_reviews(pending, query="", status_filter="All", risk_filter="All", date_filter="All"):
    """Filter pending review items by text, status, risk, and age."""
    filtered = list(pending)
    query = (query or "").strip().lower()

    if query:
        filtered = [
            meta for meta in filtered
            if query in (
                meta.get("file_name", meta.get("_json_name", "")) + " " + get_status_label(meta.get("status", "UNKNOWN"))
            ).lower()
        ]

    if status_filter and status_filter != "All":
        filtered = [meta for meta in filtered if meta.get("status") == status_filter]

    if risk_filter and risk_filter != "All":
        if risk_filter == "High risk":
            filtered = [meta for meta in filtered if (get_risk_score(meta) or 0) >= pl.HIGH_RISK_THRESHOLD]
        elif risk_filter == "Low risk":
            filtered = [meta for meta in filtered if (get_risk_score(meta) or 0) < pl.HIGH_RISK_THRESHOLD]

    if date_filter and date_filter != "All":
        now = datetime.datetime.now()
        cutoff = None
        if date_filter == "Last 24 hours":
            cutoff = now - datetime.timedelta(hours=24)
        elif date_filter == "Last 7 days":
            cutoff = now - datetime.timedelta(days=7)
        elif date_filter == "Last 30 days":
            cutoff = now - datetime.timedelta(days=30)
        if cutoff is not None:
            filtered = [
                meta for meta in filtered
                if _parse_review_timestamp(meta.get("ingested_at")) and _parse_review_timestamp(meta.get("ingested_at")) >= cutoff
            ]

    return filtered


def _parse_review_timestamp(value):
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value)
    except ValueError:
        return None


def bulk_decide_items(items, action, reason=""):
    """Approve or reject a collection of review items in one go."""
    for meta in items:
        if action == "APPROVE":
            approve_item(meta)
        elif action == "REJECT":
            reject_item(meta, reason=reason)


def discover_available_files(source_dir=None, recursive=False):
    source_dir = source_dir or pl.SOURCE_DIR
    discovered = pl.discover_pdf_files(source_dir, recursive=recursive)
    if recursive:
        return [os.path.relpath(path, source_dir).replace(os.sep, "/") for path in discovered]
    return [os.path.basename(path) for path in discovered]


def update_manifest_decision(file_hash, decision, reason=""):
    if not file_hash:
        return
    manifest = pl.load_manifest()
    if file_hash in manifest:
        manifest[file_hash]["review_decision"] = decision
        manifest[file_hash]["review_decided_at"] = datetime.datetime.now().isoformat()
        if reason:
            manifest[file_hash]["review_reason"] = reason
        pl.save_manifest(manifest)


# ---------------------------------------------------------------------------
# Word-level diff rendering
# ---------------------------------------------------------------------------
_TOKEN_RE = re.compile(r"\s+|\w+|[^\w\s]")


def _tokenize(text):
    return _TOKEN_RE.findall(text)


def render_word_diff_html(before, after):
    """Render a single inline HTML view highlighting what masking removed
    (struck through, red) vs. what it inserted (highlighted, green)."""
    before_tokens = _tokenize(before)
    after_tokens = _tokenize(after)
    matcher = difflib.SequenceMatcher(None, before_tokens, after_tokens, autojunk=False)

    parts = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            parts.append(_escape("".join(before_tokens[i1:i2])))
        elif tag == "delete":
            parts.append(
                f'<span style="background:#3a1f1f;color:#ff9a9a;'
                f'text-decoration:line-through;">{_escape("".join(before_tokens[i1:i2]))}</span>'
            )
        elif tag == "insert":
            parts.append(
                f'<span style="background:#1f3a24;color:#8fe3a4;'
                f'font-weight:600;">{_escape("".join(after_tokens[j1:j2]))}</span>'
            )
        elif tag == "replace":
            parts.append(
                f'<span style="background:#3a1f1f;color:#ff9a9a;'
                f'text-decoration:line-through;">{_escape("".join(before_tokens[i1:i2]))}</span>'
            )
            parts.append(
                f'<span style="background:#1f3a24;color:#8fe3a4;'
                f'font-weight:600;">{_escape("".join(after_tokens[j1:j2]))}</span>'
            )

    html = "".join(parts).replace("\n", "<br>")
    return (
        '<div style="font-family:monospace;font-size:0.85rem;line-height:1.5;'
        'white-space:pre-wrap;padding:0.75rem;border:1px solid #333;'
        'border-radius:6px;max-height:480px;overflow-y:auto;">' + html + "</div>"
    )


def _escape(s):
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------
def approve_item(meta, edited_sanitized_text=None):
    file_name = meta.get("file_name")
    file_hash = meta.get("file_hash")

    # If this item never had sanitized text auto-generated (e.g. an
    # unreadable-image PDF the reviewer transcribed by hand), run it
    # through the same masking function the pipeline uses, then save it.
    if edited_sanitized_text is not None:
        sanitized_text, metrics = pl.mask_sensitive_data(edited_sanitized_text)
        out_path = sanitized_path_for(file_name)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(sanitized_text)
        meta["risk_metrics"] = metrics

    # Move the queue copy + its metadata JSON into the approved subfolder
    if meta.get("_pdf_exists"):
        shutil.move(meta["_pdf_path"], os.path.join(APPROVED_DIR, file_name))

    meta_out = dict(meta)
    meta_out.pop("_json_path", None)
    meta_out.pop("_json_name", None)
    meta_out.pop("_pdf_path", None)
    meta_out.pop("_pdf_exists", None)
    meta_out["status"] = "APPROVED"
    meta_out["reviewed_at"] = datetime.datetime.now().isoformat()

    new_json_path = os.path.join(APPROVED_DIR, meta["_json_name"])
    with open(new_json_path, "w", encoding="utf-8") as f:
        json.dump(meta_out, f, indent=4)
    if os.path.exists(meta["_json_path"]):
        os.remove(meta["_json_path"])

    update_manifest_decision(file_hash, "APPROVED")
    append_review_log({
        "file_name": file_name,
        "file_hash": file_hash,
        "decision": "APPROVED",
        "decided_at": meta_out["reviewed_at"],
    })


def reject_item(meta, reason=""):
    file_name = meta.get("file_name")
    file_hash = meta.get("file_hash")

    # Quarantine the sanitized output so it can't be mistaken for
    # a cleared document -- move it alongside the rejected record
    # rather than deleting it outright, for audit purposes.
    san_text, san_path = load_sanitized_text(file_name) if file_name else (None, None)
    if san_path and os.path.exists(san_path):
        shutil.move(san_path, os.path.join(REJECTED_DIR, os.path.basename(san_path)))

    if meta.get("_pdf_exists"):
        shutil.move(meta["_pdf_path"], os.path.join(REJECTED_DIR, file_name))

    meta_out = dict(meta)
    meta_out.pop("_json_path", None)
    meta_out.pop("_json_name", None)
    meta_out.pop("_pdf_path", None)
    meta_out.pop("_pdf_exists", None)
    meta_out["status"] = "REJECTED"
    meta_out["reviewed_at"] = datetime.datetime.now().isoformat()
    meta_out["rejection_reason"] = reason

    new_json_path = os.path.join(REJECTED_DIR, meta["_json_name"])
    with open(new_json_path, "w", encoding="utf-8") as f:
        json.dump(meta_out, f, indent=4)
    if os.path.exists(meta["_json_path"]):
        os.remove(meta["_json_path"])

    update_manifest_decision(file_hash, "REJECTED", reason)
    append_review_log({
        "file_name": file_name,
        "file_hash": file_hash,
        "decision": "REJECTED",
        "reason": reason,
        "decided_at": meta_out["reviewed_at"],
    })


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="Governance Triage Dashboard", layout="wide")
    st.title("🛡️ Human Review Triage Dashboard")
    st.caption(
        f"Queue: `{pl.REVIEW_DIR}`  •  Sanitized output: `{pl.SANITIZED_DIR}`  •  "
        f"High-risk threshold: {pl.HIGH_RISK_THRESHOLD} PII hits"
    )

    if "selected_json" not in st.session_state:
        st.session_state.selected_json = None

    pending = list_pending_reviews()
    summary = build_queue_summary(pending)

    with st.sidebar:
        st.header(f"Pending Review ({summary['total']})")
        st.caption("Select the next item to review.")
        st.metric("High-risk", summary["high_risk"])
        st.metric("Unreadable", summary["unreadable"])

        st.subheader("Batch intake")
        source_dir = st.text_input("Source folder", value=pl.SOURCE_DIR, key="source_dir")
        recursive_scan = st.checkbox("Include subfolders", value=False, key="recursive_scan")
        if st.button("Discover PDFs", use_container_width=True):
            st.session_state.discovered_files = discover_available_files(source_dir, recursive=recursive_scan)
            st.success(f"Found {len(st.session_state.discovered_files)} PDF(s).")

        if "discovered_files" not in st.session_state:
            st.session_state.discovered_files = discover_available_files(source_dir, recursive=recursive_scan)

        if st.session_state.discovered_files:
            selected_files = st.multiselect(
                "Select files to process",
                st.session_state.discovered_files,
                default=st.session_state.discovered_files[:1],
                key="selected_files",
            )
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Process selected", use_container_width=True):
                    result = pl.run_ingestion_pipeline(source_dir=source_dir, selected_files=selected_files)
                    st.success(f"Processed {result['processed_count']} file(s); {result['routed_to_review']} routed for review.")
                    st.session_state.discovered_files = discover_available_files(source_dir, recursive=recursive_scan)
                    st.rerun()
            with col_b:
                if st.button("Process all", use_container_width=True):
                    result = pl.run_ingestion_pipeline(source_dir=source_dir, selected_files=st.session_state.discovered_files)
                    st.success(f"Processed {result['processed_count']} file(s); {result['routed_to_review']} routed for review.")
                    st.session_state.discovered_files = discover_available_files(source_dir, recursive=recursive_scan)
                    st.rerun()

        if not pending:
            st.info("Queue is empty. Nothing awaiting review.")
            st.stop()

        query = st.text_input("Search queue", key="queue_search")
        status_filter = st.selectbox(
            "Status",
            ["All", "FLAGGED_FOR_REVIEW", "UNREADABLE_IMAGE_PDF", "APPROVED", "REJECTED"],
            key="status_filter",
        )
        risk_filter = st.selectbox("Risk", ["All", "High risk", "Low risk"], key="risk_filter")
        date_filter = st.selectbox("Date", ["All", "Last 24 hours", "Last 7 days", "Last 30 days"], key="date_filter")
        filtered_pending = filter_pending_reviews(
            pending,
            query=query,
            status_filter=status_filter,
            risk_filter=risk_filter,
            date_filter=date_filter,
        )

        if filtered_pending:
            selected_queue_items = st.multiselect(
                "Select items for bulk action",
                [meta.get("file_name", meta.get("_json_name", "unknown")) for meta in filtered_pending],
                default=[],
                key="bulk_queue_selection",
            )
            bulk_action = st.selectbox("Bulk action", ["APPROVE", "REJECT"], key="bulk_action")
            bulk_reason = st.text_input("Bulk reason", key="bulk_reason")
            if st.button("Apply bulk action", use_container_width=True):
                selected_metas = [meta for meta in filtered_pending if meta.get("file_name", meta.get("_json_name", "unknown")) in selected_queue_items]
                if selected_metas:
                    bulk_decide_items(selected_metas, bulk_action, reason=bulk_reason)
                    st.success(f"Applied {bulk_action.lower()} to {len(selected_metas)} item(s).")
                    st.rerun()
                else:
                    st.info("Select at least one item from the queue.")

        if not filtered_pending:
            st.info("No items match the current filter.")
            st.stop()

        for meta in filtered_pending:
            status = meta.get("status", "UNKNOWN")
            badge = get_status_badge(status)
            file_name = meta.get("file_name", meta.get("_json_name", "unknown"))
            label = f"{badge} {file_name}"
            if st.button(label, key=f"select_{meta['_json_name']}", use_container_width=True):
                st.session_state.selected_json = meta["_json_name"]

    selected_meta = next(
        (m for m in pending if m["_json_name"] == st.session_state.selected_json), None
    )

    if not pending:
        st.stop()

    if selected_meta is None:
        st.info("Select a document from the sidebar to begin review.")
        st.stop()

    # -----------------------------------------------------------------------
    # Detail panel for the selected item
    # -----------------------------------------------------------------------
    meta = selected_meta
    file_name = meta.get("file_name", "unknown")
    status = meta.get("status", "UNKNOWN")

    top_left, top_right = st.columns([2, 1])
    with top_left:
        st.subheader(file_name)
        st.caption(
            f"Status: **{get_status_label(status)}**  •  Ingested: {meta.get('ingested_at', 'n/a')}"
        )
    with top_right:
        st.metric("File hash", (meta.get("file_hash") or "")[:12] + "…")
        st.metric("Risk score", get_risk_score(meta) if get_risk_score(meta) is not None else "n/a")

    if not meta.get("_pdf_exists"):
        st.warning("Original file missing from queue; review is limited to available metadata and sanitized output.")

    risk_metrics = meta.get("risk_metrics", {})
    if isinstance(risk_metrics, dict) and risk_metrics:
        mcols = st.columns(min(len(risk_metrics), 6))
        for i, (k, v) in enumerate(risk_metrics.items()):
            mcols[i % len(mcols)].metric(k, v)

    st.divider()

    is_unreadable = status == "UNREADABLE_IMAGE_PDF"
    sanitized_text, _ = load_sanitized_text(file_name)

    if meta.get("_pdf_exists"):
        original_text = load_original_text(meta["_pdf_path"])
    else:
        original_text = ""

    if is_unreadable or sanitized_text is None:
        st.warning(
            "No sanitized text exists for this document. You can paste the readable text below and approve it to run through the standard masking rules."
        )
        manual_text = st.text_area(
            "Manual transcription (optional)", value="", height=220,
            placeholder="Paste or type the document text here to enable masking + approval…",
        )
        if manual_text.strip():
            preview_sanitized, _ = pl.mask_sensitive_data(manual_text)
            st.markdown("**Preview: before → after masking**")
            st.markdown(render_word_diff_html(manual_text, preview_sanitized), unsafe_allow_html=True)
        else:
            preview_sanitized = None
    else:
        st.markdown("**Before → After masking (diff view)**")
        st.markdown(render_word_diff_html(original_text, sanitized_text), unsafe_allow_html=True)

        with st.expander("View full original text"):
            st.text_area("Original", original_text, height=250, disabled=True, label_visibility="collapsed")
        with st.expander("View full sanitized text"):
            st.text_area("Sanitized", sanitized_text, height=250, disabled=True, label_visibility="collapsed")
        preview_sanitized = None

    st.divider()

    approve_col, reject_col = st.columns(2)

    with approve_col:
        st.markdown("### ✅ Approve")
        st.caption("Archives the source and finalizes the sanitized output.")
        disabled = is_unreadable and not (locals().get("manual_text") or "").strip()
        if st.button("Approve & Archive", type="primary", disabled=disabled, use_container_width=True):
            if is_unreadable:
                approve_item(meta, edited_sanitized_text=manual_text)
            else:
                approve_item(meta)
            st.session_state.selected_json = None
            st.success(f"Approved {file_name}.")
            st.rerun()

    with reject_col:
        st.markdown("### ❌ Reject")
        st.caption("Quarantines the sanitized output and archives the source as rejected.")
        reason = st.text_input("Rejection reason (optional)", key=f"reason_{meta['_json_name']}")
        if st.button("Reject", use_container_width=True):
            reject_item(meta, reason=reason)
            st.session_state.selected_json = None
            st.warning(f"Rejected {file_name}.")
            st.rerun()


if __name__ == "__main__":
    main()
