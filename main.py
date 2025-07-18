from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from process_docx import fix_document
import uvicorn
import os
import tempfile

app = FastAPI(title="SmartDocFixer API", version="1.0.0")

# Enable CORS for Framer frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "SmartDocFixer API is running!"}

@app.post("/fix-document/")
async def upload_and_fix(file: UploadFile = File(...)):
    # Validate file type
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Only .docx files supported")
    
    try:
        # Process the document
        output_path = await fix_document(file)
        
        # Return the fixed file
        return FileResponse(
            output_path, 
            filename=f"Fixed_{file.filename}",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)