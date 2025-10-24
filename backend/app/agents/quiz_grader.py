from sqlalchemy.orm import Session, joinedload
from .. import models
import logging

logger = logging.getLogger(__name__)

def grade_quiz(db: Session, submission_id: int):
    try:
        submission = db.query(models.Submission).get(submission_id)
        if not submission:
            logger.error(f"Error: Submission {submission_id} not found.")
            return

        coursework = db.query(models.Coursework).options(
            joinedload(models.Coursework.questions).joinedload(models.Question.options)
        ).get(submission.coursework_id)
        
        total_possible_score = 0
        achieved_score = 0
        
        # Build an answer key from the coursework
        answer_key = {}
        for q in coursework.questions:
            total_possible_score += q.score
            answer_key[q.id] = {
                "type": q.question_type,
                "score": q.score,
                "correct_options": {opt.id for opt in q.options if opt.is_correct}
            }
        
        if total_possible_score == 0:
            submission.score = 1.0 # Or 0.0, policy decision
            submission.status = "GRADED"
            db.commit()
            return

        # --- NEW SCORING LOGIC ---
        for student_answer in submission.answers:
            q_id = student_answer.question_id
            if q_id not in answer_key:
                continue
            
            key = answer_key[q_id]
            student_options = set(student_answer.selected_option_ids)
            
            if key["type"] == "multiple_choice":
                # Correct if the single selected option is in the correct set
                if len(student_options) == 1 and student_options == key["correct_options"]:
                    achieved_score += key["score"]
            
            elif key["type"] == "multiple_response":
                # --- BUG FIX: Correct only if sets match *perfectly* ---
                if student_options == key["correct_options"]:
                    achieved_score += key["score"]
                # (You could also add partial credit logic here)

        # 7. Calculate and save the score
        submission.score = float(achieved_score) / float(total_possible_score) if total_possible_score > 0 else 1.0
        submission.status = "PENDING_REVIEW"
        db.commit()
        logger.info(f"Submission {submission_id} auto-graded. Score: {achieved_score}/{total_possible_score}. status: PENDING_REVIEW")
        
    except Exception as e:
        logger.error(f"An error occurred while grading {submission_id}: {e}", exc_info=True)
        db.rollback()
        submission_to_fail = db.query(models.Submission).get(submission_id)
        if submission_to_fail:
            submission_to_fail.status = "ERROR"
            db.commit()