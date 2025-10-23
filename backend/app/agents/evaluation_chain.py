import os
import json
from typing import TypedDict, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from .. import schemas
from dotenv import load_dotenv
import os
load_dotenv() # loads variables from .env into environment
print(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

# --- Pydantic Models for AI Output (from your debug log) ---
class GradedCriterion(BaseModel):
    criterion: str = Field(description="The name of the criterion being graded.")
    score: int = Field(description="The score given for this criterion.")
    justification: str = Field(description="The reason for giving this score.")

class GradedRubric(BaseModel):
    feedback: List[GradedCriterion]

# --- LangGraph State (RENAMED) ---
class EvaluationState(TypedDict):
    submission_text: str # --- RENAMED: submission_content -> submission_text ---
    rubric: List[schemas.RubricCriterion]
    ai_feedback: GradedRubric 

# --- Initialize the LLM ---
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0)
structured_llm = llm.with_structured_output(GradedRubric)

# --- Define Agent Nodes ---
def rubric_grader_node(state: EvaluationState):
    print("\n=== [DEBUG] Running Rubric Grader Node ===", flush=True)
    
    # --- RENAMED: submission_content -> submission_text ---
    submission = state["submission_text"] 
    rubric = state["rubric"]
    
    # --- ADDED: None guard (from your debug log) ---
    if submission is None:
        print("⚠️ Submission content is None! Cannot grade.", flush=True)
        return {"ai_feedback": None} # This will cause an error, but we'll catch it

    rubric_str = "\n".join(
        f"- {item.criterion} (Max Points: {item.max_points})" for item in rubric
    )

    print("=== [DEBUG] Rubric Input ===", flush=True)
    print(rubric_str, flush=True)
    print("=== [DEBUG] Submission Content (first 400 chars) ===", flush=True)
    print(submission[:400], flush=True)

    prompt = ChatPromptTemplate.from_messages([
        ("system", 
         "You are a fair and strict teaching assistant. Your job is to grade a student's submission "
         "based *only* on the provided rubric. For each criterion in the rubric, you must provide "
         "a score and a 2-sentence justification. Adhere strictly to the max points for each criterion."),
        ("human", 
         "Please grade the following submission:\n"
         "--- SUBMISSION ---\n{submission}\n"
         "--- RUBRIC ---\n{rubric}\n"
         "Provide your feedback in the required JSON format.")
    ])
    
    chain = prompt | structured_llm
    
    try:
        ai_result = chain.invoke({
            "submission": submission,
            "rubric": rubric_str
        })
        print("=== [DEBUG] AI Result ===", flush=True)
        print(ai_result, flush=True)
        return {"ai_feedback": ai_result}
    except Exception as e:
        print(f"--- [ERROR] AI evaluation chain failed: {e} ---", flush=True)
        # Return a valid-structured error or raise it
        return {"ai_feedback": None} # Let the task handler deal with this

# --- Build the Graph ---
builder = StateGraph(EvaluationState)
builder.add_node("rubric_grader", rubric_grader_node)
builder.set_entry_point("rubric_grader")
builder.add_edge("rubric_grader", END)

evaluation_graph = builder.compile()