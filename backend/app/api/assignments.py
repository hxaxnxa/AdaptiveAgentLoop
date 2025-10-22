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
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Creates a new assignment (quiz) for a classroom. (Teacher only)"""
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can create assignments")
    
    # TODO: Check if teacher owns this classroom
    
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
    """Gets all assignments for a given classroom."""
    # TODO: Check if user is enrolled in or owns this classroom
    
    return crud.get_assignments_for_classroom(db=db, classroom_id=classroom_id)

@router.get(
    "/{assignment_id}",
    response_model=schemas.AssignmentForStudent
)
def get_assignment_to_take(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Gets a single assignment, formatted for a student to take."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can take assignments")
    
    # TODO: Check if student is enrolled in the assignment's classroom
    
    db_assignment = crud.get_assignment(db=db, assignment_id=assignment_id)
    if not db_assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
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
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Submits a student's answers for an assignment."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can submit assignments")
        
    # TODO: Check if student has already submitted
    
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
    if not db_submission:
        raise HTTPException(status_code=404, detail="Submission not found or does not belong to user")
    return db_submission