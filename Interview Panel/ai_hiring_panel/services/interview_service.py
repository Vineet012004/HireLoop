"""
Interview service — orchestrates the full interview lifecycle.
Sits between the API layer and the agent/database layers.
"""
from datetime import datetime
from sqlalchemy.orm import Session

from agents.hr_agent import HRAgent
from agents.technical_agent import TechnicalAgent
from agents.manager_agent import ManagerAgent
from agents.scoring_agent import score_interview
from database.models import Candidate, InterviewSession, InterviewMessage, Report

AGENT_MAP = {
    "hr": HRAgent,
    "technical": TechnicalAgent,
    "manager": ManagerAgent,
}

# In-memory store for active agent instances keyed by session_id.
# For production, replace with Redis or a proper session store.
_active_agents: dict[int, object] = {}


# ---------------------------------------------------------------------------
# Candidate helpers
# ---------------------------------------------------------------------------

def create_candidate(db: Session, analysis: dict, resume_text: str, filename: str) -> Candidate:
    candidate = Candidate(
        name=analysis.get("name", "Unknown"),
        email=analysis.get("email", ""),
        resume_text=resume_text,
        resume_filename=filename,
        skills=analysis.get("skills", []),
        experience_years=analysis.get("experience_years", 0.0),
        job_role=analysis.get("job_role", ""),
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def get_candidate(db: Session, candidate_id: int) -> Candidate | None:
    return db.query(Candidate).filter(Candidate.id == candidate_id).first()


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def create_session(db: Session, candidate_id: int, agent_type: str) -> InterviewSession:
    if agent_type not in AGENT_MAP:
        raise ValueError(f"Unknown agent_type '{agent_type}'. Choose from: {list(AGENT_MAP)}")

    session = InterviewSession(
        candidate_id=candidate_id,
        agent_type=agent_type,
        status="pending",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def start_session(db: Session, session_id: int) -> str:
    """Instantiate the agent, save the opening message, return it."""
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise ValueError(f"Session {session_id} not found.")

    candidate = session.candidate
    analysis = {
        "name": candidate.name,
        "email": candidate.email,
        "job_role": candidate.job_role,
        "experience_years": candidate.experience_years,
        "skills": candidate.skills,
        "education": "",
        "summary": candidate.resume_text[:400] if candidate.resume_text else "",
    }

    AgentClass = AGENT_MAP[session.agent_type]
    agent = AgentClass(candidate_info=analysis, resume_text=candidate.resume_text or "")
    opening = agent.get_opening_message()

    _active_agents[session_id] = agent

    # Persist opening message
    _save_message(db, session_id, "agent", opening)

    session.status = "in_progress"
    db.commit()
    return opening


def send_answer(db: Session, session_id: int, answer: str) -> str:
    """Feed a candidate answer to the agent and persist both turns."""
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise ValueError(f"Session {session_id} not found.")
    if session.status != "in_progress":
        raise ValueError("Session is not in progress.")

    agent = _active_agents.get(session_id)
    if agent is None:
        # Agent was lost (server restart) — rebuild from DB transcript
        agent = _rebuild_agent(db, session)
        _active_agents[session_id] = agent

    _save_message(db, session_id, "candidate", answer)
    reply = agent.respond(answer)
    _save_message(db, session_id, "agent", reply)
    db.commit()
    return reply


def finish_session(db: Session, session_id: int) -> dict:
    """
    Close the interview, score it, persist the report.
    Returns the scoring dict.
    """
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise ValueError(f"Session {session_id} not found.")

    agent = _active_agents.get(session_id)
    if agent is None:
        agent = _rebuild_agent(db, session)

    closing = agent.close_interview()
    _save_message(db, session_id, "agent", closing)

    transcript = agent.get_transcript()
    candidate = session.candidate

    scores = score_interview(
        agent_type=session.agent_type,
        candidate_name=candidate.name,
        job_role=candidate.job_role or "the role",
        transcript=transcript,
        resume_summary=candidate.resume_text[:500] if candidate.resume_text else "",
    )

    report = Report(
        session_id=session_id,
        candidate_id=candidate.id,
        overall_score=scores["overall_score"],
        communication_score=scores["communication_score"],
        technical_score=scores["technical_score"],
        cultural_fit_score=scores["cultural_fit_score"],
        strengths=scores["strengths"],
        weaknesses=scores["weaknesses"],
        recommendation=scores["recommendation"],
        detailed_feedback=scores["detailed_feedback"],
    )
    db.add(report)

    session.status = "completed"
    session.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(report)

    _active_agents.pop(session_id, None)
    scores["closing_message"] = closing
    return scores


def get_session_transcript(db: Session, session_id: int) -> list[dict]:
    messages = (
        db.query(InterviewMessage)
        .filter(InterviewMessage.session_id == session_id)
        .order_by(InterviewMessage.timestamp)
        .all()
    )
    return [{"role": m.role, "content": m.content, "timestamp": str(m.timestamp)} for m in messages]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _save_message(db: Session, session_id: int, role: str, content: str):
    msg = InterviewMessage(session_id=session_id, role=role, content=content)
    db.add(msg)
    db.flush()


def _rebuild_agent(db: Session, session: InterviewSession):
    """Rebuild an agent from the persisted transcript after a server restart."""
    candidate = session.candidate
    analysis = {
        "name": candidate.name,
        "email": candidate.email,
        "job_role": candidate.job_role,
        "experience_years": candidate.experience_years,
        "skills": candidate.skills,
        "education": "",
        "summary": candidate.resume_text[:400] if candidate.resume_text else "",
    }
    AgentClass = AGENT_MAP[session.agent_type]
    agent = AgentClass(candidate_info=analysis, resume_text=candidate.resume_text or "")

    messages = (
        db.query(InterviewMessage)
        .filter(InterviewMessage.session_id == session.id)
        .order_by(InterviewMessage.timestamp)
        .all()
    )
    for m in messages:
        role = "assistant" if m.role == "agent" else "user"
        agent.conversation.append({"role": role, "content": m.content})

    return agent
