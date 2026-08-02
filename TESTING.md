# Testing Guide: Data Ingestion Governance Pipeline

This guide outlines how to run manual verification tests on the Data Ingestion Governance Pipeline. It covers configuration, starting the daemon, generating test documents, and checking expected outputs.

---

## 📋 Prerequisites & Setup

Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

Verify that **Tesseract OCR** is installed and that the executable path matches your settings in `config.json`:
- **Default Path**: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- You can verify your Tesseract installation by running:
  ```powershell
  & "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
  ```

---

## ⚙️ Testing Configuration

You can configure the behavior of the tests by modifying `config.json`:
* `high_risk_threshold`: Default is `2`. A file with PII occurrences greater than this threshold is routed to the `human_review_queue/` directory.
* `enable_spacy_ner`: Default is `true`. Set to `false` if you want to skip ML-based NER and only test regex rules.

---

## 📡 Running the Watcher Daemon

To run the pipeline in real-time, file-watching mode (rather than manual batch mode):

1. **Open a dedicated terminal tab or window** at the project root folder.
2. **Start the daemon**:
   ```bash
   python watcher.py
   ```
3. **Observe Startup Output**:
   When successfully started, you will see output similar to this:
   ```text
   ============================================================
   BACKGROUND DAEMON: Monitoring 'source_documents' for incoming PDFs.
   Press Ctrl+C to terminate the daemon safely.
   ============================================================
   ```
4. **Operation**: Keep this window open. When you drop a PDF into `source_documents/` (either manually or using the test scripts below), the watcher will automatically pick it up, run the ingestion and masking pipeline, and move the processed file out of the directory.
5. **Termination**: To stop the daemon, press `Ctrl+C` in that terminal.

---

## 🛠️ Testing Utility Scripts

We have provided two helper scripts in the `tests/` directory to generate PDF files for testing:

1. **`tests/generate_mock_pdf.py`**: Generates a standard text-based PDF containing the text you provide.
2. **`tests/generate_scanned_pdf.py`**: Generates an image-only (scanned) PDF with text rendered inside a raster image. This is used to test the **OCR Fallback** pathway.

---

## 🏃 Test Scenarios

### Scenario 0: Dashboard Batch Intake (Manual UI Flow)
This tests the new folder-based batch processing flow from the Streamlit dashboard.

1. **Start the Dashboard**:
   ```bash
   streamlit run dashboard.py
   ```
2. **Open the Sidebar**:
   In the left sidebar, locate the "Batch intake" section.
3. **Pick a Source Folder**:
   Enter a folder such as `source_documents` or another folder containing one or more `.pdf` files.
4. **Discover Files**:
   Click **Discover PDFs**. The app should list the PDFs it found in the selected folder.
5. **Test Selected Processing**:
   Use the multiselect control to choose one or more PDFs and click **Process selected**.
6. **Verify Outcomes**:
   * The pipeline should process each selected file and print progress in the terminal.
   * Each processed file should be moved to `archived_sources/` after processing.
   * Sanitized output should be written to `sanitized_output/`.
   * If a file is flagged as high risk, a review metadata file should be created in `human_review_queue/`.
7. **Test Recursive Discovery**:
   Enable **Include subfolders**, click **Discover PDFs** again, and confirm nested PDFs appear with their relative paths (for example `subfolder/example.pdf`).
8. **Test Process All**:
   After discovery, click **Process all**. The app should process every discovered file without requiring manual selection.
9. **Review the Queue**:
   After processing, refresh the dashboard and confirm the newly created review items appear in the pending review list.

### Scenario 0b: Queue Filters and Bulk Review Actions
This validates the new review workflow controls for handling larger queues.

1. **Open the Sidebar Queue Controls**:
   In the dashboard sidebar, scroll to the queue controls beneath the pending review list.
2. **Filter by Status**:
   Choose a status such as `FLAGGED_FOR_REVIEW` or `UNREADABLE_IMAGE_PDF` and verify the queue list changes to only those items.
3. **Filter by Risk**:
   Switch the risk filter to `High risk` or `Low risk` and confirm the visible items change accordingly.
4. **Filter by Date**:
   Choose `Last 7 days` or `Last 30 days` and verify the queue updates based on the ingestion timestamp.
5. **Apply a Bulk Action**:
   Select one or more queue items in the multiselect and choose `REJECT` or `APPROVE` from the bulk action dropdown.
6. **Verify Outcomes**:
   * The selected items should be moved into the approved or rejected review folders.
   * The queue should refresh and remove the processed items from the pending list.
   * A review decision log entry should be appended for each action.

---

### Scenario 1: Low-Risk Document Ingestion
This tests standard ingestion, redaction, and archiving for a low-risk document (total PII <= `high_risk_threshold`).

1. **Generate the Document**:
   Create a document containing 1 email address (which is below the threshold of 2):
   ```bash
   python tests/generate_mock_pdf.py source_documents/low_risk.pdf "This is a low-risk corporate memo. Contact john.doe@example.com for info."
   ```
2. **Run the Pipeline**:
   ```bash
   python pipeline.py
   ```
3. **Verify Outcomes**:
   * Check that `source_documents/low_risk.pdf` was moved to `archived_sources/low_risk.pdf`.
   * Check that a redacted text file is in `sanitized_output/low_risk_sanitized.txt`. It should contain:
     `This is a low-risk corporate memo. Contact [REDACTED_EMAIL] for info.`
   * View `ingestion_manifest.json` and verify `low_risk.pdf` has `routed_to_review: false`.

---

### Scenario 2: High-Risk Document Routing
This tests the threshold-based triage guardrail. Documents containing more PII instances than `high_risk_threshold` must be routed to `human_review_queue/`.

1. **Generate the Document**:
   Create a document containing 3 PII entities (email, phone, and SSN, exceeding the threshold of 2):
   ```bash
   python tests/generate_mock_pdf.py source_documents/high_risk.pdf "CONFIDENTIAL: Contact CEO at ceo@company.com or 212-555-0199. SSN: 987-65-4321."
   ```
2. **Run the Pipeline**:
   ```bash
   python pipeline.py
   ```
3. **Verify Outcomes**:
   * Verify the original file was moved to `archived_sources/high_risk.pdf`.
   * Verify that a copy of `high_risk.pdf` is in `human_review_queue/high_risk.pdf`.
   * Verify that a metadata file `human_review_queue/high_risk_review.json` was generated describing the risk metrics.
   * Verify that `sanitized_output/high_risk_sanitized.txt` contains the fully redacted text.

---

### Scenario 3: Scanned PDF & OCR Fallback
This tests the OCR pipeline for scanned/image-only PDFs which do not contain an embedded text layer.

1. **Generate the Scanned Document**:
   Create an image-only PDF:
   ```bash
   python tests/generate_scanned_pdf.py source_documents/scanned_pii.pdf "SCANNED MEMO\nEmail: ocr_test@example.com\nPhone: 111-222-3333"
   ```
2. **Run the Pipeline**:
   ```bash
   python pipeline.py
   ```
3. **Verify Outcomes**:
   * Verify that the console outputs: `[RISK WARNING] File contains 0 characters of text. Invoking OCR fallback...`
   * Check that Tesseract successfully extracted the text from the image.
   * Verify that the original is archived in `archived_sources/scanned_pii.pdf`.
   * Verify that the sanitized output in `sanitized_output/scanned_pii_sanitized.txt` has redacted the email and phone numbers.
   * Verify the manifest records details for `scanned_pii.pdf`.

---

### Scenario 4: Background File-Watcher Daemon
This tests the real-time background file ingestion.

1. **Start the Watcher**:
   ```bash
   python watcher.py
   ```
   Keep the terminal running.
2. **Create a Test PDF**:
   Open a separate command prompt or terminal and run one of the generation commands:
   ```bash
   python tests/generate_mock_pdf.py source_documents/realtime_test.pdf "Please email contact@company.org."
   ```
3. **Verify Daemon Ingestion**:
   * Observe the watcher's terminal. It should immediately detect `realtime_test.pdf`, wait 1.5 seconds, and automatically run the ingestion pipeline.
   * Verify that the file is processed and archived instantly.
   * Terminate the watcher daemon in the terminal by pressing `Ctrl+C`.

---

## ✅ Manual Validation Checklist
Use this checklist after running any of the scenarios above:

- [ ] The dashboard loads successfully with Streamlit.
- [ ] The sidebar shows the batch intake controls.
- [ ] Discovering PDFs lists the expected files from the selected folder.
- [ ] Selecting and processing files creates sanitized output.
- [ ] High-risk files are routed to `human_review_queue/`.
- [ ] Processed files are archived to `archived_sources/`.
- [ ] The review queue reflects the newly created review records.
