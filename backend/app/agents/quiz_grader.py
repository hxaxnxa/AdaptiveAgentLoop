from sqlalchemy.orm import Session
from .. import models

def grade_quiz(db: Session, submission_id: int):
    """
    Grades a quiz submission.
    This function is run in the background.
    """
    try:
        # 1. Get the submission and its answers
        submission = db.query(models.Submission).get(submission_id)
        if not submission:
            print(f"Error: Submission {submission_id} not found.")
            return

        # 2. Get the answer key from the original assignment
        # We fetch the questions and their correct options
        assignment = db.query(models.Assignment).get(submission.assignment_id)
        
        total_questions = len(assignment.questions)
        if total_questions == 0:
            submission.score = 0.0
            db.commit()
            return
            
        correct_answers = 0
        
        # 3. Loop through each answer the student gave
        for student_answer in submission.answers:
            # 4. Find the corresponding question in the answer key
            for correct_question in assignment.questions:
                if correct_question.id == student_answer.question_id:
                    # 5. Find the correct option for that question
                    for correct_option in correct_question.options:
                        if correct_option.is_correct:
                            # 6. Check if the student's selected option matches
                            if student_answer.selected_option_id == correct_option.id:
                                correct_answers += 1
                            break # Found correct option, move to next student answer
                    break # Found correct question, move to next student answer

        # 7. Calculate and save the score
        submission.score = float(correct_answers) / float(total_questions)
        db.commit()
        print(f"Submission {submission_id} graded. Score: {submission.score}")
        
    except Exception as e:
        print(f"An error occurred while grading {submission_id}: {e}")
        db.rollback() # Rollback in case of error