"""Resume analyzer — uses the LLM to extract structured information from resume text."""
import json
import re
from llm.groq_client import chat_completion

ANALYSIS_PROMPT = """You are a professional resume analyst. Given the resume text below, extract the following information and return it as a valid JSON object with exactly these keys:

{{
  "name": "full name of the candidate",
  "email": "email address or empty string",
  "job_role": "most recent or target job role",
  "experience_years": <number of years of total experience as a float>,
  "skills": ["skill1", "skill2", ...],
  "education": "highest education level and institution",
  "summary": "2-3 sentence professional summary of the candidate"
}}

Resume text:
---
{resume_text}
---

Respond ONLY with the JSON object. No explanation, no markdown fences."""


def analyze_resume(resume_text: str) -> dict:
    """
    Call the LLM to extract structured candidate info from raw resume text.

    Returns:
        A dict with keys: name, email, job_role, experience_years, skills,
        education, summary.
    """
    prompt = ANALYSIS_PROMPT.format(resume_text=resume_text[:6000])  # cap to avoid token overflow
    response = chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=800,
    )

    # Strip any accidental markdown fences
    cleaned = re.sub(r"```(?:json)?|```", "", response).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: return minimal structure so the flow doesn't break
        data = {
            "name": "Unknown",
            "email": "",
            "job_role": "Unknown",
            "experience_years": 0.0,
            "skills": [],
            "education": "",
            "summary": resume_text[:300],
        }

    # Normalise types
    data["experience_years"] = float(data.get("experience_years") or 0)
    data["skills"] = data.get("skills") or []
    return data
