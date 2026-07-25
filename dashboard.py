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
st.set_page_config(page_title="Governance Triage Dashboard", layout="wide")
st.title("🛡️ Human Review Triage Dashboard")
st.caption(
    f"Queue: `{pl.REVIEW_DIR}`  •  Sanitized output: `{pl.SANITIZED_DIR}`  •  "
    f"High-risk threshold: {pl.HIGH_RISK_THRESHOLD} PII hits"
)

if "selected_json" not in st.session_state:
    st.session_state.selected_json = None

pending = list_pending_reviews()

with st.sidebar:
    st.header(f"Pending Review ({len(pending)})")
    if not pending:
        st.info("Queue is empty. Nothing awaiting review.")
    for meta in pending:
        status = meta.get("status", "UNKNOWN")
        badge = "🔴" if status == "UNREADABLE_IMAGE_PDF" else "🟠"
        label = f"{badge} {meta.get('file_name', meta['_json_name'])}"
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

# ---------------------------------------------------------------------------
# Detail panel for the selected item
# ---------------------------------------------------------------------------
meta = selected_meta
file_name = meta.get("file_name", "unknown")
status = meta.get("status", "UNKNOWN")

col_a, col_b, col_c = st.columns([2, 1, 1])
with col_a:
    st.subheader(file_name)
    st.caption(f"Status: **{status}**  •  Ingested: {meta.get('ingested_at', 'n/a')}")
with col_b:
    st.metric("File hash", (meta.get("file_hash") or "")[:12] + "…")
with col_c:
    if not meta.get("_pdf_exists"):
        st.error("Original file missing from queue")

risk_metrics = meta.get("risk_metrics", {})
if isinstance(risk_metrics, dict) and risk_metrics:
    mcols = st.columns(min(len(risk_metrics), 6))
    for i, (k, v) in enumerate(risk_metrics.items()):
        mcols[i % len(mcols)].metric(k, v)

st.divider()

is_unreadable = status == "UNREADABLE_IMAGE_PDF"
sanitized_text, san_path = load_sanitized_text(file_name)

if meta.get("_pdf_exists"):
    original_text = load_original_text(meta["_pdf_path"])
else:
    original_text = ""

if is_unreadable or sanitized_text is None:
    st.warning(
        "No sanitized text exists for this document (extraction/OCR returned "
        "nothing). You can transcribe or paste the readable text below, and "
        "Approve will run it through the standard masking rules before saving."
    )
    manual_text = st.text_area(
        "Manual transcription (optional)", value="", height=220,
        placeholder="Paste or type the document text here to enable masking + approval…",
    )
    if manual_text.strip():
        preview_sanitized, preview_metrics = pl.mask_sensitive_data(manual_text)
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
