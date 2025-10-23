from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
import pypdf
import io
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from .. import crud, models, schemas, auth
from ..database import get_db
from ..agents.quiz_grader import grade_quiz
from .. import tasks

# --- AI Rubric Parser ---
from ..agents.evaluation_chain import llm
from pydantic import BaseModel, Field


class ParsedCriterion(BaseModel):
    criterion: str = Field(description="The name of the criterion, e.g., 'Clarity'")
    max_points: int = Field(description="The maximum points for this criterion, e.g., 10")


class ParsedRubric(BaseModel):
    rubric: List[ParsedCriterion]


router = APIRouter(
    prefix="/api/coursework",
    tags=["coursework"]
)


# ============================================================
# Create Coursework
# ============================================================

@router.post(
    "/classrooms/{classroom_id}",
    response_model=schemas.CourseworkDisplay,
    status_code=status.HTTP_201_CREATED
)
def create_new_coursework(
    classroom_id: int,
    coursework: schemas.CourseworkCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_teacher_user)
):
    db_classroom = crud.get_classroom_by_id(db, classroom_id=classroom_id)
    if not db_classroom or db_classroom.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this classroom")

    if coursework.coursework_type == "quiz" and not coursework.questions:
        raise HTTPException(status_code=400, detail="Quizzes must have questions.")
    if coursework.coursework_type in ["essay", "assignment", "case_study"] and not coursework.rubric:
        raise HTTPException(status_code=400, detail="This coursework type must have a rubric.")

    return crud.create_coursework(db=db, coursework=coursework, classroom_id=classroom_id)


# ============================================================
# Get Coursework List
# ============================================================

@router.get(
    "/classrooms/{classroom_id}",
    response_model=List[schemas.CourseworkDisplay]
)
def get_courseworks(
    classroom_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if current_user.role == "student":
        if not crud.is_student_enrolled(db, current_user.id, classroom_id):
            raise HTTPException(status_code=403, detail="You are not enrolled in this class")
    elif current_user.role == "teacher":
        db_classroom = crud.get_classroom_by_id(db, classroom_id=classroom_id)
        if not db_classroom or db_classroom.teacher_id != current_user.id:
            raise HTTPException(status_code=403, detail="You do not own this classroom")

    return crud.get_courseworks_for_classroom(db=db, classroom_id=classroom_id)


# ============================================================
# Get Coursework to Take (with timezone fix)
# ============================================================

@router.get(
    "/{coursework_id}",
    response_model=schemas.CourseworkForStudent
)
def get_coursework_to_take(
    coursework_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_student_user)
):
    db_coursework = crud.get_coursework(db=db, coursework_id=coursework_id)
    if not db_coursework:
        raise HTTPException(status_code=404, detail="Coursework not found")

    if not crud.is_student_enrolled(db, current_user.id, db_coursework.classroom_id):
        raise HTTPException(status_code=403, detail="You are not enrolled in this coursework's class")

    now = datetime.now(timezone.utc)

    # --- FIX: Normalize DB datetimes to be timezone-aware ---
    available_from = (
        db_coursework.available_from.replace(tzinfo=timezone.utc)
        if db_coursework.available_from and db_coursework.available_from.tzinfo is None
        else db_coursework.available_from
    )

    due_at = (
        db_coursework.due_at.replace(tzinfo=timezone.utc)
        if db_coursework.due_at and db_coursework.due_at.tzinfo is None
        else db_coursework.due_at
    )

    if available_from and available_from > now:
        raise HTTPException(
            status_code=403,
            detail=f"This coursework is not available until {db_coursework.available_from}"
        )

    if due_at and now > due_at:
        raise HTTPException(status_code=403, detail="The deadline for this coursework has passed")

    existing_submission = crud.get_submission_by_student_and_coursework(db, current_user.id, coursework_id)
    if existing_submission:
        raise HTTPException(status_code=403, detail="You have already submitted this coursework.")

    return db_coursework


# ============================================================
# Submit Quiz
# ============================================================

@router.post(
    "/{coursework_id}/submit-quiz",
    response_model=schemas.SubmissionDetail
)
def submit_quiz(
    coursework_id: int,
    submission: schemas.QuizSubmissionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_student_user)
):
    db_coursework = crud.get_coursework(db=db, coursework_id=coursework_id)
    if not db_coursework or db_coursework.coursework_type != 'quiz':
        raise HTTPException(status_code=404, detail="Quiz coursework not found")
    if not crud.is_student_enrolled(db, current_user.id, db_coursework.classroom_id):
        raise HTTPException(status_code=403, detail="You are not enrolled in this class")

    now = datetime.now(timezone.utc)
    due_at = (
        db_coursework.due_at.replace(tzinfo=timezone.utc)
        if db_coursework.due_at and db_coursework.due_at.tzinfo is None
        else db_coursework.due_at
    )
    if due_at and now > due_at:
        raise HTTPException(status_code=403, detail="The deadline has passed")

    existing_submission = crud.get_submission_by_student_and_coursework(db, current_user.id, coursework_id)
    if existing_submission:
        raise HTTPException(status_code=403, detail="You have already submitted this quiz.")

    db_submission = crud.create_quiz_submission(
        db=db, submission=submission, coursework_id=coursework_id, student_id=current_user.id
    )
    background_tasks.add_task(grade_quiz, db, db_submission.id)

    return crud.get_submission_detail(db, db_submission.id, current_user.id)


# ============================================================
# Submit Essay / Assignment / Case Study
# ============================================================

@router.post(
    "/{coursework_id}/submit-essay",
    response_model=schemas.SubmissionDetail
)
def submit_essay(
    coursework_id: int,
    submission: schemas.EssaySubmissionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_student_user)
):
    db_coursework = crud.get_coursework(db=db, coursework_id=coursework_id)
    if not db_coursework or db_coursework.coursework_type not in ['essay', 'assignment', 'case_study']:
        raise HTTPException(status_code=404, detail="Coursework not found")
    if not crud.is_student_enrolled(db, current_user.id, db_coursework.classroom_id):
        raise HTTPException(status_code=403, detail="You are not enrolled in this class")

    now = datetime.now(timezone.utc)
    due_at = (
        db_coursework.due_at.replace(tzinfo=timezone.utc)
        if db_coursework.due_at and db_coursework.due_at.tzinfo is None
        else db_coursework.due_at
    )
    if due_at and now > due_at:
        raise HTTPException(status_code=403, detail="The deadline has passed")

    existing_submission = crud.get_submission_by_student_and_coursework(db, current_user.id, coursework_id)
    if existing_submission:
        raise HTTPException(status_code=403, detail="You have already submitted this coursework.")

    db_submission = crud.create_essay_submission(
        db=db, submission=submission, coursework_id=coursework_id, student_id=current_user.id
    )

    tasks.run_ai_evaluation.delay(db_submission.id)

    return crud.get_submission_detail(db, db_submission.id, current_user.id)


# ============================================================
# Get Submission Result
# ============================================================

@router.get(
    "/submissions/{submission_id}/result",
    response_model=schemas.SubmissionDetail
)
def get_submission_result(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if current_user.role == 'student':
        db_submission = crud.get_submission_detail(db, submission_id, current_user.id)
        if not db_submission:
            raise HTTPException(status_code=404, detail="Submission not found or does not belong to you")
        return db_submission
    elif current_user.role == 'teacher':
        db_submission = crud.get_submission_detail_for_teacher(db, submission_id)
        if not db_submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        return db_submission


# ============================================================
# Rubric Upload + Parse
# ============================================================

@router.post("/upload-rubric", response_model=schemas.RubricParseRequest)
async def upload_rubric_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_teacher_user)
):
    """Extracts text from an uploaded .txt or .pdf file."""
    content_type = file.content_type
    raw_text = ""
    try:
        contents = await file.read()
        if content_type == "text/plain":
            raw_text = contents.decode("utf-8")
        elif content_type == "application/pdf":
            with io.BytesIO(contents) as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    raw_text += page.extract_text() + "\n"
        else:
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload .txt or .pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse file: {e}")

    return schemas.RubricParseRequest(raw_text=raw_text)


@router.post("/parse-rubric", response_model=schemas.RubricParseResponse)
def parse_rubric_with_ai(
    request: schemas.RubricParseRequest,
    current_user: models.User = Depends(auth.get_teacher_user)
):
    """Uses an LLM to convert raw rubric text into structured JSON."""
    structured_rubric_parser = llm.with_structured_output(ParsedRubric)

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are an assistant that parses unstructured text into a JSON rubric. "
         "Identify each grading criterion and its maximum points. "
         "Example: 'Clarity (10 pts) and Grammar (5 pts)' should become "
         "[{{\"criterion\": \"Clarity\", \"max_points\": 10}}, "
         "{{\"criterion\": \"Grammar\", \"max_points\": 5}}]"),
        ("human", "Please parse the following rubric text:\n{raw_text}")
    ])

    chain = prompt | structured_rubric_parser

    try:
        result = chain.invoke({"raw_text": request.raw_text})
        return schemas.RubricParseResponse(rubric=result.rubric)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI failed to parse rubric: {e}")
