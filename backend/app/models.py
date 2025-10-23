from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Float, Text, JSON
from sqlalchemy.orm import relationship
from .database import Base
import secrets
from sqlalchemy.sql import func

# --- User model (from M3.5) ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)
    enrollment_number = Column(String, unique=True, index=True, nullable=True)
    is_approved = Column(Boolean, default=False, nullable=False)
    
    owned_classrooms = relationship("Classroom", back_populates="owner")
    enrolled_classrooms = relationship("Classroom", secondary="enrollments", back_populates="students")

# --- Classroom model (from M2) ---
def generate_invite_code():
    return secrets.token_hex(3).upper()

class Classroom(Base):
    __tablename__ = "classrooms"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    invite_code = Column(String, unique=True, index=True, default=generate_invite_code)
    
    teacher_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="owned_classrooms")
    
    students = relationship("User", secondary="enrollments", back_populates="enrolled_classrooms")
    
    # --- ADDED RELATIONSHIP ---
    courseworks = relationship("Coursework", back_populates="classroom", cascade="all, delete-orphan")

# --- Enrollment model (from M2) ---
class Enrollment(Base):
    __tablename__ = "enrollments"
    student_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), primary_key=True)

# --- RENAMED: Coursework (was Assignment) ---
class Coursework(Base):
    __tablename__ = "coursework" # --- RENAMED ---
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    
    # --- UPDATED: Deadline fields ---
    available_from = Column(DateTime(timezone=True), server_default=func.now()) # Start time
    due_at = Column(DateTime(timezone=True), nullable=True) # End time
    
    # --- UPDATED: Type field ---
    # Will be 'quiz', 'assignment', 'case_study', 'essay'
    coursework_type = Column(String, nullable=False)
    
    # For essays/assignments
    rubric = Column(JSON, nullable=True) 
    
    # Link to classroom
    classroom_id = Column(Integer, ForeignKey("classrooms.id"))
    classroom = relationship("Classroom", back_populates="courseworks")
    
    # For quizzes
    questions = relationship("Question", back_populates="coursework", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="coursework", cascade="all, delete-orphan")

# --- Question model (Updated relationship) ---
class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(Text, nullable=False)
    
    # --- UPDATED RELATIONSHIP ---
    coursework_id = Column(Integer, ForeignKey("coursework.id"))
    coursework = relationship("Coursework", back_populates="questions")
    
    options = relationship("Option", back_populates="question", cascade="all, delete-orphan")
    submission_answers = relationship("SubmissionAnswer", back_populates="question")

# --- Option model (No change) ---
class Option(Base):
    __tablename__ = "options"
    id = Column(Integer, primary_key=True, index=True)
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"))
    question = relationship("Question", back_populates="options")

# --- Submission model (Updated field names) ---
class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    score = Column(Float, nullable=True) 
    
    # --- RENAMED: submission_content -> submission_text ---
    submission_text = Column(Text, nullable=True) 
    
    ai_feedback = Column(JSON, nullable=True)
    # --- RENAMED: teacher_feedback (for M5) ---
    final_feedback = Column(Text, nullable=True)
    final_score = Column(Float, nullable=True)
    
    status = Column(String, default="SUBMITTED", nullable=False) 
    
    # --- UPDATED RELATIONSHIP ---
    coursework_id = Column(Integer, ForeignKey("coursework.id"))
    coursework = relationship("Coursework", back_populates="submissions")
    
    student_id = Column(Integer, ForeignKey("users.id"))
    student = relationship("User")
    
    answers = relationship("SubmissionAnswer", back_populates="submission", cascade="all, delete-orphan")

# --- SubmissionAnswer model (No change) ---
class SubmissionAnswer(Base):
    __tablename__ = "submission_answers"
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"))
    submission = relationship("Submission", back_populates="answers")
    question_id = Column(Integer, ForeignKey("questions.id"))
    question = relationship("Question", back_populates="submission_answers")
    selected_option_id = Column(Integer, ForeignKey("options.id"))
    selected_option = relationship("Option")