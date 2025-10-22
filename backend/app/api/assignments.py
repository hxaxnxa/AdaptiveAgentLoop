from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from .. import crud, models, schemas, auth
from ..database import get_db
from ..agents.quiz_grader import grade_quiz # Import our new agent

router = APIRouter(
    prefix="/api/assignments",
    tags=["assignments"]
)

@router.post(
    "/classrooms/{classroom_id}", 
    response_model=schemas.AssignmentForStudent, # Return the assignment
    status_code=status.HTTP_201_CREATED
)
def create_new_assignment(
    classroom_id: int,
    assignment: schemas.AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_teacher_user)
):
    db_classroom = crud.get_classroom_by_id(db, classroom_id=classroom_id)
    if not db_classroom or db_classroom.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this classroom")
    
    return crud.create_assignment(db=db, assignment=assignment, classroom_id=classroom_id)

@router.get(
    "/classrooms/{classroom_id}",
    response_model=List[schemas.Assignment] # Define a simple Assignment schema in schemas.py
)
def get_assignments(
    classroom_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # Check if user is enrolled (student) or owns (teacher)
    if current_user.role == "student":
        if not crud.is_student_enrolled(db, current_user.id, classroom_id):
            raise HTTPException(status_code=403, detail="You are not enrolled in this class")
    elif current_user.role == "teacher":
        db_classroom = crud.get_classroom_by_id(db, classroom_id=classroom_id)
        if not db_classroom or db_classroom.teacher_id != current_user.id:
            raise HTTPException(status_code=403, detail="You do not own this classroom")
    
    return crud.get_assignments_for_classroom(db=db, classroom_id=classroom_id)

@router.get(
    "/{assignment_id}",
    response_model=schemas.AssignmentForStudent
)
def get_assignment_to_take(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_student_user)
):
    db_assignment = crud.get_assignment(db=db, assignment_id=assignment_id)
    if not db_assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
        
    # Check if student is enrolled in the assignment's class
    if not crud.is_student_enrolled(db, current_user.id, db_assignment.classroom_id):
        raise HTTPException(status_code=403, detail="You are not enrolled in this assignment's class")
    
    return db_assignment

@router.post(
    "/{assignment_id}/submit",
    response_model=schemas.SubmissionResult
)
def submit_assignment(
    assignment_id: int,
    submission: schemas.SubmissionCreate,
    background_tasks: BackgroundTasks, # Import from fastapi
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_student_user)
):
    db_assignment = crud.get_assignment(db=db, assignment_id=assignment_id)
    if not db_assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Check if student is enrolled
    if not crud.is_student_enrolled(db, current_user.id, db_assignment.classroom_id):
        raise HTTPException(status_code=403, detail="You are not enrolled in this assignment's class")

    # NEW: Implement Deadline Check
    from datetime import datetime, timezone
    if db_assignment.due_at and datetime.now(timezone.utc) > db_assignment.due_at:
        raise HTTPException(status_code=403, detail="The deadline for this assignment has passed")
    
    # 1. Create the submission record in the DB
    db_submission = crud.create_submission(
        db=db, 
        submission=submission, 
        assignment_id=assignment_id, 
        student_id=current_user.id
    )
    
    # 2. Add the grading job to the background
    background_tasks.add_task(grade_quiz, db, db_submission.id)
    
    # 3. Return the initial submission receipt immediately
    return db_submission

@router.get(
    "/submissions/{submission_id}/result",
    response_model=schemas.SubmissionResult
)
def get_submission_result(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Fetches the result of a submission after it has been graded."""
    db_submission = crud.get_submission(
        db=db, 
        submission_id=submission_id, 
        student_id=current_user.id
    )
    if current_user.role == 'student' and not db_submission:
        raise HTTPException(status_code=404, detail="Submission not found or does not belong to you")
    
    # TODO: Add logic for a teacher to view a student's submission
    
    if not db_submission:
        raise HTTPException(status_code=404, detail="Submission not found")
        
    return db_submission