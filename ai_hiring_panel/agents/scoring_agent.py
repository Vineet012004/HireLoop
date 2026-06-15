"""Scoring Agent — analyses full interview transcripts and produces a structured evaluation report."""
import json
import re
from llm.groq_client import chat_completion

SCORING_PROMPT = """You are an expert hiring evaluator. You have just reviewed the full transcript of a {agent_type} interview with {candidate_name} for the role of {job_role}.

Interview transcript:
---
{transcript}
---

Candidate resume summary:
{resume_summary}

Based on the transcript, produce a JSON evaluation report with exactly these keys:

{{
  "overall_score": <float 0-10>,
  "communication_score": <float 0-10>,
  "technical_score": <float 0-10>,
  "cultural_fit_score": <float 0-10>,
  "strengths": ["strength1", "strength2", "strength3"],
  "weaknesses": ["weakness1", "weakness2"],
  "recommendation": "<one of: strong_hire | hire | consider | no_hire | strong_no_hire>",
  "detailed_feedback": "3-5 sentences of honest, constructive feedback for the recruiter."
}}

Scoring rubric:
- 9-10: Exceptional, rare talent
- 7-8: Strong candidate, clear hire
- 5-6: Average, needs more consideration
- 3-4: Below expectations
- 0-2: Poor fit

Be honest and objective. Respond ONLY with the JSON object."""


def score_interview(
    agent_type: str,
    candidate_name: str,
    job_role: str,
    transcript: list[dict],
    resume_summary: str,
) -> dict:
    """
    Score a completed interview session.

    Args:
        agent_type: "hr" | "technical" | "manager"
        candidate_name: Candidate's full name.
        job_role: Target role.
        transcript: List of {"role": ..., "content": ...} dicts.
        resume_summary: Short resume summary text.

    Returns:
        Scoring dict with scores, strengths, weaknesses, recommendation, feedback.
    """
    transcript_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in transcript
    )

    prompt = SCORING_PROMPT.format(
        agent_type=agent_type,
        candidate_name=candidate_name,
        job_role=job_role,
        transcript=transcript_text[:5000],
        resume_summary=resume_summary[:500],
    )

    response = chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=900,
    )

    cleaned = re.sub(r"```(?:json)?|```", "", response).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = _fallback_scores()

    # Clamp all numeric scores between 0 and 10
    for key in ("overall_score", "communication_score", "technical_score", "cultural_fit_score"):
        data[key] = max(0.0, min(10.0, float(data.get(key) or 0)))

    data.setdefault("strengths", [])
    data.setdefault("weaknesses", [])
    data.setdefault("recommendation", "consider")
    data.setdefault("detailed_feedback", "No detailed feedback generated.")
    return data


def _fallback_scores() -> dict:
    return {
        "overall_score": 5.0,
        "communication_score": 5.0,
        "technical_score": 5.0,
        "cultural_fit_score": 5.0,
        "strengths": ["Unable to parse strengths"],
        "weaknesses": ["Unable to parse weaknesses"],
        "recommendation": "consider",
        "detailed_feedback": "Scoring could not be fully parsed. Please review the transcript manually.",
    }
