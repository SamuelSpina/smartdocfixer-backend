from docx import Document
from docx.shared import Inches, Pt
import tempfile
import os

async def fix_document(file):
    """Main function to fix document - SIMPLIFIED DEBUG VERSION"""
    
    # Read uploaded file
    contents = await file.read()
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    
    # Load document
    doc = Document(tmp_path)
    
    print(f"Processing document with {len(doc.paragraphs)} paragraphs")
    
    # Simple text replacement WITHOUT AI (for testing)
    for i, para in enumerate(doc.paragraphs):
        if para.text.strip():
            original_text = para.text
            print(f"Paragraph {i}: {original_text}")
            
            # Simple improvement - just add "IMPROVED: " prefix
            improved_text = f"IMPROVED: {original_text}"
            
            # Clear and replace
            para.clear()
            run = para.add_run(improved_text)
            run.font.name = 'Calibri'
            run.font.size = Pt(11)
    
    # Save fixed document
    output_path = tmp_path.replace(".docx", "_fixed.docx")
    doc.save(output_path)
    
    print(f"Saved to: {output_path}")
    
    # Clean up original temp file
    os.unlink(tmp_path)
    
    return output_path
