from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import openai
import os
import tempfile
from dotenv import load_dotenv

load_dotenv()

async def fix_document(file):
    """Main function to fix document grammar, clarity, and formatting"""
    
    # Read uploaded file
    contents = await file.read()
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    
    # Load document
    doc = Document(tmp_path)
    
    # Fix each paragraph with AI
    for para in doc.paragraphs:
        if para.text.strip():  # Only process non-empty paragraphs
            original_text = para.text
            print(f"Original: {original_text}")  # Debug log
            
            # Get AI-improved text
            improved_text = await improve_text_with_ai(original_text)
            print(f"Improved: {improved_text}")  # Debug log
            
            # Clear the paragraph and add improved text
            para.clear()
            run = para.add_run(improved_text)
            
            # Apply consistent formatting
            apply_formatting_to_run(run)
    
    # Apply document-wide formatting
    format_document(doc)
    
    # Save fixed document
    output_path = tmp_path.replace(".docx", "_fixed.docx")
    doc.save(output_path)
    
    # Clean up original temp file
    os.unlink(tmp_path)
    
    return output_path

async def improve_text_with_ai(text):
    """Use OpenAI to improve grammar and clarity"""
    
    # Initialize client here to avoid import issues
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"""You are a professional document editor. Improve this text by:
1. Fixing grammar and spelling errors
2. Improving clarity and readability  
3. Making it more professional
4. Keeping the original meaning

Original text: {text}

Return ONLY the improved text, nothing else."""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional document editor. Return only the improved text."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        improved = response.choices[0].message.content.strip()
        
        # Remove any quotes or extra formatting that AI might add
        if improved.startswith('"') and improved.endswith('"'):
            improved = improved[1:-1]
        
        return improved
    
    except Exception as e:
        print(f"AI processing error: {e}")
        return text  # Return original text if AI fails

def apply_formatting_to_run(run):
    """Apply consistent formatting to a text run"""
    run.font.name = 'Calibri'
    run.font.size = Pt(11)  # Using Pt instead of Inches for font size

def format_document(doc):
    """Apply document-wide formatting improvements"""
    
    # Set margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
    
    # Format potential headings
    for para in doc.paragraphs:
        text = para.text.strip()
        # Simple heuristic for headings: short lines without periods
        if text and len(text) < 60 and not text.endswith('.') and not text.endswith(','):
            para.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for run in para.runs:
                run.bold = True
                run.font.size = Pt(14)  # 14pt for headings
