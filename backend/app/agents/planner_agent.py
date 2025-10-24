import logging
from neo4j import Session as Neo4jSession
from sqlalchemy.orm import Session as SqlSession
from typing import List
from ..core.kg_graph import get_graph_db
from .. import models, crud
from .evaluation_chain import llm # Re-use your LLM
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# --- Re-use Pydantic models from coursework.py for AI output ---
class AIOption(BaseModel):
    option_text: str
    is_correct: bool

class AIQuestion(BaseModel):
    question_text: str
    question_type: str = "multiple_choice"
    options: List[AIOption]

class AIQuiz(BaseModel):
    questions: List[AIQuestion]

# --- TOOL 1: Get Weakest Concepts ---
def get_weakest_concepts(student_id: int) -> List[str]:
    logger.info(f"Planner: Finding weak concepts for {student_id}")
    neo_session = get_graph_db()
    try:
        result = neo_session.run(
            """
            MATCH (s:Student {student_id: $student_id})-[r:KNOWS]->(c:Concept)
            WHERE r.score < 0.7
            RETURN c.name AS concept
            ORDER BY r.score ASC
            LIMIT 3
            """,
            student_id=student_id
        )
        concepts = [record["concept"] for record in result]
        logger.info(f"Planner: Found weak concepts: {concepts}")
        return concepts
    finally:
        neo_session.close()

# --- TOOL 2: Generate Remedial Quiz ---
def generate_remedial_quiz(concept: str) -> AIQuiz:
    logger.info(f"Planner: Generating remedial quiz for '{concept}'")
    ai_quiz_gen = llm.with_structured_output(AIQuiz)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a helpful tutor. Create a 3-question multiple-choice quiz "
         "to help a student practice this single concept: {concept}. "
         "The questions should be clear and test fundamental understanding."),
        ("human", "Please generate the 3-question quiz for {concept}.")
    ])
    chain = prompt | ai_quiz_gen
    quiz_result = chain.invoke({"concept": concept})
    return quiz_result

def _save_remedial_quiz(db: SqlSession, student_id: int, concept: str, quiz_data: AIQuiz):
    """Saves the generated quiz to the PostgreSQL database."""
    
    # --- FIX: Use a single transaction ---
    try:
        # Create the main quiz entry
        db_remedial_quiz = models.RemedialQuiz(
            student_id=student_id,
            concept=concept
        )
        db.add(db_remedial_quiz)
        
        # We must flush to get the quiz ID before adding questions
        db.flush() 

        questions_to_add = []
        for q_in in quiz_data.questions:
            db_question = models.RemedialQuestion(
                quiz_id=db_remedial_quiz.id,
                question_text=q_in.question_text,
                question_type=q_in.question_type
            )
            
            # Create options for this question
            db_options = [
                models.RemedialOption(
                    question=db_question,
                    option_text=o_in.option_text,
                    is_correct=o_in.is_correct
                ) for o_in in q_in.options
            ]
            
            # Add the question and its options to the session
            questions_to_add.append(db_question)
            db.add_all(db_options)
        
        db.add_all(questions_to_add)
        
        # Commit everything at once
        db.commit()
        logger.info(f"Planner: Saved new remedial quiz {db_remedial_quiz.id} for student {student_id}")
    
    except Exception as e:
        logger.error(f"Planner: Failed to save remedial quiz. Rolling back. Error: {e}")
        db.rollback()
        raise
    # --- END OF FIX ---

# --- MAIN PLANNER FUNCTION ---
def run_planner(db: SqlSession, student_id: int):
    # 1. Check for existing *incomplete* quizzes
    existing = db.query(models.RemedialQuiz).filter(
        models.RemedialQuiz.student_id == student_id,
        models.RemedialQuiz.is_completed == False
    ).first()
    
    if existing:
        logger.info(f"Planner: Student {student_id} already has a pending quiz. Skipping.")
        return

    # 2. Get weakest concepts from DSKG (Neo4j)
    weak_concepts = get_weakest_concepts(student_id)
    if not weak_concepts:
        logger.info(f"Planner: No weak concepts for {student_id}. Good job!")
        return

    # 3. For the *weakest* concept, generate a quiz
    target_concept = weak_concepts[0]
    
    # 4. Generate quiz content (LLM)
    quiz_content = generate_remedial_quiz(target_concept)
    
    # 5. Save quiz to database (PostgreSQL)
    _save_remedial_quiz(db, student_id, target_concept, quiz_content)