from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import Boolean, DateTime, Float, Text
from sqlalchemy.sql import func
from .database import Base
import secrets # Import secrets to generate invite codes

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False) # "teacher" or "student"
    enrollment_number = Column(String, unique=True, index=True, nullable=True) # Nullable=True because teachers don't have one
    is_approved = Column(Boolean, default=False, nullable=False)
    # --- ADD THESE RELATIONSHIPS ---
    # If I am a teacher, what classrooms do I own?
    owned_classrooms = relationship("Classroom", back_populates="owner")
    
    # What classrooms am I enrolled in (as a student)?
    enrolled_classrooms = relationship(
        "Classroom", secondary="enrollments", back_populates="students"
    )

def generate_invite_code():
    """Generates a unique 6-character code."""
    return secrets.token_hex(3).upper()

class Classroom(Base):
    __tablename__ = "classrooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    invite_code = Column(String, unique=True, index=True, default=generate_invite_code)
    
    # --- ADD THESE RELATIONSHIPS ---
    # Link to the teacher who owns this class
    teacher_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="owned_classrooms")
    
    # Link to all students enrolled in this class
    students = relationship(
        "User", secondary="enrollments", back_populates="enrolled_classrooms"
    )

class Enrollment(Base):
    """This is a many-to-many association table."""
    __tablename__ = "enrollments"
    
    student_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), primary_key=True)

class Assignment(Base):
    __tablename__ = "assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    due_at = Column(DateTime(timezone=True), nullable=True) # For deadlines
    assignment_type = Column(String, default="quiz") # For future (e.g., 'essay')
    
    # Link to the classroom
    classroom_id = Column(Integer, ForeignKey("classrooms.id"))
    classroom = relationship("Classroom")
    
    # Link to all questions
    questions = relationship("Question", back_populates="assignment", cascade="all, delete-orphan")
    # Link to all submissions
    submissions = relationship("Submission", back_populates="assignment", cascade="all, delete-orphan")

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(Text, nullable=False)
    # In the future: question_type (e.g., 'multiple-choice', 'short-answer')
    
    # Link to the assignment
    assignment_id = Column(Integer, ForeignKey("assignments.id"))
    assignment = relationship("Assignment", back_populates="questions")
    
    # Link to all options
    options = relationship("Option", back_populates="question", cascade="all, delete-orphan")
    # Link to all answers
    submission_answers = relationship("SubmissionAnswer", back_populates="question")

class Option(Base):
    __tablename__ = "options"
    
    id = Column(Integer, primary_key=True, index=True)
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)
    
    # Link to the question
    question_id = Column(Integer, ForeignKey("questions.id"))
    question = relationship("Question", back_populates="options")

class Submission(Base):
    __tablename__ = "submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    score = Column(Float, nullable=True) # The grade (e.g., 0.8 for 80%)
    
    # Link to the assignment
    assignment_id = Column(Integer, ForeignKey("assignments.id"))
    assignment = relationship("Assignment", back_populates="submissions")
    
    # Link to the student
    student_id = Column(Integer, ForeignKey("users.id"))
    student = relationship("User")
    
    # Link to all answers
    answers = relationship("SubmissionAnswer", back_populates="submission", cascade="all, delete-orphan")

class SubmissionAnswer(Base):
    __tablename__ = "submission_answers"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Link to the main submission
    submission_id = Column(Integer, ForeignKey("submissions.id"))
    submission = relationship("Submission", back_populates="answers")
    
    # Link to the question being answered
    question_id = Column(Integer, ForeignKey("questions.id"))
    question = relationship("Question", back_populates="submission_answers")
    
    # Link to the specific option the student chose
    selected_option_id = Column(Integer, ForeignKey("options.id"))
    selected_option = relationship("Option")