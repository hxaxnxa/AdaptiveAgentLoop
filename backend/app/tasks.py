from .celery_worker import celery_app
from .database import SessionLocal
from . import models, schemas, crud
from .agents.evaluation_chain import evaluation_graph, GradedRubric
import logging

# Use logger for better output
logger = logging.getLogger(__name__)

@celery_app.task
def run_ai_evaluation(submission_id: int):
    logger.info(f"--- Starting AI Evaluation for Submission {submission_id} ---")
    
    db = SessionLocal()
    try:
        submission = db.query(models.Submission).get(submission_id)
        if not submission:
            logger.error(f"Error: Submission {submission_id} not found.")
            return

        # --- UPDATED to use coursework_id ---
        coursework = db.query(models.Coursework).get(submission.coursework_id)
        if not coursework or not coursework.rubric:
            logger.error(f"Error: Coursework {coursework.id} or rubric not found.")
            submission.status = "ERROR"
            db.commit()
            return
            
        # --- THE CRITICAL FIX (Req #5) ---
        submission_text_content = submission.submission_text
        if not submission_text_content:
            logger.error(f"Error: Submission {submission_id} has no submission_text. Cannot grade.")
            submission.status = "ERROR"
            db.commit()
            return
            
        submission.status = "GRADING"
        db.commit()

        rubric_schema = [schemas.RubricCriterion(**item) for item in coursework.rubric]
        
        inputs = {
            "submission_text": submission_text_content, # --- RENAMED ---
            "rubric": rubric_schema
        }
        
        # Run the agent graph
        result_state = evaluation_graph.invoke(inputs)
        ai_result: GradedRubric = result_state.get("ai_feedback")

        if ai_result is None:
            logger.error(f"AI chain returned None for submission {submission_id}.")
            raise Exception("AI evaluation failed to return data.")

        # --- Save results ---
        # ai_result is a Pydantic model (GradedRubric)
        submission.ai_feedback = [item.dict() for item in ai_result.feedback]
        
        total_score = sum(item.score for item in ai_result.feedback)
        max_score = sum(item.max_points for item in rubric_schema)
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