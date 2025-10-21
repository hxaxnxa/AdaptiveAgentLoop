from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Import all our modules
from .. import crud, models, schemas, auth
from ..database import get_db

# Create a new "router". This is like a mini-FastAPI app.
router = APIRouter(
    prefix="/api/classrooms",  # All routes in this file will start with /api/classrooms
    tags=["classrooms"]        # This is for the auto-generated docs
)

@router.post("/", response_model=schemas.ClassroomDisplay, status_code=status.HTTP_201_CREATED)
def create_new_classroom(
    classroom: schemas.ClassroomCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """
    Creates a new classroom. Only accessible by users with 'teacher' role.
    """
    # 1. Check if the user is a teacher
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create a classroom."
        )
    # 2. Create the classroom
    return crud.create_classroom(db=db, classroom=classroom, teacher_id=current_user.id)

@router.post("/join", status_code=status.HTTP_201_CREATED)
def join_a_classroom(
    join_request: schemas.JoinRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """
    Allows a student to join a classroom using an invite code.
    """
    # 1. Check if the user is a student
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can join classrooms."
        )
    
    # 2. Find the classroom by the invite code
    classroom = crud.get_classroom_by_invite_code(db, code=join_request.invite_code)
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found with this invite code."
        )
        
    # 3. Add the student to the classroom
    # (You might want to add a check here to prevent joining twice)
    crud.add_student_to_classroom(
        db=db, student_id=current_user.id, classroom_id=classroom.id
    )
    return {"message": f"Successfully joined classroom: {classroom.name}"}


@router.get("/", response_model=List[schemas.ClassroomDisplay | schemas.EnrolledClassroomDisplay])
def get_user_classrooms(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """
    Gets a list of classrooms.
    - If user is a teacher, returns classrooms they own.
    - If user is a student, returns classrooms they are enrolled in.
    """
    if current_user.role == "teacher":
        return crud.get_classrooms_by_teacher(db, teacher_id=current_user.id)
    elif current_user.role == "student":
        return crud.get_classrooms_by_student(db, student_id=current_user.id)
    else:
        return [] # Or raise an exception