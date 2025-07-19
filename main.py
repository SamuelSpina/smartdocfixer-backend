from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from process_docx import fix_document
import uvicorn
import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path

app = FastAPI(title="SmartDocFixer API", version="1.0.0")

# File-based storage for MVP
USAGE_FILE = "user_usage.json"
USERS_FILE = "users.json"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

def load_users():
    """Load registered users"""
    if Path(USERS_FILE).exists():
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(data):
    """Save users data"""
    with open(USERS_FILE, 'w') as f:
        json.dump(data, f)

def hash_password(password: str) -> str:
    """Hash password for storage"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_client_ip(request: Request) -> str:
    """Get client IP address"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host

def get_user_usage(email: str, ip_address: str = None):
    """Get user's current usage count for this month"""
    data = load_usage_data()
    current_month = datetime.now().strftime("%Y-%m")
    
    # Create usage key (email + IP to prevent abuse)
    usage_key = f"{email}:{ip_address}" if ip_address else email
    
    if usage_key not in data:
        return 0
    
    user_data = data[usage_key]
    if user_data.get("month") != current_month:
        return 0  # New month, reset count
    
    return user_data.get("count", 0)

def track_usage(email: str, ip_address: str = None):
    """Track document processing for user"""
    data = load_usage_data()
    current_month = datetime.now().strftime("%Y-%m")
    
    usage_key = f"{email}:{ip_address}" if ip_address else email
    
    if usage_key not in data:
        data[usage_key] = {"month": current_month, "count": 1, "email": email}
    else:
        if data[usage_key].get("month") != current_month:
            data[usage_key]["month"] = current_month
            data[usage_key]["count"] = 1
        else:
            data[usage_key]["count"] += 1
    
    save_usage_data(data)

def is_registered_user(email: str) -> bool:
    """Check if user is registered"""
    users = load_users()
    return email in users

def is_pro_user(email: str) -> bool:
    """Check if user has pro subscription"""
    users = load_users()
    user_data = users.get(email, {})
    
    # Check if pro subscription is still valid
    if user_data.get("is_pro", False):
        pro_until = user_data.get("pro_until")
        if pro_until:
            pro_date = datetime.fromisoformat(pro_until)
            return datetime.now() < pro_date
    
    return False

def get_usage_limit(email: str) -> int:
    """Get usage limit based on user status"""
    if is_pro_user(email):
        return float('inf')  # Unlimited
    elif is_registered_user(email):
        return 3  # 3 total for registered users
    else:
        return 1  # 1 for email-only users

@app.get("/")
async def root():
    return {"message": "SmartDocFixer API is running!"}

@app.post("/signup/")
async def signup(
    email: str = Form(...),
    password: str = Form(...)
):
    """Register new user"""
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")
    
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    users = load_users()
    
    if email in users:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Save new user
    users[email] = {
        "email": email,
        "password_hash": hash_password(password),
        "registered_date": datetime.now().isoformat(),
        "is_pro": False,
        "pro_until": None
    }
    
    save_users(users)
    
    return {
        "message": "Registration successful! You now have 3 free documents total.",
        "user": {
            "email": email,
            "registered": True,
            "is_pro": False
        }
    }

@app.post("/login/")
async def login(
    email: str = Form(...),
    password: str = Form(...)
):
    """User login"""
    users = load_users()
    
    if email not in users:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    user = users[email]
    if user["password_hash"] != hash_password(password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    return {
        "message": "Login successful",
        "user": {
            "email": email,
            "registered": True,
            "is_pro": is_pro_user(email)
        }
    }

@app.post("/upgrade-to-pro/")
async def upgrade_to_pro(email: str = Form(...)):
    """Upgrade user to pro (placeholder for Stripe integration)"""
    users = load_users()
    
    if email not in users:
        raise HTTPException(status_code=404, detail="User not found. Please register first.")
    
    # Set pro status for 1 month (in production, this would be handled by Stripe webhooks)
    pro_until = datetime.now() + timedelta(days=30)
    users[email]["is_pro"] = True
    users[email]["pro_until"] = pro_until.isoformat()
    
    save_users(users)
    
    return {
        "message": f"User {email} upgraded to Pro!",
        "pro_until": pro_until.isoformat()
    }

@app.get("/usage/{email}")
async def get_usage(email: str, request: Request):
    """Get user's usage statistics"""
    ip_address = get_client_ip(request)
    usage_count = get_user_usage(email, ip_address)
    usage_limit = get_usage_limit(email)
    is_registered = is_registered_user(email)
    is_pro = is_pro_user(email)
    
    remaining = "unlimited" if is_pro else max(0, usage_limit - usage_count)
    
    return {
        "email": email,
        "documents_processed": usage_count,
        "usage_limit": usage_limit if usage_limit != float('inf') else "unlimited",
        "remaining_free": remaining,
        "is_registered": is_registered,
        "is_pro": is_pro,
        "limit_reached": usage_count >= usage_limit and not is_pro,
        "needs_signup": not is_registered and usage_count >= 1
    }

@app.post("/fix-document/")
async def upload_and_fix(
    file: UploadFile = File(...),
    email: str = Form(...),
    request: Request
):
    # Validate file type
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Only .docx files supported")
    
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")
    
    ip_address = get_client_ip(request)
    usage_count = get_user_usage(email, ip_address)
    usage_limit = get_usage_limit(email)
    is_registered = is_registered_user(email)
    is_pro = is_pro_user(email)
    
    # Check usage limits
    if not is_pro:
        if usage_count >= usage_limit:
            if not is_registered:
                # First time user exceeded 1 document
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Signup required",
                        "message": "Sign up for free to get 2 more documents!",
                        "action": "signup"
                    }
                )
            else:
                # Registered user exceeded 3 documents
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": "Upgrade required",
                        "message": "Upgrade to Pro for unlimited document processing!",
                        "action": "upgrade"
                    }
                )
    
    try:
        print(f"Processing document for {email} (IP: {ip_address})")
        output_path = await fix_document(file)
        
        # Track usage
        track_usage(email, ip_address)
        
        print(f"Document processed successfully for {email}")
        
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