import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "tests" / "run_dashboard_demo.py"

spec = importlib.util.spec_from_file_location("run_dashboard_demo", MODULE_PATH)
run_dashboard_demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_dashboard_demo)


class DashboardDemoTests(unittest.TestCase):
    def test_create_demo_pdf_writes_a_pdf_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "demo.pdf"
            created_path = run_dashboard_demo.create_demo_pdf(output_path=output_path)

            self.assertEqual(created_path, output_path)
            self.assertTrue(output_path.exists())
            self.assertGreater(output_path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
