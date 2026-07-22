from PIL import Image, ImageDraw
import fitz
import sys
import os

def create_scanned_pdf(output_path, text_content):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    # Create image with text
    img = Image.new("RGB", (1000, 300), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    # We write multiple lines
    lines = text_content.split("\\n")
    y = 20
    for line in lines:
        d.text((20, y), line, fill=(0, 0, 0))
        y += 30
        
    temp_img_path = "temp_scanned.png"
    img.save(temp_img_path)
    
    # Create PDF from image using PyMuPDF
    doc = fitz.open()
    img_doc = fitz.open(temp_img_path)
    pdf_bytes = img_doc.convert_to_pdf()
    img_doc.close()
    
    scanned_doc = fitz.open("pdf", pdf_bytes)
    doc.insert_pdf(scanned_doc)
    doc.save(output_path)
    doc.close()
    
    # Clean up temp image
    if os.path.exists(temp_img_path):
        os.remove(temp_img_path)
        
    print(f"Created scanned PDF at {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_scanned_pdf.py <output_path> <text_content>")
        print("Example: python generate_scanned_pdf.py ../source_documents/scanned_test.pdf \"Scanned content here\"")
        sys.exit(1)
        
    out_path = sys.argv[1]
    content = sys.argv[2]
    create_scanned_pdf(out_path, content)
