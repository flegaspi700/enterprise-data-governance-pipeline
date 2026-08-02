import importlib.util
import datetime
import json
import tempfile
from pathlib import Path
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "dashboard.py"

spec = importlib.util.spec_from_file_location("dashboard_module", MODULE_PATH)
dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard)


class DashboardUIHelpersTests(unittest.TestCase):
    def test_status_badge_and_label_for_unreadable_items(self):
        self.assertEqual(dashboard.get_status_badge("UNREADABLE_IMAGE_PDF"), "⚠️")
        self.assertEqual(dashboard.get_status_label("UNREADABLE_IMAGE_PDF"), "Unreadable image PDF")

    def test_queue_summary_counts_risk_and_status(self):
        pending = [
            {"status": "UNREADABLE_IMAGE_PDF", "file_name": "a.pdf", "risk_metrics": {"PII hits": 7}},
            {"status": "PENDING_REVIEW", "file_name": "b.pdf", "risk_metrics": {"PII hits": 2}},
            {"status": "PENDING_REVIEW", "file_name": "c.pdf", "risk_metrics": {"PII hits": 9}},
        ]

        summary = dashboard.build_queue_summary(pending)

        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["high_risk"], 3)
        self.assertEqual(summary["unreadable"], 1)

    def test_discover_available_files_supports_recursive_paths(self):
        with mock.patch.object(dashboard.pl, "discover_pdf_files", return_value=[
            "/tmp/source/nested/alpha.pdf",
            "/tmp/source/beta.pdf",
        ]):
            discovered = dashboard.discover_available_files("/tmp/source", recursive=True)

        self.assertEqual(discovered, ["nested/alpha.pdf", "beta.pdf"])

    def test_filter_pending_reviews_applies_query_status_risk_and_date_filters(self):
        now = datetime.datetime.now()
        pending = [
            {
                "file_name": "alpha.pdf",
                "status": "FLAGGED_FOR_REVIEW",
                "ingested_at": now.isoformat(),
                "risk_metrics": {"PII hits": 3},
            },
            {
                "file_name": "beta.pdf",
                "status": "UNREADABLE_IMAGE_PDF",
                "ingested_at": (now - datetime.timedelta(days=10)).isoformat(),
                "risk_metrics": {"PII hits": 1},
            },
            {
                "file_name": "gamma.pdf",
                "status": "FLAGGED_FOR_REVIEW",
                "ingested_at": (now - datetime.timedelta(days=2)).isoformat(),
                "risk_metrics": {"PII hits": 8},
            },
        ]

        filtered = dashboard.filter_pending_reviews(
            pending,
            query="alpha",
            status_filter="FLAGGED_FOR_REVIEW",
            risk_filter="High risk",
            date_filter="Last 7 days",
        )

        self.assertEqual([item["file_name"] for item in filtered], ["alpha.pdf"])

    def test_bulk_decide_items_dispatches_to_bulk_handlers(self):
        calls = []

        def fake_approve(meta):
            calls.append(("approve", meta["file_name"]))

        def fake_reject(meta, reason=""):
            calls.append(("reject", meta["file_name"], reason))

        with mock.patch.object(dashboard, "approve_item", side_effect=fake_approve), \
             mock.patch.object(dashboard, "reject_item", side_effect=fake_reject):
            dashboard.bulk_decide_items(
                [{"file_name": "alpha.pdf"}, {"file_name": "beta.pdf"}],
                "REJECT",
                reason="needs review",
            )

        self.assertEqual(calls, [
            ("reject", "alpha.pdf", "needs review"),
            ("reject", "beta.pdf", "needs review"),
        ])

    def test_build_dashboard_summary_counts_pending_reviewed_archived_and_sanitized(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            review_dir = base / "review"
            archive_dir = base / "archive"
            sanitized_dir = base / "sanitized"
            review_dir.mkdir()
            archive_dir.mkdir()
            sanitized_dir.mkdir()
            (review_dir / "review_decisions.json").write_text(json.dumps([{"decision": "APPROVED"}]), encoding="utf-8")
            (archive_dir / "one.pdf").write_text("archived", encoding="utf-8")
            (sanitized_dir / "two_sanitized.txt").write_text("sanitized", encoding="utf-8")

            summary = dashboard.build_dashboard_summary(
                [{"file_name": "pending.pdf"}],
                review_dir=str(review_dir),
                archive_dir=str(archive_dir),
                sanitized_dir=str(sanitized_dir),
            )

        self.assertEqual(summary["pending"], 1)
        self.assertEqual(summary["reviewed"], 1)
        self.assertEqual(summary["archived"], 1)
        self.assertEqual(summary["sanitized"], 1)


if __name__ == "__main__":
    unittest.main()
