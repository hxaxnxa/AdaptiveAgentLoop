from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Float, Text, JSON
from sqlalchemy.orm import relationship
from .database import Base
import secrets
from sqlalchemy.sql import func
from sqlalchemy.ext.mutable import MutableList
# --- User, Classroom, Enrollment (No Change from M3.5) ---
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
    courseworks = relationship("Coursework", back_populates="classroom", cascade="all, delete-orphan")

class Enrollment(Base):
    __tablename__ = "enrollments"
    student_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), primary_key=True)

# --- Coursework (UPDATED) ---
class Coursework(Base):
    __tablename__ = "coursework"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    available_from = Column(DateTime(timezone=True), server_default=func.now())
    due_at = Column(DateTime(timezone=True), nullable=True)
    coursework_type = Column(String, nullable=False) # quiz, assignment, case_study, essay
    concept_tags = Column(MutableList.as_mutable(JSON), nullable=True, default=[])
    
    # --- UPDATED: Rubric can be a file or embedded JSON ---
    rubric = Column(JSON, nullable=True) 
    rubric_file_url = Column(String, nullable=True) # --- NEW ---
    material_file_urls = Column(MutableList.as_mutable(JSON), nullable=True, default=[])
    classroom_id = Column(Integer, ForeignKey("classrooms.id"))
    classroom = relationship("Classroom", back_populates="courseworks")
    questions = relationship("Question", back_populates="coursework", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="coursework", cascade="all, delete-orphan")

# --- Question (UPDATED) ---
class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(Text, nullable=False)
    
    # --- NEW: 'multiple_choice' (one answer) vs 'multiple_response' (many answers) ---
    question_type = Column(String, default="multiple_choice", nullable=False)
    score = Column(Integer, default=1, nullable=False) # --- NEW: Manual Score ---
    is_editable = Column(Boolean, default=True)
    coursework_id = Column(Integer, ForeignKey("coursework.id"))
    coursework = relationship("Coursework", back_populates="questions")
    options = relationship("Option", back_populates="question", cascade="all, delete-orphan")
    submission_answers = relationship("SubmissionAnswer", back_populates="question")
    concept_tags = Column(MutableList.as_mutable(JSON), nullable=True, default=[])

# --- Option (No Change) ---
class Option(Base):
    __tablename__ = "options"
    id = Column(Integer, primary_key=True, index=True)
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"))
    question = relationship("Question", back_populates="options")

# --- Submission (UPDATED) ---
class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    score = Column(Float, nullable=True) 
    submission_text = Column(Text, nullable=True) # Extracted text
    
    # --- NEW: Link to the uploaded file ---
    submission_file_url = Column(String, nullable=True) 
    
    ai_feedback = Column(JSON, nullable=True)
    teacher_override_score = Column(Float, nullable=True)
    teacher_feedback = Column(Text, nullable=True)

    status = Column(String, default="SUBMITTED", nullable=False) 
    coursework_id = Column(Integer, ForeignKey("coursework.id"))
    coursework = relationship("Coursework", back_populates="submissions")
    student_id = Column(Integer, ForeignKey("users.id"))
    student = relationship("User")
    answers = relationship("SubmissionAnswer", back_populates="submission", cascade="all, delete-orphan")
    
    # --- Property to get the final score ---
    @property
    def final_score(self):
        # Teacher override takes precedence
        if self.teacher_override_score is not None:
            return self.teacher_override_score
        # Otherwise, use the auto-generated score
        return self.score
    
    
# --- SubmissionAnswer (UPDATED) ---
class SubmissionAnswer(Base):
    __tablename__ = "submission_answers"
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"))
    submission = relationship("Submission", back_populates="answers")
    question_id = Column(Integer, ForeignKey("questions.id"))
    question = relationship("Question", back_populates="submission_answers")
    
    # --- UPDATED: To support 'multiple_response' ---
    # For single-choice, this will be a list with one item
    selected_option_ids = Column(JSON, nullable=True)

class RemedialQuiz(Base):
    __tablename__ = "remedial_quizzes"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    concept = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_completed = Column(Boolean, default=False)
    
    student = relationship("User")
    questions = relationship("RemedialQuestion", cascade="all, delete-orphan")

class RemedialQuestion(Base):
    __tablename__ = "remedial_questions"
    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("remedial_quizzes.id"))
    question_text = Column(Text, nullable=False)
    question_type = Column(String, default="multiple_choice", nullable=False)
    
    quiz = relationship("RemedialQuiz", back_populates="questions")
    options = relationship("RemedialOption", cascade="all, delete-orphan")

class RemedialOption(Base):
    __tablename__ = "remedial_options"
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("remedial_questions.id"))
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)
    
    question = relationship("RemedialQuestion", back_populates="options")