from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import Form, Body
from datetime import datetime, timezone, timedelta
import pypdf
import io
import docx
import uuid
import logging
import requests

from .. import crud, models, schemas, auth
from ..database import get_db
from ..agents.quiz_grader import grade_quiz
from .. import tasks
from ..core.storage import upload_file_to_storage, get_presigned_url_for_key

# --- AI Rubric Parser & Quiz Generator ---
from ..agents.evaluation_chain import llm, get_text_from_url
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate

def get_text_from_presigned_url(url: str) -> str:
    """PDF/text extractor from a presigned URL using requests."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "pdf" in content_type:
            with io.BytesIO(response.content) as f:
                reader = pypdf.PdfReader(f)
                return "\n".join(page.extract_text() or "" for page in reader.pages)
        elif "text" in content_type:
            return response.text
        else:
            return ""
    except Exception as e:
        raise RuntimeError(f"Failed to read material file from {url}: {e}")

# --- Models for AI structured outputs ---
class ParsedCriterion(BaseModel):
    criterion: str
    max_points: int

class ParsedRubric(BaseModel):
    rubric: List[ParsedCriterion]

class AIOption(BaseModel):
    option_text: str
    is_correct: bool

class AIQuestion(BaseModel):
    question_text: str
    question_type: str
    score: int
    options: List[AIOption]

class AIQuiz(BaseModel):
    questions: List[AIQuestion]

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/coursework",
    tags=["coursework"]
)

# ============================================================
# Helper: File Upload to MinIO
# ============================================================
def handle_file_upload(file: UploadFile, folder: str = "uploads") -> str:
    """Helper to upload a file to MinIO and return its KEY."""
    try:
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{folder}/{uuid.uuid4()}.{file_extension}"

        # --- CHANGED ---
        # This now returns the key (e.g., "uploads/...")
        file_key = upload_file_to_storage(
            file_obj=file.file,
            file_name=unique_filename,
            content_type=file.content_type
        )
        return file_key
    except Exception as e:
        logger.error(f"File upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"File upload failed: {e}")

# ============================================================
# Create Coursework
# ============================================================
@router.post("/classrooms/{classroom_id}", response_model=schemas.CourseworkDisplay)
async def create_new_coursework(
    classroom_id: int,
    coursework: schemas.CourseworkCreate = Body(...),
    ##rubric_file: Optional[UploadFile] = File(None),
    #material_files: List[UploadFile] = File([]),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_teacher_user)
):
    # Rubric upload
    #if rubric_file:
        #file_ext = rubric_file.filename.split(".")[-1].lower()
        #if file_ext not in ["pdf", "docx", "txt"]:
            #raise HTTPException(status_code=400, detail="Unsupported rubric file type")
        #coursework.rubric_file_url = handle_file_upload(rubric_file, "rubrics")
        #coursework.rubric = None

    # Material files upload
    #material_urls = [handle_file_upload(f, "materials") for f in material_files]
    #coursework.material_file_urls = material_urls

    return crud.create_coursework(db=db, coursework=coursework, classroom_id=classroom_id)

# ============================================================
# Upload File (General)
# ============================================================
@router.post("/upload-file", response_model=dict)
async def upload_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_teacher_user)
):
    # --- CHANGED ---
    # file_key now holds the permanent key
    file_key = handle_file_upload(file)
    # Return the key to the frontend.
    # The frontend must now store this key.
    return {"file_key": file_key}

# ============================================================
# AI Quiz Generation Endpoint
# ============================================================
@router.post("/generate-quiz-from-files", response_model=schemas.QuizGenerationResponse)
def generate_quiz_with_ai(
    request: schemas.QuizGenerationRequest,
    current_user: models.User = Depends(auth.get_teacher_user)
):
    ai_quiz_gen = llm.with_structured_output(AIQuiz)
    context_text = ""
    logger.info("--- [AI Quiz Gen] Starting... ---") # <-- New log

    # request.material_file_urls now contains a list of KEYS
    for key in request.material_file_urls:
        try:
            # --- THIS IS THE FIX ---
            # DO NOT generate a presigned URL.
            # Pass the KEY directly to the text extractor from evaluation_chain
            # which correctly uses the minio_client.
            logger.info(f"--- [AI Quiz Gen] Extracting text from key: {key} ---") # <-- New log
            
            # This function is imported at the top of coursework.py
            # from ..agents.evaluation_chain
            context_text += get_text_from_url(key) + "\n\n"
            # --- END OF FIX ---
            
        except Exception as e:
            # This log will now show up if text extraction fails
            logger.warning(f"--- [AI Quiz Gen] Could not read material file {key}: {e} ---", exc_info=True)

    if not context_text.strip():
        logger.warning("--- [AI Quiz Gen] Context text is empty. Aborting. ---") # <-- New log
        raise HTTPException(status_code=400, detail="Could not extract text from any provided material files.")

    logger.info("--- [AI Quiz Gen] Context extracted. Generating prompt... ---") # <-- New log
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a quiz generation expert. Create exactly {num_questions} questions "
         "based *only* on the provided context material. The questions should match {difficulty} difficulty. "
         "Include a mix of multiple-choice (one correct answer) and multiple-response (select all that apply) questions. "
         "Assign 1 point to easy, 2 to medium, 3 to hard. Provide 4 options for each question."),
        ("human",
         "--- CONTEXT MATERIAL ---\n{context}\n\n"
         "Please generate the quiz based *only* on the context above in the required JSON format.")
    ])

    chain = prompt | ai_quiz_gen

    try:
        logger.info("--- [AI Quiz Gen] Invoking AI model... ---") # <-- New log
        result = chain.invoke({
            "num_questions": request.num_questions,
            "difficulty": request.difficulty,
            "context": context_text[:10000]
        })
        logger.info("--- [AI Quiz Gen] AI model returned. Converting questions... ---") # <-- New log
        
        questions_converted = []
        for q in result.questions:
            questions_converted.append(
                schemas.QuestionCreate(
                    question_text=q.question_text,
                    question_type=q.question_type,
                    score=q.score,
                    options=[
                        schemas.OptionCreate(
                            option_text=o.option_text,
                            is_correct=o.is_correct
                        ) for o in q.options
                    ]
                )
            )

        return schemas.QuizGenerationResponse(questions=questions_converted)
    except Exception as e:
        logger.error(f"AI Quiz Gen failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI failed to generate quiz: {e}")

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
    db_coursework = crud.get_coursework_with_details(db=db, coursework_id=coursework_id)
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
        raise HTTPException(status_code=409, detail="You have already submitted this coursework.", headers={"X-Submission-ID": str(existing_submission.id)})

    if db_coursework.rubric_file_url:
        try:
            # Replace the key with a fresh, 1-hour URL
            db_coursework.rubric_file_url = get_presigned_url_for_key(
                db_coursework.rubric_file_url
            )
        except Exception as e:
            logger.error(f"Failed to generate URL for rubric key: {e}")
            db_coursework.rubric_file_url = None # Send null if URL gen fails

    # Do the same for material files (if you show them to students)
    if db_coursework.material_file_urls:
        fresh_urls = []
        for key in db_coursework.material_file_urls:
            try:
                fresh_urls.append(get_presigned_url_for_key(key))
            except Exception:
                pass # Skip file if URL gen fails
        db_coursework.material_file_urls = fresh_urls

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
    db_coursework = crud.get_coursework_with_details(db=db, coursework_id=coursework_id)
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
    tasks.run_quiz_grading.delay(db_submission.id)

    return crud.get_submission_detail(db, db_submission.id)


# ============================================================
# Submit Essay / Assignment / Case Study
# ============================================================
def handle_file_upload_from_bytes(
    file_obj: io.BytesIO, 
    filename: str, 
    content_type: str, 
    folder: str = "uploads"
) -> str:
    """Helper to upload a file-like object (BytesIO) to MinIO and return its KEY."""
    try:
        file_extension = filename.split(".")[-1]
        unique_filename = f"{folder}/{uuid.uuid4()}.{file_extension}"

        file_key = upload_file_to_storage(
            file_obj=file_obj,
            file_name=unique_filename,
            content_type=content_type
        )
        return file_key
    except Exception as e:
        logger.error(f"File upload from bytes failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"File upload failed: {e}")
    

@router.post(
    "/{coursework_id}/submit-file",
    response_model=schemas.SubmissionDetail
)
async def submit_file(
    coursework_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_student_user)
):
    db_coursework = crud.get_coursework_with_details(db=db, coursework_id=coursework_id)
    if not db_coursework or db_coursework.coursework_type not in ['essay', 'assignment', 'case_study']:
        raise HTTPException(status_code=404, detail="Coursework not found")
    if not crud.is_student_enrolled(db, current_user.id, db_coursework.classroom_id):
        raise HTTPException(status_code=403, detail="You are not enrolled in this class")

    # --- Deadline and Existing Submission Checks ---
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
    
    # --- ROBUST FILE HANDLING FIX ---
    # 1. Read the file ONCE asynchronously
    try:
        file_contents = await file.read()
    except Exception as e:
        logger.error(f"Failed to read file stream: {e}")
        raise HTTPException(status_code=500, detail="Failed to read file.")
    
    # 2. Extract text using a *new* in-memory buffer
    text_content = ""
    filename = file.filename.lower()
    try:
        if filename.endswith(".pdf"):
            reader = pypdf.PdfReader(io.BytesIO(file_contents))
            text_content = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif filename.endswith(".docx"):
            doc = docx.Document(io.BytesIO(file_contents))
            text_content = "\n".join(para.text for para in doc.paragraphs)
        elif filename.endswith(".txt"):
            text_content = file_contents.decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to extract text during submission: {e}")
        # We can still proceed; the Celery task will try again
    
    # 3. Upload the file using a *new* in-memory buffer
    # This avoids all file-pointer/seek issues.
    file_key = handle_file_upload_from_bytes(
        io.BytesIO(file_contents), 
        file.filename, 
        file.content_type
    )
    # --- END OF FIX ---

    submission_schema = schemas.EssaySubmissionCreate(
        submission_text=text_content,
        submission_file_url=file_key
    )

    db_submission = crud.create_essay_submission(
        db=db, submission=submission_schema, coursework_id=coursework_id, student_id=current_user.id
    )

    # Trigger the AI evaluation (which will also extract text if it's missing)
    tasks.run_ai_evaluation.delay(db_submission.id)

    return crud.get_submission_detail(db, db_submission.id)


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
    db_submission = crud.get_submission_detail(db, submission_id)
    if not db_submission:
        raise HTTPException(status_code=404, detail="Submission not found")
        
    # Check permissions
    if current_user.role == 'student' and db_submission.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    elif current_user.role == 'teacher' and db_submission.coursework.classroom.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if db_submission and db_submission.submission_file_url:
        try:
            # Replace the stored key with a fresh URL
            db_submission.submission_file_url = get_presigned_url_for_key(
                db_submission.submission_file_url
            )
        except Exception as e:
            logger.error(f"Failed to generate URL for submission key: {e}")
            db_submission.submission_file_url = None
       
    # --- NEW: Hide results if not GRADED for student (Req #2) ---
    if current_user.role == 'student' and db_submission.status != 'GRADED':
        # --- FIX: Manually convert nested ORM models to Pydantic models ---
        coursework_data = schemas.CourseworkDisplay.model_validate(db_submission.coursework)
        student_data = schemas.UserDisplay.model_validate(db_submission.student)
        
        # Return limited info, hide score/feedback
        return schemas.SubmissionDetail(
            id=db_submission.id, 
            submitted_at=db_submission.submitted_at, 
            status=db_submission.status, 
            coursework_id=db_submission.coursework_id,
            student_id=db_submission.student_id, 
            coursework=coursework_data,
            student=student_data,
            
            # --- ADD THIS LINE ---
            submission_file_url=db_submission.submission_file_url
            
        )
        
    return db_submission

@router.get("/{coursework_id}/submissions", response_model=List[schemas.SubmissionDetail])
def get_all_submissions(
    coursework_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_teacher_user)
):
    # Check if teacher owns this class
    db_coursework = crud.get_coursework_with_details(db, coursework_id)
    if not db_coursework or db_coursework.classroom.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this coursework")
    
    return crud.get_submissions_for_coursework(db, coursework_id)
@router.patch("/submissions/{submission_id}/approve", response_model=schemas.SubmissionDetail)
def approve_submission(
    submission_id: int,
    approval_data: schemas.SubmissionApproval,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_teacher_user)
):
    db_submission = crud.get_submission_detail(db, submission_id)
    if not db_submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if db_submission.coursework.classroom.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    crud.approve_submission(db, submission_id, approval_data)
    
    # Return the updated submission
    return crud.get_submission_detail(db, submission_id)

@router.patch("/questions/{question_id}/options/{option_id}", status_code=status.HTTP_204_NO_CONTENT)
def update_option(
    question_id: int,
    option_id: int,
    is_correct: bool, # Send in request body e.g., {"is_correct": true}
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_teacher_user)
):
    db_question = crud.get_question_with_options(db, question_id)
    if not db_question: raise HTTPException(status_code=404)
    # Check teacher owns coursework
    if db_question.coursework.classroom.teacher_id != current_user.id: raise HTTPException(status_code=403)
    
    # Update the specific option
    crud.update_option_correctness(db, option_id, is_correct)
    
    # If correctness changed, trigger regrading
    tasks.regrade_quiz_submissions_for_question.delay(question_id)
    
    return {"message": "Option updated and regrading triggered."}
# ============================================================
# Rubric Upload + Parse
# ============================================================

@router.post("/upload-rubric", response_model=schemas.RubricParseRequest)
async def upload_rubric_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_teacher_user)
):
    """Extract text from PDF/DOCX/TXT rubric."""
    raw_text = ""
    try:
        contents = await file.read()
        ext = file.filename.split(".")[-1].lower()

        if ext == "txt":
            raw_text = contents.decode("utf-8")
        elif ext == "pdf":
            with io.BytesIO(contents) as f:
                reader = pypdf.PdfReader(f)
                raw_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif ext == "docx":
            with io.BytesIO(contents) as f:
                doc = docx.Document(f)
                raw_text = "\n".join(p.text for p in doc.paragraphs)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Upload PDF, DOCX, or TXT.")
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
