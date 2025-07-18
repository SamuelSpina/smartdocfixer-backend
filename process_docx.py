from docx import Document
from docx.shared import Inches
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
            # Get AI-improved text
            improved_text = await improve_text_with_ai(para.text)
            
            # Replace paragraph text
            para.text = improved_text
            
            # Apply consistent formatting
            apply_formatting(para)
    
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
    
    prompt = f"""
    You are a professional document editor. Improve this text by:
    1. Fixing grammar and spelling errors
    2. Improving clarity and readability
    3. Making it more professional
    4. Keeping the original meaning and tone
    
    Original text: {text}
    
    Return only the improved text, nothing else.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using mini version for faster/cheaper processing
            messages=[
                {"role": "system", "content": "You are a professional document editor."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"AI processing error: {e}")
        return text  # Return original text if AI fails

def apply_formatting(paragraph):
    """Apply consistent formatting to paragraph"""
    
    # Set font and size
    for run in paragraph.runs:
        run.font.name = 'Calibri'
        run.font.size = Inches(0.12)  # 11pt
    
    # Set paragraph spacing
    paragraph.space_after = Inches(0.1)
    paragraph.space_before = Inches(0.05)

def format_document(doc):
    """Apply document-wide formatting improvements"""
    
    # Set margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
    
    # Identify and format headings (simple heuristic)
    for para in doc.paragraphs:
        text = para.text.strip()
        if text and len(text) < 60 and not text.endswith('.'):
            # Likely a heading
            para.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for run in para.runs:
                run.bold = True
                run.font.size = Inches(0.14)  # 14pt for headings
