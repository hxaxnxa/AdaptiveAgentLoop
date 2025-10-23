from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- User & Auth Schemas (from M3.5) ---
class UserCreate(BaseModel):
    email: str
    password: str
    role: str
    enrollment_number: Optional[str] = None

class UserLogin(BaseModel):
    login_id: str
    password: str
    role: str
    
class UserDisplay(BaseModel):
    id: int
    email: str
    role: str
    enrollment_number: Optional[str] = None
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

# --- Classroom Schemas (from M2) ---
class ClassroomCreate(BaseModel):
    name: str

class ClassroomDisplay(BaseModel):
    id: int
    name: str
    invite_code: str
    owner: UserDisplay
    class Config:
        from_attributes = True

class JoinRequest(BaseModel):
    invite_code: str

class EnrolledClassroomDisplay(BaseModel):
    id: int
    name: str
    owner: UserDisplay
    class Config:
        from_attributes = True

# --- RENAMED: Coursework Schemas (was Assignment) ---

class RubricCriterion(BaseModel):
    criterion: str
    max_points: int
    class Config:
        from_attributes = True

class OptionCreate(BaseModel):
    option_text: str
    is_correct: bool

class QuestionCreate(BaseModel):
    question_text: str
    options: List[OptionCreate]

class CourseworkCreate(BaseModel): # --- RENAMED ---
    name: str
    available_from: datetime # --- ADDED ---
    due_at: Optional[datetime] = None
    coursework_type: str # 'quiz', 'assignment', 'case_study', 'essay'
    
    questions: Optional[List[QuestionCreate]] = None
    rubric: Optional[List[RubricCriterion]] = None

# Schema for the list on the classroom page
class CourseworkDisplay(BaseModel): # --- RENAMED ---
    id: int
    name: str
    coursework_type: str
    available_from: datetime
    due_at: Optional[datetime] = None
    classroom_id: int
    class Config:
        from_attributes = True

# Schema for taking a quiz
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

class CourseworkForStudent(BaseModel): # --- RENAMED ---
    id: int
    name: str
    coursework_type: str
    available_from: datetime
    due_at: Optional[datetime] = None
    rubric: Optional[List[RubricCriterion]] = None # Show rubric for essays
    questions: Optional[List[QuestionForStudent]] = None # Show questions for quizzes
    class Config:
        from_attributes = True

# --- Submission Schemas ---

class AnswerAttempt(BaseModel):
    question_id: int
    selected_option_id: int

class QuizSubmissionCreate(BaseModel): # --- RENAMED ---
    answers: List[AnswerAttempt]

class EssaySubmissionCreate(BaseModel): # --- RENAMED ---
    submission_text: str # --- RENAMED ---

# --- NEW: Schemas for Viewing Submission (Req #4) ---

class OptionResultDisplay(BaseModel):
    id: int
    option_text: str
    is_correct: bool
    class Config:
        from_attributes = True
        
class QuestionResultDisplay(BaseModel):
    id: int
    question_text: str
    options: List[OptionResultDisplay] # Show all options
    class Config:
        from_attributes = True

class SubmissionAnswerDisplay(BaseModel):
    id: int
    question: QuestionResultDisplay # Nested full question
    selected_option: OptionResultDisplay # Nested selected option
    class Config:
        from_attributes = True
        
class AIFeedbackDisplay(BaseModel):
    criterion: str
    score: int
    justification: str
    class Config:
        from_attributes = True

class SubmissionDetail(BaseModel): # --- RENAMED (was SubmissionResult) ---
    id: int
    submitted_at: datetime
    score: Optional[float] = None # This is the AI score
    status: str
    coursework_id: int
    student_id: int
    
    # --- ADDED: The actual content (Req #4) ---
    submission_text: Optional[str] = None # For essays
    answers: Optional[List[SubmissionAnswerDisplay]] = None # For quizzes
    ai_feedback: Optional[List[AIFeedbackDisplay]] = None # For graded essays
    coursework: CourseworkDisplay # So we know the type

    class Config:
        from_attributes = True

# --- NEW: Schemas for Rubric Upload (Req #3) ---

class RubricParseRequest(BaseModel):
    raw_text: str

class RubricParseResponse(BaseModel):
    rubric: List[RubricCriterion]