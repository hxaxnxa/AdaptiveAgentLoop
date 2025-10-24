import logging
from neo4j import Session as Neo4jSession
from sqlalchemy.orm import Session as SqlSession, joinedload
from datetime import datetime, timezone
from .. import models
from ..core.kg_graph import get_graph_db
from typing import List
import json

logger = logging.getLogger(__name__)

def _write_knowledge_to_graph(
    tx: Neo4jSession, 
    student_id: int, 
    concept_name: str, 
    score: float
):
    """
    Private helper to write a single student-concept relationship to Neo4j.
    """
    history_entry_map = {
        "score": score,
        "date": datetime.now(timezone.utc).isoformat()
    }
    history_entry_str = json.dumps(history_entry_map)
    
    cypher_query = """
    MERGE (s:Student {student_id: $student_id})
    MERGE (c:Concept {name: $concept_name})
    MERGE (s)-[r:KNOWS]->(c)
    SET r.score = $score, 
        r.last_assessed = $timestamp, 
        r.history = COALESCE(r.history, []) + $history_entry
    """
    tx.run(
        cypher_query,
        student_id=student_id,
        concept_name=concept_name,
        score=score,
        timestamp=history_entry_map["date"], # Pass the same timestamp
        history_entry=history_entry_str      # Pass the JSON string
    )

def _write_remedial_knowledge_to_graph(
    tx: Neo4jSession, 
    student_id: int, 
    concept_name: str, 
    score: float
):
    """
    Writes remedial (practice) scores to the graph.
    It ONLY appends to history and does NOT update the main 'r.score'.
    """
    history_entry_map = {
        "score": score,
        "date": datetime.now(timezone.utc).isoformat(),
        "type": "remedial"
    }
    history_entry_str = json.dumps(history_entry_map)

    cypher_query = """
    MERGE (s:Student {student_id: $student_id})
    MERGE (c:Concept {name: $concept_name})
    MERGE (s)-[r:KNOWS]->(c)
    // We do NOT set r.score
    SET r.last_assessed = $timestamp, 
        r.history = COALESCE(r.history, []) + $history_entry
    """
    
    tx.run(
        cypher_query,
        student_id=student_id,
        concept_name=concept_name,
        score=score,
        # --- THIS WAS THE FIX: Removed extra text from this line ---
        timestamp=history_entry_map["date"], 
        history_entry=history_entry_str
    )

def update_dskg_from_submission(db: SqlSession, submission_id: int):
    """
    Main function to update the DSKG based on a graded submission.
    """
    logger.info(f"--- DSKG: Updating for submission {submission_id} ---")
    submission = db.query(models.Submission).options(
        joinedload(models.Submission.coursework),
        joinedload(models.Submission.answers).joinedload(models.SubmissionAnswer.question).joinedload(models.Question.options)
    ).get(submission_id)

    if not submission or submission.status != "GRADED":
        logger.warning(f"DSKG: Submission {submission_id} not found or not graded.")
        return

    student_id = submission.student_id
    coursework = submission.coursework
    concepts_to_update = {}  # { "concept_name": [list_of_scores] }

    if coursework.coursework_type == 'quiz':
        logger.info(f"DSKG: Processing quiz submission {submission_id}")
        for answer in submission.answers:
            question = answer.question
            if not question:
                continue

            correct_options = {opt.id for opt in question.options if opt.is_correct}
            student_options = set(answer.selected_option_ids or [])
            is_correct = (student_options == correct_options)
            question_score = 1.0 if is_correct else 0.0
            
            for concept in (question.concept_tags or []):
                concepts_to_update.setdefault(concept, []).append(question_score)
    else:
        logger.info(f"DSKG: Processing essay submission {submission_id}")
        for feedback_item in (submission.ai_feedback or []):
            concept = feedback_item.get('criterion')
            score_val = feedback_item.get('score')
            max_points = feedback_item.get('max_points')
            
            if concept and score_val is not None and max_points is not None and max_points > 0:
                score = float(score_val) / float(max_points)
                concepts_to_update.setdefault(concept, []).append(score)

    if not concepts_to_update:
        logger.info(f"DSKG: No concepts found for submission {submission_id}.")
        return

    neo_session = get_graph_db()
    with neo_session.begin_transaction() as tx:
        for concept, scores in concepts_to_update.items():
            avg_score = sum(scores) / len(scores)
            _write_knowledge_to_graph(tx, student_id, concept, avg_score)
            logger.info(f"DSKG: Wrote {student_id} -> {concept} @ {avg_score}")
    
    neo_session.close()
    logger.info(f"--- DSKG: Update complete for {submission_id} ---")

def update_dskg_from_remedial(
    student_id: int, 
    concept: str, 
    question_scores: List[float]
):
    """
    Updates DSKG from a remedial quiz.
    """
    logger.info(f"--- DSKG: Updating from remedial quiz for {student_id} ---")
    if not question_scores:
        return
        
    avg_score = sum(question_scores) / len(question_scores)
    
    neo_session = get_graph_db()
    with neo_session.begin_transaction() as tx:
        _write_remedial_knowledge_to_graph(tx, student_id, concept, avg_score)
        logger.info(f"DSKG: Wrote (remedial) {student_id} -> {concept} @ {avg_score}")
    neo_session.close()