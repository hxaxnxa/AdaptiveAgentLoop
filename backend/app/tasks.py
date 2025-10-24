from .celery_worker import celery_app
from .database import SessionLocal
from . import models, schemas, crud
from .agents.evaluation_chain import evaluation_graph, get_text_from_url
import logging
import json
from .agents.quiz_grader import grade_quiz
from .agents.dskg_agent import update_dskg_from_submission
from .agents.planner_agent import run_planner
logger = logging.getLogger(__name__)

# --- Task 1: Quiz Grader (No change in task logic) ---
from .agents.quiz_grader import grade_quiz
@celery_app.task
def run_quiz_grading(submission_id: int):
    logger.info(f"--- Starting Quiz Grading for Submission {submission_id} ---")
    db = SessionLocal()
    try:
        grade_quiz(db, submission_id)
    finally:
        db.close()

# --- Task 2: Essay/File Grader (UPDATED) ---
@celery_app.task
def run_ai_evaluation(submission_id: int):
    logger.info(f"--- Starting AI Evaluation for Submission {submission_id} ---")
    
    db = SessionLocal()
    try:
        submission = db.query(models.Submission).get(submission_id)
        if not submission:
            logger.error(f"Error: Submission {submission_id} not found.")
            return

        coursework = db.query(models.Coursework).get(submission.coursework_id)
        
        # --- 1. Get Rubric Text ---
        rubric_text = ""
        if coursework.rubric_file_url:
            logger.info(f"Fetching rubric from URL: {coursework.rubric_file_url}")
            rubric_text = get_text_from_url(coursework.rubric_file_url)
        elif coursework.rubric:
            logger.info("Using JSON rubric.")
            rubric_text = json.dumps(coursework.rubric)
        else:
            logger.error(f"Error: Coursework {coursework.id} has no rubric.")
            submission.status = "ERROR"; db.commit(); return

        # --- 2. Get Submission Text (from file or text) ---
        submission_text_content = ""
        if submission.submission_file_url:
            logger.info(f"Fetching submission from URL: {submission.submission_file_url}")
            submission_text_content = get_text_from_url(submission.submission_file_url)
            # Save extracted text for future viewing
            submission.submission_text = submission_text_content
        elif submission.submission_text:
            logger.info("Using raw text submission.")
            submission_text_content = submission.submission_text
        else:
            logger.error(f"Error: Submission {submission_id} has no text or file.")
            submission.status = "ERROR"; db.commit(); return
            
        submission.status = "GRADING"
        db.commit()
        
        # --- 3. Run the AI Agent ---
        inputs = {
            "submission_id": submission_id,
            "submission_text": submission_text_content,
            "rubric_text": rubric_text
        }
        
        result_state = evaluation_graph.invoke(inputs)
        ai_result = result_state.get("ai_feedback")

        if ai_result is None:
            raise Exception("AI evaluation failed to return data.")

        # --- 4. Save results ---
        total_score = 0
        max_score = 0
        feedback_list = []
        
        for item in ai_result.feedback:
            feedback_list.append(item.dict())
            total_score += item.score
            max_score += item.max_points

        submission.ai_feedback = feedback_list
        submission.score = float(total_score) / float(max_score) if max_score > 0 else 0.0
        submission.status = "PENDING_REVIEW"
        db.commit()
        
        logger.info(f"--- Finished AI Evaluation for Submission {submission_id}. Score: {submission.score} ---")
        
    except Exception as e:
        logger.error(f"--- ERROR during evaluation for {submission_id}: {e} ---", exc_info=True)
        db.rollback()
        submission_to_fail = db.query(models.Submission).get(submission_id)
        if submission_to_fail:
            submission_to_fail.status = "ERROR"
            db.commit()
    finally:
        db.close()

@celery_app.task
def regrade_quiz_submissions_for_question(question_id: int):
    logger.info(f"--- Starting Regrade for Question {question_id} ---")
    db = SessionLocal()
    try:
        # Find all submissions affected by this question change
        submissions_to_regrade = crud.get_submissions_for_question(db, question_id)
        
        submission_ids = [sub.id for sub in submissions_to_regrade]
        logger.info(f"Found {len(submission_ids)} submissions to regrade.")
        
        # Trigger the original grading task for each one
        for sub_id in submission_ids:
            run_quiz_grading.delay(sub_id)
            
    except Exception as e:
        logger.error(f"Error during regrade trigger for Q{question_id}: {e}", exc_info=True)
    finally:
        db.close()

@celery_app.task
def run_dskg_update(submission_id: int):
    logger.info(f"--- Task: Starting DSKG Update for {submission_id} ---")
    db = SessionLocal()
    try:
        submission = crud.get_submission_detail(db, submission_id)
        if not submission:
            logger.error(f"DSKG update failed: No submission {submission_id}")
            return
            
        update_dskg_from_submission(db, submission_id)
        
        # --- CHAIN THE NEXT TASK ---
        # After updating memory, run the planner
        task_run_planner.delay(submission.student_id)
        
    except Exception as e:
        logger.error(f"Error in DSKG update task: {e}", exc_info=True)
    finally:
        db.close()

@celery_app.task
def task_run_planner(student_id: int):
    """Celery task wrapper for the planner agent."""
    logger.info(f"--- Task: Starting Planner for Student {student_id} ---")
    db = SessionLocal()
    try:
        # Call the *actual* planner function from planner_agent.py
        run_planner(db, student_id)
    except Exception as e:
        logger.error(f"Error in planner task: {e}", exc_info=True)
    finally:
        db.close()