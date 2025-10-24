from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import crud, models, schemas, auth
from ..database import get_db
from pydantic import BaseModel
from typing import Optional

# Create a new "router". This is like a mini-FastAPI app.
router = APIRouter(
    prefix="/api/classrooms",  # All routes in this file will start with /api/classrooms
    tags=["classrooms"]        # This is for the auto-generated docs
)

@router.post("/", response_model=schemas.ClassroomDisplay, status_code=status.HTTP_201_CREATED)
def create_new_classroom(
    classroom: schemas.ClassroomCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_teacher_user) # CHANGED
):
    # (The dependency already checks for teacher role and approval)
    return crud.create_classroom(db=db, classroom=classroom, teacher_id=current_user.id)

@router.post("/join", status_code=status.HTTP_201_CREATED)
def join_a_classroom(
    join_request: schemas.JoinRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_student_user)
):
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
    
# ---  Get Students in Classroom ---
@router.get("/{classroom_id}/students", response_model=List[schemas.UserDisplay])
def get_students_in_classroom(
    classroom_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_teacher_user) # Teacher only
):
    # Check if teacher owns this classroom
    db_classroom = crud.get_classroom_by_id(db, classroom_id=classroom_id)
    if not db_classroom or db_classroom.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this classroom")
    
    return crud.get_students_in_classroom(db, classroom_id=classroom_id)

# ---  Remove Student ---
@router.delete("/{classroom_id}/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_student(
    classroom_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_teacher_user) # Teacher only
):
    # Check if teacher owns this classroom
    db_classroom = crud.get_classroom_by_id(db, classroom_id=classroom_id)
    if not db_classroom or db_classroom.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this classroom")
    
    crud.remove_student_from_classroom(db, student_id=student_id, classroom_id=classroom_id)
    return {"message": "Student removed successfully"}

# --- DTOs for Gradebook ---
class GradebookScore(BaseModel):
    coursework_id: int
    final_score: Optional[float] = None

class GradebookStudentRow(BaseModel):
    student: schemas.UserDisplay
    scores: dict[int, GradebookScore] # { coursework_id: score_object }

class GradebookResponse(BaseModel):
    courseworks: List[schemas.CourseworkDisplay]
    students: List[GradebookStudentRow]
    class Config:
        from_attributes = True

@router.get("/{classroom_id}/gradebook", response_model=GradebookResponse)
def get_classroom_gradebook(
    classroom_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_teacher_user)
):
    # (Add your logic to verify teacher owns this classroom)
    if not crud.get_classroom_by_id(db, classroom_id).teacher_id == current_user.id:
         raise HTTPException(status_code=403, detail="Not authorized")
         
    data = crud.get_gradebook_data(db, classroom_id)
    return data

class GradeDistribution(BaseModel):
    A: int = 0
    B: int = 0
    C: int = 0
    D: int = 0
    F: int = 0

class CourseworkAnalytics(BaseModel):
    coursework_id: int
    coursework_name: str
    class_average: Optional[float] = None
    highest_score: Optional[float] = None
    lowest_score: Optional[float] = None
    submission_rate: str
    grade_distribution: GradeDistribution

@router.get("/{classroom_id}/analytics", response_model=List[CourseworkAnalytics])
def get_classroom_analytics(
    classroom_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_teacher_user)
):
    # (Add your logic to verify teacher owns this classroom)
    if not crud.get_classroom_by_id(db, classroom_id).teacher_id == current_user.id:
         raise HTTPException(status_code=403, detail="Not authorized")
         
    return crud.get_class_analytics(db, classroom_id)