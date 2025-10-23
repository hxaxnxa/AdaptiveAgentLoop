from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import timedelta

from . import models, schemas, crud, auth
from .database import SessionLocal, engine
from .api import classrooms, coursework # --- UPDATED ---

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Include the routers ---
app.include_router(classrooms.router)
app.include_router(coursework.router) # --- UPDATED ---

# --- Auth Endpoints (from M3.5) ---
@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user_email = crud.get_user_by_email(db, email=user.email)
    if db_user_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if user.role == "student":
        if not user.enrollment_number:
            raise HTTPException(status_code=400, detail="Student registration requires an enrollment number")
        db_user_enrollment = crud.get_user_by_enrollment_number(db, enrollment_number=user.enrollment_number)
        if db_user_enrollment:
            raise HTTPException(status_code=400, detail="Enrollment number already registered")
    elif user.role == "teacher":
        if user.enrollment_number:
            raise HTTPException(status_code=400, detail="Teacher registration must not have an enrollment number")
    else:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'teacher' or 'student'")
    
    new_user = crud.create_user(db=db, user=user)
    
    if new_user.role == "teacher":
        return {"message": "Teacher account created successfully. It is pending admin approval."}
    
    return {"message": "Student account created successfully."}

@app.post("/api/auth/login", response_model=schemas.Token)
def login_for_access_token(user_login: schemas.UserLogin, db: Session = Depends(get_db)):
    user = crud.get_user_by_login_id(db, login_id=user_login.login_id)
    
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email/enrollment number or password")
    
    if not auth.verify_password(user_login.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email/enrollment number or password")
        
    if user.role != user_login.role:
        raise HTTPException(status_code=401, detail=f"You are not registered as a {user_login.role}")
        
    if not user.is_approved:
        raise HTTPException(status_code=401, detail="Account is pending approval. Please contact admin.")

    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email, "role": user.role}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/")
def read_root():
    return {"message": "Welcome to the A-LMS Backend! Coursework module is active."}