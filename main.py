from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from process_docx import fix_document
import uvicorn
import os
import json
from datetime import datetime
from pathlib import Path

app = FastAPI(title="SmartDocFixer API", version="1.0.0")

# Simple file-based user tracking (for MVP)
USAGE_FILE = "user_usage.json"

# Enable CORS for Framer frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_usage_data():
    """Load user usage data from file"""
    if Path(USAGE_FILE).exists():
        with open(USAGE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_usage_data(data):
    """Save user usage data to file"""
    with open(USAGE_FILE, 'w') as f:
        json.dump(data, f)

def get_user_usage(email):
    """Get user's current usage count for this month"""
    data = load_usage_data()
    current_month = datetime.now().strftime("%Y-%m")
    
    if email not in data:
        return 0
    
    user_data = data[email]
    if user_data.get("month") != current_month:
        return 0  # New month, reset count
    
    return user_data.get("count", 0)

def track_usage(email):
    """Track document processing for user"""
    data = load_usage_data()
    current_month = datetime.now().strftime("%Y-%m")
    
    if email not in data:
        data[email] = {"month": current_month, "count": 1, "is_pro": False}
    else:
        if data[email].get("month") != current_month:
            # New month, reset count
            data[email]["month"] = current_month
            data[email]["count"] = 1
        else:
            data[email]["count"] += 1
    
    save_usage_data(data)

def is_pro_user(email):
    """Check if user is a pro subscriber"""
    data = load_usage_data()
    return data.get(email, {}).get("is_pro", False)

@app.get("/")
async def root():
    return {"message": "SmartDocFixer API is running!"}

@app.get("/usage/{email}")
async def get_usage(email: str):
    """Get user's usage statistics"""
    usage_count = get_user_usage(email)
    is_pro = is_pro_user(email)
    
    return {
        "email": email,
        "documents_processed": usage_count,
        "remaining_free": max(0, 2 - usage_count) if not is_pro else "unlimited",
        "is_pro": is_pro,
        "limit_reached": usage_count >= 2 and not is_pro
    }

@app.post("/fix-document/")
async def upload_and_fix(
    file: UploadFile = File(...),
    email: str = Form(...)
):
    # Validate file type
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Only .docx files supported")
    
    # Validate email format (basic check)
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")
    
    # Check usage limits for free users
    if not is_pro_user(email):
        usage_count = get_user_usage(email)
        if usage_count >= 2:
            raise HTTPException(
                status_code=402, 
                detail={
                    "error": "Free limit reached", 
                    "message": "You've used your 2 free documents this month. Upgrade to Pro for unlimited processing!",
                    "upgrade_url": "https://your-website.com/upgrade"
                }
            )
    
    try:
        # Process the document
        print(f"Processing document for {email}")
        output_path = await fix_document(file)
        
        # Track usage
        track_usage(email)
        
        print(f"Document processed successfully for {email}")
        
        # Return the fixed file
        return FileResponse(
            output_path, 
            filename=f"SmartDocFixed_{file.filename}",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except Exception as e:
        print(f"Error processing document: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
