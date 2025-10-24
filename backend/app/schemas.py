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
    criterion: str; max_points: int
    class Config:
        from_attributes = True

class OptionCreate(BaseModel):
    option_text: str; is_correct: bool

class QuestionCreate(BaseModel):
    question_text: str; question_type: str; score: int; options: List[OptionCreate]
    concept_tags: Optional[List[str]] = None

class CourseworkCreate(BaseModel):
    name: str; available_from: datetime; due_at: Optional[datetime] = None
    coursework_type: str 
    questions: Optional[List[QuestionCreate]] = None
    rubric: Optional[List[RubricCriterion]] = None
    rubric_file_url: Optional[str] = None
    material_file_urls: Optional[List[str]] = None 
    concept_tags: Optional[List[str]] = None

class CourseworkDisplay(BaseModel):
    id: int; name: str; coursework_type: str; available_from: datetime
    due_at: Optional[datetime] = None; classroom_id: int
    class Config:
        from_attributes = True

# Schema for taking a quiz
class OptionForStudent(BaseModel):
    id: int; option_text: str
    class Config:
        from_attributes: True 

class QuestionForStudent(BaseModel):
    id: int; question_text: str; question_type: str; score: int
    options: List[OptionForStudent]
    class Config:
        from_attributes: True

class CourseworkForStudent(BaseModel):
    id: int; name: str; coursework_type: str; available_from: datetime
    due_at: Optional[datetime] = None
    rubric: Optional[List[RubricCriterion]] = None
    rubric_file_url: Optional[str] = None
    material_file_urls: Optional[List[str]] = None # --- NEW ---
    questions: Optional[List[QuestionForStudent]] = None
    class Config:
        from_attributes: True

# --- Submission Schemas ---

class AnswerAttempt(BaseModel):
    question_id: int; selected_option_ids: List[int]

class QuizSubmissionCreate(BaseModel):
    answers: List[AnswerAttempt]

class EssaySubmissionCreate(BaseModel):
    submission_text: Optional[str] = None # Text might come from file later
    submission_file_url: Optional[str] = None

# --- NEW: Schemas for Viewing Submission (Req #4) ---

class OptionResultDisplay(BaseModel):
    id: int; option_text: str; is_correct: bool
    class Config:
        from_attributes: True
        
class QuestionResultDisplay(BaseModel):
    id: int; question_text: str; question_type: str; score: int
    options: List[OptionResultDisplay]
    class Config:
        from_attributes: True

class SubmissionAnswerDisplay(BaseModel):
    id: int; question: QuestionResultDisplay; selected_option_ids: List[int]
    class Config:
        from_attributes: True
        
class AIFeedbackDisplay(BaseModel):
    criterion: str; score: int; justification: str
    max_points: Optional[int] = None # Add max points for context
    class Config:
        from_attributes: True

class SubmissionDetail(BaseModel):
    id: int; submitted_at: datetime
    score: Optional[float] = None # AI Score
    teacher_override_score: Optional[float] = None # --- NEW ---
    final_score: Optional[float] = None # --- NEW (Implicitly uses property) ---
    status: str
    coursework_id: int; student_id: int
    
    submission_text: Optional[str] = None
    submission_file_url: Optional[str] = None
    answers: Optional[List[SubmissionAnswerDisplay]] = None
    ai_feedback: Optional[List[AIFeedbackDisplay]] = None
    teacher_feedback: Optional[str] = None # --- NEW ---
    
    coursework: CourseworkDisplay
    student: UserDisplay # --- NEW: Include student info ---

    class Config:
        from_attributes = True

# --- NEW: Schemas for Rubric Upload (Req #3) ---

class RubricParseRequest(BaseModel): raw_text: str
class RubricParseResponse(BaseModel): rubric: List[RubricCriterion]

class QuizGenerationRequest(BaseModel):
    topic: Optional[str] = None # Optional now
    material_file_urls: List[str] # --- NEW ---
    num_questions: int; difficulty: str

class QuizGenerationResponse(BaseModel):
    questions: List[QuestionCreate]
    
# --- NEW: Schema for Teacher Approval (Req #2) ---
class SubmissionApproval(BaseModel):
    teacher_override_score: Optional[float] = None # Score between 0.0 and 1.0
    teacher_feedback: Optional[str] = None

class DSKGNode(BaseModel):
    concept: str
    score: float
    last_assessed: datetime

class DSKGProfileResponse(BaseModel):
    student: UserDisplay  # The student's public info
    dskg: List[DSKGNode]  # Their knowledge graph

class CourseworkForStudentList(CourseworkDisplay):
    submission_id: Optional[int] = None

