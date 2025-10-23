from sqlalchemy.orm import Session
from .. import models

def grade_quiz(db: Session, submission_id: int):
    try:
        submission = db.query(models.Submission).get(submission_id)
        if not submission:
            print(f"Error: Submission {submission_id} not found.")
            return

        # --- UPDATED to use coursework_id ---
        coursework = db.query(models.Coursework).get(submission.coursework_id)
        
        total_questions = len(coursework.questions)
        if total_questions == 0:
            submission.score = 0.0
            submission.status = "GRADED" # Auto-graded
            db.commit()
            return
            
        correct_answers = 0
        
        for student_answer in submission.answers:
            for correct_question in coursework.questions:
                if correct_question.id == student_answer.question_id:
                    for correct_option in correct_question.options:
                        if correct_option.is_correct:
                            if student_answer.selected_option_id == correct_option.id:
                                correct_answers += 1
                            break 
                    break 

        submission.score = float(correct_answers) / float(total_questions)
        submission.status = "GRADED" # Auto-graded and viewable
        db.commit()
        print(f"Submission {submission_id} graded. Score: {submission.score}")
        
    except Exception as e:
        print(f"An error occurred while grading {submission_id}: {e}")
        db.rollback()
        # --- ADDED: Error status ---
        submission_to_fail = db.query(models.Submission).get(submission_id)
        if submission_to_fail:
            submission_to_fail.status = "ERROR"
            db.commit()