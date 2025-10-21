from sqlalchemy.orm import Session
from . import models, schemas, auth

# --- User Functions (No Change) ---
def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        email=user.email, 
        hashed_password=hashed_password, 
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- NEW: Classroom Functions ---

def create_classroom(db: Session, classroom: schemas.ClassroomCreate, teacher_id: int):
    """Creates a new classroom in the DB, linked to the teacher."""
    db_classroom = models.Classroom(name=classroom.name, teacher_id=teacher_id)
    db.add(db_classroom)
    db.commit()
    db.refresh(db_classroom)
    return db_classroom

def get_classrooms_by_teacher(db: Session, teacher_id: int):
    """Gets all classrooms owned by a specific teacher."""
    return db.query(models.Classroom).filter(models.Classroom.teacher_id == teacher_id).all()

def get_classrooms_by_student(db: Session, student_id: int):
    """Gets all classrooms a student is enrolled in."""
    # This is a query across the join table
    return db.query(models.Classroom).join(models.Enrollment).filter(
        models.Enrollment.student_id == student_id
    ).all()

def get_classroom_by_invite_code(db: Session, code: str):
    """Finds a classroom by its unique invite code."""
    return db.query(models.Classroom).filter(models.Classroom.invite_code == code).first()

def add_student_to_classroom(db: Session, student_id: int, classroom_id: int):
    """Creates an enrollment record."""
    enrollment = models.Enrollment(student_id=student_id, classroom_id=classroom_id)
    db.add(enrollment)
    db.commit()
    return enrollment