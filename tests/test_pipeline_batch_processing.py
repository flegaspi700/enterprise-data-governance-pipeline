import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "pipeline.py"

spec = importlib.util.spec_from_file_location("pipeline_module", MODULE_PATH)
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


class PipelineBatchProcessingTests(unittest.TestCase):
    def test_discover_pdf_files_from_source_folder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "batch_a").mkdir()
            (root / "batch_b").mkdir()
            (root / "batch_a" / "one.pdf").write_text("dummy", encoding="utf-8")
            (root / "batch_a" / "two.txt").write_text("ignore", encoding="utf-8")
            (root / "batch_b" / "three.pdf").write_text("dummy", encoding="utf-8")

            discovered = pipeline.discover_pdf_files(str(root), recursive=True)

            self.assertEqual(discovered, [
                str(root / "batch_a" / "one.pdf"),
                str(root / "batch_b" / "three.pdf"),
            ])

    def test_run_ingestion_pipeline_processes_selected_files_from_a_folder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source_dir = tmp / "source"
            sanitized_dir = tmp / "sanitized"
            review_dir = tmp / "review"
            archive_dir = tmp / "archive"
            manifest_file = tmp / "manifest.json"
            source_dir.mkdir()
            sanitized_dir.mkdir()
            review_dir.mkdir()
            archive_dir.mkdir()

            first_pdf = source_dir / "alpha.pdf"
            second_pdf = source_dir / "beta.pdf"
            first_pdf.write_bytes(b"first dummy content")
            second_pdf.write_bytes(b"second dummy content")

            with mock.patch.object(pipeline, "SOURCE_DIR", str(source_dir)), \
                 mock.patch.object(pipeline, "SANITIZED_DIR", str(sanitized_dir)), \
                 mock.patch.object(pipeline, "REVIEW_DIR", str(review_dir)), \
                 mock.patch.object(pipeline, "ARCHIVE_DIR", str(archive_dir)), \
                 mock.patch.object(pipeline, "MANIFEST_FILE", str(manifest_file)), \
                 mock.patch.object(pipeline, "extract_text_from_pdf", return_value="sample text"), \
                 mock.patch.object(pipeline, "mask_sensitive_data", return_value=("sanitized text", {"emails": 0, "phones": 0, "ssns": 0, "total": 0})), \
                 mock.patch.object(pipeline, "load_spacy_engine", return_value=None):
                summary = pipeline.run_ingestion_pipeline(source_dir=str(source_dir), selected_files=["alpha.pdf", "beta.pdf"])

            self.assertEqual(summary["processed_count"], 2)
            self.assertEqual(summary["routed_to_review"], 0)
            self.assertTrue((sanitized_dir / "alpha_sanitized.txt").exists())
            self.assertTrue((sanitized_dir / "beta_sanitized.txt").exists())
            self.assertFalse(first_pdf.exists())
            self.assertFalse(second_pdf.exists())
            self.assertTrue((archive_dir / "alpha.pdf").exists())
            self.assertTrue((archive_dir / "beta.pdf").exists())

    def test_mask_sensitive_data_redacts_configured_pii_rules(self):
        text = "Email this to test.user@example.com and call 415-555-1234. SSN is 123-45-6789."
        with mock.patch.object(pipeline, "load_spacy_engine", return_value=None):
            sanitized, metrics = pipeline.mask_sensitive_data(text)

        self.assertIn("[REDACTED_EMAIL]", sanitized)
        self.assertIn("[REDACTED_PHONE]", sanitized)
        self.assertIn("[REDACTED_TAX_ID]", sanitized)
        self.assertEqual(metrics["emails"], 1)
        self.assertEqual(metrics["phones"], 1)
        self.assertEqual(metrics["ssns"], 1)
        self.assertEqual(metrics["total"], 3)


if __name__ == "__main__":
    unittest.main()
