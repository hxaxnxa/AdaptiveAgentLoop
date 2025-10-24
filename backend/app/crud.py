from sqlalchemy.orm import Session, joinedload
from . import models, schemas, auth
from datetime import datetime, timezone

# --- User Functions (from M3.5) ---
def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()
def get_user_by_enrollment_number(db: Session, enrollment_number: str):
    return db.query(models.User).filter(models.User.enrollment_number == enrollment_number).first()
def get_user_by_login_id(db: Session, login_id: str):
    return db.query(models.User).filter(
        (models.User.email == login_id) | (models.User.enrollment_number == login_id)
    ).first()
def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = auth.get_password_hash(user.password)
    is_approved = True if user.role == 'student' else False
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        role=user.role,
        enrollment_number=user.enrollment_number,
        is_approved=is_approved
    )
    db.add(db_user); db.commit(); db.refresh(db_user); return db_user

# --- Classroom Functions (from M3.5) ---
def create_classroom(db: Session, classroom: schemas.ClassroomCreate, teacher_id: int):
    db_classroom = models.Classroom(name=classroom.name, teacher_id=teacher_id)
    db.add(db_classroom); db.commit(); db.refresh(db_classroom); return db_classroom
def get_classrooms_by_teacher(db: Session, teacher_id: int):
    return db.query(models.Classroom).filter(models.Classroom.teacher_id == teacher_id).all()
def get_classrooms_by_student(db: Session, student_id: int):
    return db.query(models.Classroom).join(models.Enrollment).filter(
        models.Enrollment.student_id == student_id
    ).all()
def get_classroom_by_invite_code(db: Session, code: str):
    return db.query(models.Classroom).filter(models.Classroom.invite_code == code).first()
def add_student_to_classroom(db: Session, student_id: int, classroom_id: int):
    enrollment = models.Enrollment(student_id=student_id, classroom_id=classroom_id)
    db.add(enrollment); db.commit(); return enrollment
def get_classroom_by_id(db: Session, classroom_id: int):
    return db.query(models.Classroom).get(classroom_id)
def is_student_enrolled(db: Session, student_id: int, classroom_id: int):
    return db.query(models.Enrollment).filter(
        models.Enrollment.student_id == student_id,
        models.Enrollment.classroom_id == classroom_id
    ).first() is not None
def get_students_in_classroom(db: Session, classroom_id: int):
    return db.query(models.User).join(models.Enrollment).filter(
        models.Enrollment.classroom_id == classroom_id
    ).order_by(models.User.enrollment_number).all()
def remove_student_from_classroom(db: Session, student_id: int, classroom_id: int):
    db.query(models.Enrollment).filter(
        models.Enrollment.student_id == student_id,
        models.Enrollment.classroom_id == classroom_id
    ).delete()
    db.commit()

# --- RENAMED: Coursework & Submission Functions ---

def create_coursework(db: Session, coursework: schemas.CourseworkCreate, classroom_id: int):
    rubric_data = [r.dict() for r in coursework.rubric] if coursework.rubric else None
    
    db_coursework = models.Coursework(
        name=coursework.name,
        available_from=coursework.available_from,
        due_at=coursework.due_at,
        coursework_type=coursework.coursework_type,
        rubric=rubric_data,
        rubric_file_url=coursework.rubric_file_url,
        material_file_urls=coursework.material_file_urls, # --- NEW ---
        classroom_id=classroom_id
    )
    db.add(db_coursework); db.commit(); db.refresh(db_coursework)
    
    for question_in in coursework.questions or []:
        db_question = models.Question(
            question_text=question_in.question_text,
            question_type=question_in.question_type,
            score=question_in.score,
            coursework_id=db_coursework.id
        )
        db.add(db_question); db.commit(); db.refresh(db_question)
        
        for option_in in question_in.options:
            db_option = models.Option(
                option_text=option_in.option_text,
                is_correct=option_in.is_correct,
                question_id=db_question.id
            )
            db.add(db_option)
            
    db.commit(); db.refresh(db_coursework)
    return db_coursework

def get_courseworks_for_classroom(db: Session, classroom_id: int):
    now = datetime.now(timezone.utc)
    query = db.query(models.Coursework).filter(models.Coursework.classroom_id == classroom_id)
    # If adding student context: query = query.filter(models.Coursework.available_from <= now)
    return query.order_by(models.Coursework.available_from).all()

def get_coursework_with_details(db: Session, coursework_id: int): # --- RENAMED ---
    return db.query(models.Coursework).filter(models.Coursework.id == coursework_id).options(
        joinedload(models.Coursework.questions).joinedload(models.Question.options)
    ).first()

def get_question_with_options(db: Session, question_id: int): # --- NEW ---
    return db.query(models.Question).filter(models.Question.id == question_id).options(
        joinedload(models.Question.options)
    ).first()

def get_submission_by_student_and_coursework(db: Session, student_id: int, coursework_id: int):
    return db.query(models.Submission).filter(
        models.Submission.student_id == student_id,
        models.Submission.coursework_id == coursework_id
    ).first()

def create_quiz_submission(db: Session, submission: schemas.QuizSubmissionCreate, coursework_id: int, student_id: int):
    db_submission = models.Submission(
        coursework_id=coursework_id,
        student_id=student_id,
        status="SUBMITTED"
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    
    for answer_in in submission.answers:
        db_answer = models.SubmissionAnswer(
            submission_id=db_submission.id,
            question_id=answer_in.question_id,
            selected_option_ids=answer_in.selected_option_ids # --- UPDATED ---
        )
        db.add(db_answer)
        
    db.commit()
    db.refresh(db_submission)
    return db_submission

def create_essay_submission(db: Session, submission: schemas.EssaySubmissionCreate, coursework_id: int, student_id: int):
    db_submission = models.Submission(
        coursework_id=coursework_id,
        student_id=student_id,
        submission_text=submission.submission_text,
        submission_file_url=submission.submission_file_url,
        status="SUBMITTED"
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    return db_submission

def get_submission_detail(db: Session, submission_id: int):
    # --- UPDATED: To handle new quiz answer model ---
    return db.query(models.Submission).filter(
        models.Submission.id == submission_id
    ).options(
        joinedload(models.Submission.coursework),
        joinedload(models.Submission.student), # --- ADDED ---
        joinedload(models.Submission.answers)
            .joinedload(models.SubmissionAnswer.question)
            .joinedload(models.Question.options)
    ).first()

def get_submissions_for_coursework(db: Session, coursework_id: int):
    """NEW: For the teacher's review list"""
    return db.query(models.Submission).filter(
        models.Submission.coursework_id == coursework_id
    ).options(
        joinedload(models.Submission.student) # Include student info
    ).order_by(models.Submission.submitted_at).all()

# --- NEW: Functions for Regrading and Approval (Req #2, #3) ---

def update_option_correctness(db: Session, option_id: int, is_correct: bool):
    """Updates a single option's correct status."""
    db.query(models.Option).filter(models.Option.id == option_id).update({"is_correct": is_correct})
    db.commit()

def get_submissions_for_question(db: Session, question_id: int):
    """Finds all submissions that answered a specific question."""
    return db.query(models.Submission).join(models.SubmissionAnswer).filter(
        models.SubmissionAnswer.question_id == question_id
    ).all()

def approve_submission(db: Session, submission_id: int, approval_data: schemas.SubmissionApproval):
    """Applies teacher overrides and sets status to GRADED."""
    db.query(models.Submission).filter(models.Submission.id == submission_id).update({
        "teacher_override_score": approval_data.teacher_override_score,
        "teacher_feedback": approval_data.teacher_feedback,
        "status": "GRADED"
    })
    db.commit()