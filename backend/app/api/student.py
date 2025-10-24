from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, auth, crud
from ..database import get_db
from ..core.kg_graph import get_graph_db
from pydantic import BaseModel
from ..agents.dskg_agent import update_dskg_from_remedial
from datetime import datetime

router = APIRouter(
    prefix="/api/student",
    tags=["student"]
)

# --- DTOs for Remedial Quiz ---
class RemedialOptionDisplay(BaseModel):
    id: int
    option_text: str
    class Config:
        from_attributes = True

class RemedialQuestionDisplay(BaseModel):
    id: int
    question_text: str
    question_type: str
    options: List[RemedialOptionDisplay]
    class Config:
        from_attributes = True

class RemedialQuizDisplay(BaseModel):
    id: int
    concept: str
    created_at: datetime
    questions: List[RemedialQuestionDisplay]
    class Config:
        from_attributes = True

# --- DTO for DSKG ---
class DSKGNode(BaseModel):
    concept: str
    score: float
    last_assessed: datetime

class DSKGProfileResponse(BaseModel):
    student: schemas.UserDisplay
    dskg: List[DSKGNode]

# --- Helper function ---
def _get_dskg_data(student_id: int) -> List[DSKGNode]:
    neo_session = get_graph_db()
    try:
        result = neo_session.run(
            """
            MATCH (s:Student {student_id: $student_id})-[r:KNOWS]->(c:Concept)
            RETURN c.name AS concept, r.score AS score, r.last_assessed AS last_assessed
            ORDER BY r.score ASC
            """,
            student_id=student_id
        )
        nodes = [
            DSKGNode(
                concept=record["concept"],
                score=record["score"],
                last_assessed=datetime.fromisoformat(record["last_assessed"])
            )
            for record in result
        ]
        return nodes
    finally:
        neo_session.close()

# --- FIX: "ME" ROUTES MUST BE DEFINED BEFORE DYNAMIC {ID} ROUTES ---

@router.get("/me/remedial", response_model=List[RemedialQuizDisplay])
def get_my_remedial_quizzes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Fetches incomplete remedial quizzes for the logged-in student."""
    quizzes = db.query(models.RemedialQuiz).filter(
        models.RemedialQuiz.student_id == current_user.id,
        models.RemedialQuiz.is_completed == False
    ).all()
    return quizzes

@router.get("/me/dskg", response_model=List[DSKGNode])
def get_my_dskg(
    current_user: models.User = Depends(auth.get_current_active_user)
):
    return _get_dskg_data(current_user.id)

# --- END OF FIX ---

# --- Teacher-facing API ---
@router.get("/{student_id}/dskg", response_model=DSKGProfileResponse) # <-- FIX: Changed response model
def get_student_dskg(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_teacher_user)
):
    if not crud.is_teacher_and_student_in_same_class(db, current_user.id, student_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # --- FIX: Fetch student details ---
    student_user = db.query(models.User).get(student_id)
    if not student_user:
        raise HTTPException(status_code=404, detail="Student not found")
        
    dskg_data = _get_dskg_data(student_id)
    return DSKGProfileResponse(student=student_user, dskg=dskg_data)

# --- Remedial Submission API ---
class RemedialAnswer(BaseModel):
    question_id: int
    selected_option_id: int

class RemedialSubmission(BaseModel):
    answers: List[RemedialAnswer]

class RemedialResult(BaseModel):
    correct: int
    total: int
    score: float

@router.post("/remedial/{quiz_id}/submit", response_model=RemedialResult)
def submit_remedial_quiz(
    quiz_id: int,
    submission: RemedialSubmission,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    quiz = db.query(models.RemedialQuiz).filter(
        models.RemedialQuiz.id == quiz_id,
        models.RemedialQuiz.student_id == current_user.id
    ).first()
    
    if not quiz or quiz.is_completed:
        raise HTTPException(status_code=404, detail="Quiz not found or already completed")

    # Grade the quiz
    correct_count = 0
    question_scores = []
    answer_map = {ans.question_id: ans.selected_option_id for ans in submission.answers}
    
    for q in quiz.questions:
        is_correct = False
        correct_option_id = next(opt.id for opt in q.options if opt.is_correct)
        if answer_map.get(q.id) == correct_option_id:
            correct_count += 1
            is_correct = True
        question_scores.append(1.0 if is_correct else 0.0)
    
    score = correct_count / len(quiz.questions)
    
    # Update DSKG
    update_dskg_from_remedial(current_user.id, quiz.concept, question_scores)
    
    # Mark quiz as complete
    quiz.is_completed = True
    db.commit()
    
    return RemedialResult(correct=correct_count, total=len(quiz.questions), score=score)