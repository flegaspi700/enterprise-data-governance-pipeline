import fitz
import sys
import os

def create_mock_pdf(output_path, text_content):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc = fitz.open()
    page = doc.new_page()
    # Insert text on page
    page.insert_text((50, 50), text_content)
    doc.save(output_path)
    doc.close()
    print(f"Created mock PDF at {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_mock_pdf.py <output_path> <text_content>")
        print("Example: python generate_mock_pdf.py ../source_documents/test.pdf \"Sample PII text\"")
        sys.exit(1)
    
    out_path = sys.argv[1]
    content = sys.argv[2]
    create_mock_pdf(out_path, content)
