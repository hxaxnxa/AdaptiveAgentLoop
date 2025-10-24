from sqlalchemy.orm import Session, joinedload
from . import models, schemas, auth
from datetime import datetime, timezone
from typing import List, Optional

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
        material_file_urls=coursework.material_file_urls,
        classroom_id=classroom_id,
        concept_tags=coursework.concept_tags  # <-- FIX: Added this line
    )
    db.add(db_coursework); db.commit(); db.refresh(db_coursework)
    
    for question_in in coursework.questions or []:
        db_question = models.Question(
            question_text=question_in.question_text,
            question_type=question_in.question_type,
            score=question_in.score,
            coursework_id=db_coursework.id,
            concept_tags=question_in.concept_tags  # <-- FIX: Added this line
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

def delete_coursework(db: Session, coursework: models.Coursework):
    """Deletes a coursework item. Cascades are handled by the DB relationship."""
    db.delete(coursework)
    db.commit()

def get_courseworks_for_classroom(db: Session, classroom_id: int, student_id: Optional[int] = None):
    """
    Gets all coursework for a classroom.
    If student_id is provided, it also fetches their submission status.
    """
    courseworks = db.query(models.Coursework).filter(
        models.Coursework.classroom_id == classroom_id
    ).order_by(models.Coursework.available_from).all()
    
    if student_id is None:
        # Teacher view: just return the coursework
        return courseworks

    # Student view: Find their submissions for this class
    submissions = db.query(models.Submission).filter(
        models.Submission.student_id == student_id,
        models.Submission.coursework_id.in_([cw.id for cw in courseworks])
    ).all()
    
    # Create a map for fast lookup
    submission_map = {sub.coursework_id: sub.id for sub in submissions}
    
    # Build the enhanced response
    response_list = []
    for cw in courseworks:
        cw_data = schemas.CourseworkForStudentList.model_validate(cw)
        cw_data.submission_id = submission_map.get(cw.id)
        response_list.append(cw_data)
        
    return response_list

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

def get_gradebook_data(db: Session, classroom_id: int):
    # 1. Get all coursework for the class, ordered
    courseworks = db.query(models.Coursework).filter(
        models.Coursework.classroom_id == classroom_id
    ).order_by(models.Coursework.available_from).all()
    
    # 2. Get all students in the class
    students = get_students_in_classroom(db, classroom_id)
    
    # 3. Get all submissions for this class
    submissions = db.query(models.Submission).join(models.Coursework).filter(
        models.Coursework.classroom_id == classroom_id
    ).all()
    
    # 4. Create a fast lookup map: { (student_id, coursework_id): final_score }
    submission_map = {
        (sub.student_id, sub.coursework_id): sub.final_score
        for sub in submissions
        if sub.final_score is not None
    }
    
    # 5. Build the response structure
    student_rows = []
    for student in students:
        scores = {}
        for cw in courseworks:
            score = submission_map.get((student.id, cw.id))
            scores[cw.id] = {
                "coursework_id": cw.id,
                "final_score": score
            }
        student_rows.append({
            "student": student,
            "scores": scores
        })
        
    return {
        "courseworks": courseworks,
        "students": student_rows
    }


def get_class_analytics(db: Session, classroom_id: int):
    courseworks = db.query(models.Coursework).filter(
        models.Coursework.classroom_id == classroom_id
    ).all()
    
    total_students = db.query(models.Enrollment).filter(
        models.Enrollment.classroom_id == classroom_id
    ).count()
    if total_students == 0:
        return [] # Return empty if no students
        
    analytics = []
    for cw in courseworks:
        # --- FIX: Get ALL submissions for the rate ---
        all_submissions = db.query(models.Submission).filter(
            models.Submission.coursework_id == cw.id
        ).all()
        
        # --- FIX: Filter for submissions with a score ---
        scores = [s.final_score for s in all_submissions if s.final_score is not None]
        
        if scores:
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
            distribution = {
                'A': len([s for s in scores if s >= 0.9]),
                'B': len([s for s in scores if 0.8 <= s < 0.9]),
                'C': len([s for s in scores if 0.7 <= s < 0.8]),
                'D': len([s for s in scores if 0.6 <= s < 0.7]),
                'F': len([s for s in scores if s < 0.6]),
            }
        else:
            avg_score, max_score, min_score = None, None, None
            distribution = {}

        analytics.append({
            "coursework_id": cw.id,
            "coursework_name": cw.name,
            "class_average": avg_score,
            "highest_score": max_score,
            "lowest_score": min_score,
            "submission_rate": f"{len(all_submissions)}/{total_students}",
            "grade_distribution": distribution
        })
    return analytics

def is_teacher_and_student_in_same_class(db: Session, teacher_id: int, student_id: int) -> bool:
    """Checks if a teacher and student share at least one classroom."""
    
    # Find all classrooms for the teacher
    teacher_classrooms = db.query(models.Classroom.id).filter(
        models.Classroom.teacher_id == teacher_id
    ).subquery()
    
    # Check if the student is enrolled in any of those classrooms
    enrollment = db.query(models.Enrollment).filter(
        models.Enrollment.student_id == student_id,
        models.Enrollment.classroom_id.in_(teacher_classrooms)
    ).first()
    
    return enrollment is not None