from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
import secrets # Import secrets to generate invite codes

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False) # "teacher" or "student"

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