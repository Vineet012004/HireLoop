"""FastAPI routes — all HTTP endpoints for the hiring panel backend."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.db import get_db
from database.models import Report
from resume.parser import parse_resume
from resume.analyzer import analyze_resume
from services import interview_service

router = APIRouter(prefix="/api/v1")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class StartSessionRequest(BaseModel):
    candidate_id: int
    agent_type: str  # hr | technical | manager


class AnswerRequest(BaseModel):
    answer: str


# ---------------------------------------------------------------------------
# Resume endpoints
# ---------------------------------------------------------------------------

@router.post("/resume/upload", summary="Upload and analyse a resume")
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a PDF, DOCX, or TXT resume.
    Returns parsed candidate info and a new candidate_id.
    """
    if file.content_type not in (
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    ):
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT files are supported.")

    file_bytes = await file.read()
    if len(file_bytes) > 5 * 1024 * 1024:  # 5 MB cap
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5 MB.")

    try:
        resume_text = parse_resume(file_bytes, file.filename or "resume.pdf")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    analysis = analyze_resume(resume_text)
    candidate = interview_service.create_candidate(db, analysis, resume_text, file.filename or "")

    return {
        "candidate_id": candidate.id,
        "analysis": analysis,
    }


# ---------------------------------------------------------------------------
# Interview session endpoints
# ---------------------------------------------------------------------------

@router.post("/sessions", summary="Create an interview session")
def create_session(payload: StartSessionRequest, db: Session = Depends(get_db)):
    """Create a new interview session for a candidate with the specified agent type."""
    candidate = interview_service.get_candidate(db, payload.candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    try:
        session = interview_service.create_session(db, payload.candidate_id, payload.agent_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"session_id": session.id, "agent_type": session.agent_type, "status": session.status}


@router.post("/sessions/{session_id}/start", summary="Start the interview (get opening message)")
def start_session(session_id: int, db: Session = Depends(get_db)):
    """Instantiates the AI agent and returns its opening greeting + first question."""
    try:
        opening = interview_service.start_session(db, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {"session_id": session_id, "message": opening}


@router.post("/sessions/{session_id}/answer", summary="Submit a candidate answer")
def submit_answer(session_id: int, payload: AnswerRequest, db: Session = Depends(get_db)):
    """Send the candidate's answer and receive the agent's next question."""
    if not payload.answer.strip():
        raise HTTPException(status_code=400, detail="Answer cannot be empty.")

    try:
        reply = interview_service.send_answer(db, session_id, payload.answer)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"session_id": session_id, "message": reply}


@router.post("/sessions/{session_id}/finish", summary="Finish interview and generate score report")
def finish_session(session_id: int, db: Session = Depends(get_db)):
    """Close the interview, score it, and return the full evaluation report."""
    try:
        scores = interview_service.finish_session(db, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"session_id": session_id, "report": scores}


@router.get("/sessions/{session_id}/transcript", summary="Get full interview transcript")
def get_transcript(session_id: int, db: Session = Depends(get_db)):
    messages = interview_service.get_session_transcript(db, session_id)
    return {"session_id": session_id, "transcript": messages}


# ---------------------------------------------------------------------------
# Report / recruiter endpoints
# ---------------------------------------------------------------------------

@router.get("/candidates/{candidate_id}/reports", summary="Get all reports for a candidate")
def get_candidate_reports(candidate_id: int, db: Session = Depends(get_db)):
    candidate = interview_service.get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    reports = db.query(Report).filter(Report.candidate_id == candidate_id).all()
    return {
        "candidate_id": candidate_id,
        "candidate_name": candidate.name,
        "reports": [
            {
                "report_id": r.id,
                "session_id": r.session_id,
                "overall_score": r.overall_score,
                "communication_score": r.communication_score,
                "technical_score": r.technical_score,
                "cultural_fit_score": r.cultural_fit_score,
                "recommendation": r.recommendation,
                "strengths": r.strengths,
                "weaknesses": r.weaknesses,
                "detailed_feedback": r.detailed_feedback,
                "created_at": str(r.created_at),
            }
            for r in reports
        ],
    }
