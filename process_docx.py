# process_docx.py

import os
import tempfile
from dotenv import load_dotenv
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import openai

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")  # ← set your key here

async def fix_document(file):
    """Fix grammar, clarity & formatting in a .docx upload."""
    # 1) Read and dump to temp file
    contents = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    # 2) Load doc
    doc = Document(tmp_path)
    print(f"Loaded {len(doc.paragraphs)} paragraphs…")

    # 3) AI system prompt
    system_msg = """
You are SmartDocFixer AI. Improve grammar, clarity, and professional formatting
while preserving headings, lists, tables, and overall structure. Do not remove
bullets or tables—only correct and polish.
"""

    # 4) Iterate paragraphs
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if not text:
            continue

        # Call OpenAI
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user",   "content": f"Fix this paragraph:\n\n{text}"}
                ],
                max_tokens=800,
                temperature=0.2,
            )
            improved = resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI error on para {i}:", e)
            improved = text  # fallback

        # 5) Replace paragraph text (this clears old runs)
        para.text = improved

        # 6) Re‑apply run formatting
        for run in para.runs:
            run.font.name = "Calibri"
            run.font.size = Pt(11)

    # 7) Global document formatting
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # 8) Save to new file
    out_path = tmp_path.replace(".docx", "_fixed.docx")
    doc.save(out_path)
    os.unlink(tmp_path)
    print("Saved fixed document to:", out_path)
    return out_path

