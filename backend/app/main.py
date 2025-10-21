from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi import status, Depends
from .api import classrooms
from datetime import timedelta

from . import models, schemas, crud, auth
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Include the new routers ---
app.include_router(classrooms.router)


# --- Auth Endpoints ---

@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Registers a new user (teacher or student)."""
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check for valid role
    if user.role not in ["teacher", "student"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'teacher' or 'student'")
        
    new_user = crud.create_user(db=db, user=user)
    return {"message": "User created successfully"}

@app.post("/api/auth/login", response_model=schemas.Token)
def login_for_access_token(user_login: schemas.UserLogin, db: Session = Depends(get_db)):
    """Logs in a user and returns a JWT access token."""
    user = crud.get_user_by_email(db, email=user_login.email)
    
    # Check 1: Does the user exist?
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    # Check 2: Does the password match?
    if not auth.verify_password(user_login.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
        
    # Check 3: Is the role correct?
    if user.role != user_login.role:
        raise HTTPException(status_code=401, detail=f"You are not registered as a {user_login.role}")
    
    # Create and return the access token
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email, "role": user.role}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/")
def read_root():
    return {"message": "Welcome to the A-LMS Backend! Auth & Classrooms are active."}