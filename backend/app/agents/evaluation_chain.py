import os
import json
import pypdf
import docx
import io
import requests # To download files
from typing import TypedDict, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from .. import schemas, models
from urllib.parse import urlparse
from ..core.storage import minio_client, MINIO_BUCKET # Import storage
import logging
from dotenv import load_dotenv
import os
load_dotenv() # loads variables from .env into environment
print(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

logger = logging.getLogger(__name__)

# --- Pydantic Models for AI Output ---
class GradedCriterion(BaseModel):
    criterion: str = Field(description="The name of the criterion being graded.")
    score: int = Field(description="The score given for this criterion (must be an integer).")
    max_points: int = Field(description="The maximum points for this criterion (must be an integer).")
    justification: str = Field(description="The reason for giving this score, citing examples from the text.")

class GradedRubric(BaseModel):
    feedback: List[GradedCriterion]

# --- LangGraph State (UPDATED) ---
class EvaluationState(TypedDict):
    submission_id: int
    submission_text: str # Extracted text
    rubric_text: str # Extracted rubric text
    ai_feedback: GradedRubric 

# --- Initialize the LLM ---
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0)
structured_llm = llm.with_structured_output(GradedRubric)

# --- NEW: Helper function to get text from storage ---
def get_text_from_url(object_name: str) -> str:
    """Fetches a file from a MinIO object KEY and extracts text."""
    if minio_client is None:
        logger.error("MinIO client not initialized.")
        return "Error: MinIO client not available."

    try:
        # --- THIS IS THE FIX ---
        # No URL parsing. We are given the object_name (key) directly.
        response = minio_client.get_object(MINIO_BUCKET, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        file_bytes = io.BytesIO(data)

        if object_name.endswith(".pdf"):
            reader = pypdf.PdfReader(file_bytes)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        elif object_name.endswith(".docx"):
            doc = docx.Document(file_bytes)
            return "\n".join(para.text for para in doc.paragraphs)
        elif object_name.endswith(".txt"):
            return file_bytes.read().decode("utf-8")
        else:
            return "Unsupported file type."

    except Exception as e:
        logger.error(f"Failed to get text from MinIO object {object_name}: {e}")
        return "Error: Could not read file."
    
# --- Define Agent Nodes (UPDATED for Req #1) ---
def rubric_grader_node(state: EvaluationState):
    logger.info("--- [AI] Running Rubric Grader Node ---")
    
    submission_text = state["submission_text"]
    rubric_text = state["rubric_text"]
    
    if not submission_text or submission_text.startswith("Error:"):
        logger.error("Submission text is missing or unreadable.")
        return {"ai_feedback": None}
    if not rubric_text or rubric_text.startswith("Error:"):
        logger.error("Rubric text is missing or unreadable.")
        return {"ai_feedback": None}

    # --- THE NEW PROMPT (Req #1) ---
    prompt = ChatPromptTemplate.from_messages([
        ("system", 
         "You are an expert, fair, and objective teaching assistant. "
         "Your job is to grade a student's submission *strictly* based on the provided rubric. "
         "Read the rubric carefully to understand the criteria and performance levels. "
         "Then, read the student's submission. "
         "For each criterion in the rubric, provide a score and a detailed justification, citing examples from the submission. "
         "You MUST output a JSON object containing a list of your grades for *all* criteria."),
        ("human", 
         "--- GRADING RUBRIC ---\n{rubric}\n\n"
         "--- STUDENT SUBMISSION ---\n{submission}\n\n"
         "Please grade the submission based on the rubric and provide your feedback in the required JSON format.")
    ])
    
    chain = prompt | structured_llm
    
    try:
        ai_result = chain.invoke({
            "submission": submission_text,
            "rubric": rubric_text
        })
        logger.info(f"--- [AI] Result: {ai_result} ---")
        return {"ai_feedback": ai_result}
    except Exception as e:
        logger.error(f"--- [AI ERROR] Chain failed: {e} ---", exc_info=True)
        return {"ai_feedback": None}

# --- Build the Graph ---
builder = StateGraph(EvaluationState)
builder.add_node("rubric_grader", rubric_grader_node)
builder.set_entry_point("rubric_grader")
builder.add_edge("rubric_grader", END)
evaluation_graph = builder.compile()