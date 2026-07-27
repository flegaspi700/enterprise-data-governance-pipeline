import os
import shutil
import subprocess
import sys
from pathlib import Path

from generate_mock_pdf import create_mock_pdf

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "source_documents"
PIPELINE = ROOT / "pipeline.py"


def create_demo_pdf(output_path=None):
    if output_path is None:
        output_path = SOURCE_DIR / "dashboard_demo.pdf"
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample_text = (
        "CONFIDENTIAL: Contact CEO at ceo@company.com or 212-555-0199. "
        "SSN: 987-65-4321."
    )
    create_mock_pdf(str(output_path), sample_text)
    return output_path


def run_demo_flow():
    pdf_path = create_demo_pdf()
    result = subprocess.run(
        [sys.executable, str(PIPELINE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        return result.returncode
    return 0


if __name__ == "__main__":
    run_demo_flow()
