from pydantic import BaseModel, constr
from typing import Optional, List # Import List
from datetime import datetime

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

# --- NEW: Schemas for Creating a Quiz ---

class OptionCreate(BaseModel):
    option_text: str
    is_correct: bool

class QuestionCreate(BaseModel):
    question_text: str
    options: List[OptionCreate] # A list of 2-4 options

class AssignmentCreate(BaseModel):
    name: str
    due_at: Optional[datetime] = None
    questions: List[QuestionCreate] # A list of questions

# --- NEW: Schemas for Displaying a Quiz ---
# (For the student taking the quiz - answers are hidden)

class OptionForStudent(BaseModel):
    id: int
    option_text: str
    
    class Config:
        from_attributes = True

class QuestionForStudent(BaseModel):
    id: int
    question_text: str
    options: List[OptionForStudent]
    
    class Config:
        from_attributes = True

class AssignmentForStudent(BaseModel):
    id: int
    name: str
    due_at: Optional[datetime] = None
    classroom_id: int
    questions: List[QuestionForStudent]
    
    class Config:
        from_attributes = True

class Assignment(BaseModel):
    id: int
    name: str
    due_at: Optional[datetime] = None
    classroom_id: int

    class Config:
        from_attributes = True

# --- NEW: Schemas for Submitting a Quiz ---

class AnswerAttempt(BaseModel):
    question_id: int
    selected_option_id: int

class SubmissionCreate(BaseModel):
    answers: List[AnswerAttempt]

# --- NEW: Schemas for Displaying Results ---

class SubmissionResult(BaseModel):
    id: int
    submitted_at: datetime
    score: Optional[float] = None
    assignment_id: int
    student_id: int
    
    class Config:
        from_attributes = True