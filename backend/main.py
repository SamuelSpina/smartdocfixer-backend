import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
import stripe

# Import our modules
from database import SessionLocal, engine, Base
import models
import schemas
from process_docx import fix_document

# Create all database tables on startup if they don't exist
# Note: For schema changes (like adding a column), use Alembic migrations.
Base.metadata.create_all(bind=engine)

# --- Configuration & Setup ---
app = FastAPI(title="SmartDocFixer API", version="2.0.0")

# Load environment variables
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PRO_PRICE_ID = os.getenv("STRIPE_PRO_PRICE_ID")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:8080")
SECRET_KEY = os.getenv("SECRET_KEY", "a_very_secret_key_for_development")

stripe.api_key = STRIPE_SECRET_KEY

# IMPORTANT: For production, restrict this to your frontend's actual URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://127.0.0.1:5500"], # Add all allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Security & Authentication ---
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # Token expires in 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- Helper Functions ---
def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
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

def get_client_ip(request: Request):
    x_forwarded_for = request.headers.get('x-forwarded-for')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.client.host

# --- API Endpoints ---
@app.get("/")
def read_root():
    return {"message": "Welcome to the SmartDocFixer API"}

@app.post("/signup", response_model=schemas.Token)
async def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    email = user.email
    password = user.password

    if "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    db_user = db.query(models.User).filter(models.User.email == email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(password)
    new_user = models.User(email=email, password_hash=hashed_password, plan="free")
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.email, "plan": new_user.plan},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "plan": new_user.plan}

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
        data={"sub": user.email, "plan": user.plan},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "plan": user.plan}

@app.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: Annotated[models.User, Depends(get_current_user)]):
    """Get current user's details."""
    return current_user

# --- Document Processing Endpoint ---
FREE_TIER_LIMIT = 3
PRO_TIER_LIMIT = 1000

@app.post("/fix-document/")
async def upload_and_fix(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Upload, validate, and fix a document."""
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Only .docx files are supported.")

    usage_count = len(current_user.processed_files)
    
    if current_user.plan == "free" and usage_count >= FREE_TIER_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"error": "Upgrade required", "message": f"You have reached your limit of {FREE_TIER_LIMIT} free documents. Upgrade to Pro for more!", "action": "upgrade"}
        )
    
    if current_user.plan == "pro" and usage_count >= PRO_TIER_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "Monthly limit reached", "message": f"You have reached your generous monthly limit of {PRO_TIER_LIMIT} documents.", "action": "contact_support"}
        )
    
    try:
        ip_address = get_client_ip(request)
        output_path = await fix_document(file)

        # Track usage in the database by creating a ProcessedFile record
        new_file_record = models.ProcessedFile(
            user_id=current_user.id, 
            file_name=file.filename, 
            ip_address=ip_address
        )
        db.add(new_file_record)
        db.commit()
        
        return FileResponse(
            path=output_path,
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            filename=f"fixed_{file.filename}"
        )
    except Exception as e:
        print(f"Error processing document: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while processing the document: {e}")

# --- Stripe & Payment Endpoints ---
@app.post("/create-checkout-session")
async def create_checkout_session(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Creates a Stripe checkout session for a user to upgrade to Pro."""
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[{'price': STRIPE_PRO_PRICE_ID, 'quantity': 1}],
            mode='subscription',
            success_url=f"{FRONTEND_URL}/success.html?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/cancel.html",
            customer_email=current_user.email,
            # Pass user ID to identify user in webhook
            metadata={'user_id': current_user.id}
        )
        return JSONResponse(status_code=200, content={"url": checkout_session.url})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stripe-webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Listens for events from Stripe to confirm successful payments."""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get('metadata', {}).get('user_id')
        stripe_customer_id = session.get('customer')

        if user_id:
            user = db.query(models.User).filter(models.User.id == int(user_id)).first()
            if user:
                user.plan = 'pro'
                user.stripe_customer_id = stripe_customer_id
                db.commit()
                print(f"User {user.email} (ID: {user_id}) successfully upgraded to Pro.")

    return JSONResponse(status_code=200, content={"status": "success"})