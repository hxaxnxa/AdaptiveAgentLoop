from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session # Import Session
from . import schemas, models, crud, database

# --- CONTEXT/KEYS (No Change) ---
SECRET_KEY = "b808acd65ef4da313e993ea339c20b3307a975b49cb71662ad2cb5add423b4c0" # Make sure this is the same as in Milestone 1
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# --- HASHING/TOKEN CREATION (No Change) ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- NEW FUNCTION: GET CURRENT USER ---
def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)
):
    """
    Decodes the JWT token to get the user's email and fetches the user from the DB.
    This function is a dependency that our protected endpoints will use.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub") # "sub" is the key we used in login
        if email is None:
            raise credentials_exception
        # Store the payload's data in our TokenData schema
        token_data = schemas.TokenData(email=email, role=payload.get("role"))
    except JWTError:
        raise credentials_exception
    
    # Get the user from the database
    user = crud.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    
    # We can also store the token data (like role) in the user object
    # for easy access in our endpoints
    user.token_role = token_data.role
    return user

# --- NEW FUNCTION: GET CURRENT *ACTIVE* USER (Optional but good practice) ---
# This is a simple wrapper for now
async def get_current_active_user(
    current_user: models.User = Depends(get_current_user)
):
    # In the future, you could add a check here (e.g., if user.is_active is False)
    return current_user

def get_teacher_user(
    current_user: models.User = Depends(get_current_active_user)
):
    """Dependency to ensure the user is an *approved* teacher."""
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized: Requires teacher role"
        )
    if not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Teacher account is pending approval"
        )
    return current_user

def get_student_user(
    current_user: models.User = Depends(get_current_active_user)
):
    """Dependency to ensure the user is a student."""
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized: Requires student role"
        )
    return current_user