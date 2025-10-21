from pydantic import BaseModel, constr
from typing import Optional

# Schema for creating a new user (registration)
class UserCreate(BaseModel):
    email: str
    password: constr(min_length=6, max_length=72)
    role: str  # "teacher" or "student"

# Schema for logging in a user
class UserLogin(BaseModel):
    email: str
    password: str
    role: str

# Schema for the JWT token response
class Token(BaseModel):
    access_token: str
    token_type: str

# Schema for the data hidden inside the JWT
class TokenData(BaseModel):
    email: Optional[str] = None