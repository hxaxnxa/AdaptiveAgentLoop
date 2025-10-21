from pydantic import BaseModel, constr
from typing import Optional, List # Import List

# --- User Schemas (No Change) ---
class UserCreate(BaseModel):
    email: str
    password: constr(min_length=6, max_length=72)
    role: str # "teacher" or "student"

class UserLogin(BaseModel):
    email: str
    password: str
    role: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None # Add role here

# --- NEW: Classroom Schemas ---

# Base schema for a User, to be nested in responses
class UserDisplay(BaseModel):
    id: int
    email: str
    role: str

    class Config:
        from_attributes = True # This tells Pydantic to read data from ORM models

# Schema for creating a classroom
class ClassroomCreate(BaseModel):
    name: str

# Schema for displaying a classroom
class ClassroomDisplay(BaseModel):
    id: int
    name: str
    invite_code: str
    owner: UserDisplay # Nested schema to show teacher info

    class Config:
        from_attributes = True
        
# Schema for a student joining a classroom
class JoinRequest(BaseModel):
    invite_code: str

# Schema for displaying a classroom for an enrolled student
class EnrolledClassroomDisplay(BaseModel):
    id: int
    name: str
    owner: UserDisplay # Show who the teacher is

    class Config:
        from_attributes = True