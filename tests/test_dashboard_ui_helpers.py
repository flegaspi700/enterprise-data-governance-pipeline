import importlib.util
from pathlib import Path
import unittest


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


if __name__ == "__main__":
    unittest.main()
