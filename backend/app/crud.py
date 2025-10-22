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

def create_assignment(db: Session, assignment: schemas.AssignmentCreate, classroom_id: int):
    """Creates a new assignment, with all its questions and options."""
    # 1. Create the main Assignment
    db_assignment = models.Assignment(
        name=assignment.name,
        due_at=assignment.due_at,
        classroom_id=classroom_id
    )
    db.add(db_assignment)
    db.commit()
    db.refresh(db_assignment)
    
    # 2. Loop and create each Question
    for question_in in assignment.questions:
        db_question = models.Question(
            question_text=question_in.question_text,
            assignment_id=db_assignment.id
        )
        db.add(db_question)
        db.commit()
        db.refresh(db_question)
        
        # 3. Loop and create each Option for the question
        for option_in in question_in.options:
            db_option = models.Option(
                option_text=option_in.option_text,
                is_correct=option_in.is_correct,
                question_id=db_question.id
            )
            db.add(db_option)
            
    # Commit all the nested options and questions
    db.commit()
    db.refresh(db_assignment)
    return db_assignment

def get_assignments_for_classroom(db: Session, classroom_id: int):
    """Gets all assignments for a single classroom."""
    return db.query(models.Assignment).filter(
        models.Assignment.classroom_id == classroom_id
    ).all()

def get_assignment(db: Session, assignment_id: int):
    """Gets a single assignment by its ID."""
    return db.query(models.Assignment).get(assignment_id)

def create_submission(db: Session, submission: schemas.SubmissionCreate, assignment_id: int, student_id: int):
    """Creates a new submission record and its associated answers."""
    # 1. Create the main Submission
    db_submission = models.Submission(
        assignment_id=assignment_id,
        student_id=student_id
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    
    # 2. Loop and create each SubmissionAnswer
    for answer_in in submission.answers:
        db_answer = models.SubmissionAnswer(
            submission_id=db_submission.id,
            question_id=answer_in.question_id,
            selected_option_id=answer_in.selected_option_id
        )
        db.add(db_answer)
        
    db.commit()
    db.refresh(db_submission)
    return db_submission

def get_submission(db: Session, submission_id: int, student_id: int):
    """Gets a submission result, ensuring it belongs to the student."""
    return db.query(models.Submission).filter(
        models.Submission.id == submission_id,
        models.Submission.student_id == student_id
    ).first()