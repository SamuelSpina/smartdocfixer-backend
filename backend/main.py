# main.py
import os
import uvicorn
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext

# Import our new modules
from database import SessionLocal, engine, Base
import models
import schemas
from process_docx import fix_document

# Create all database tables on startup
Base.metadata.create_all(bind=engine)

# --- Configuration & Setup ---
app = FastAPI(title="SmartDocFixer API", version="2.0.0")

# Allow all origins for simplicity during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Security & Authentication ---
# Secret key to create and sign tokens.
# In production, load this from an environment variable and make it much more complex!
SECRET_KEY = os.getenv("SECRET_KEY", "a_very_secret_key_for_development")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # Token expires in 7 days

# Password Hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- Dependency ---
def get_db():
    """Dependency to get a DB session for each request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Utility Functions ---
def verify_password(plain_password, hashed_password):
    """Verify a plain password against a hashed one."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Hash a password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create a new JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    """Decode token to get the current user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user

def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else request.client.host


# --- API Endpoints ---
@app.get("/")
async def root():
    return {"message": "Welcome to SmartDocFixer API v2.0!"}

@app.post("/signup", response_model=schemas.User)
async def signup(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """Register a new user."""
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    db_user = db.query(models.User).filter(models.User.email == email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(password)
    new_user = models.User(email=email, password_hash=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=schemas.Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
    """User login to get an access token."""
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: Annotated[models.User, Depends(get_current_user)]):
    """Get information about the currently logged-in user."""
    return current_user

@app.post("/fix-document/")
async def upload_and_fix(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    # The token is now the primary way to identify a user
    current_user: models.User = Depends(get_current_user)
):
    """Upload, validate, and fix a document."""
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Only .docx files are supported.")

    # Check usage limits
    usage_count = len(current_user.processed_files)
    limit_reached = (not current_user.is_pro) and (usage_count >= 3)
    
    if limit_reached:
        raise HTTPException(
            status_code=402, # 402 Payment Required is fitting
            detail={
                "error": "Upgrade required",
                "message": "You have reached your limit of 3 free documents. Upgrade to Pro for unlimited processing!",
                "action": "upgrade"
            }
        )
    
    try:
        ip_address = get_client_ip(request)
        print(f"Processing document for {current_user.email} (IP: {ip_address})")
        output_path = await fix_document(file)

        # Track usage in the database
        new_usage = models.Usage(user_id=current_user.id, file_name=file.filename, ip_address=ip_address)
        db.add(new_usage)
        db.commit()
        
        print(f"Document processed successfully for {current_user.email}")
        return FileResponse(
            output_path,
            filename=f"SmartDocFixed_{file.filename}",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except Exception as e:
        print(f"Error processing document: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while processing your document: {str(e)}")


@app.post("/upgrade-to-pro/")
async def upgrade_to_pro(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """(Placeholder) Upgrade the current user to Pro."""
    # In a real app, this endpoint would be a webhook called by Stripe after a successful payment.
    current_user.is_pro = True
    # For a subscription, you'd set a 'pro_until' date.
    # current_user.pro_until = datetime.now(timezone.utc) + timedelta(days=31)
    db.commit()
    return {"message": f"User {current_user.email} has been upgraded to Pro!"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)