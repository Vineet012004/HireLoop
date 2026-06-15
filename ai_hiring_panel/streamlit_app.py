"""
HireLoop — Streamlit Frontend
==============================
Talks to the FastAPI backend at API_BASE_URL.
"""
import os
import streamlit as st
import requests

# Read backend URL from Streamlit secrets (cloud) or env var (local)
try:
    API_BASE_URL = st.secrets["API_BASE_URL"]
except Exception:
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(
    page_title="HireLoop",
    page_icon="🔁",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def api_post(endpoint: str, json: dict | None = None, files=None) -> dict:
    try:
        if files:
            resp = requests.post(f"{API_BASE_URL}{endpoint}", files=files, timeout=60)
        else:
            resp = requests.post(f"{API_BASE_URL}{endpoint}", json=json, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to the backend. Make sure the FastAPI server is running on port 8000.")
        st.stop()
    except requests.exceptions.HTTPError as exc:
        detail = exc.response.json().get("detail", str(exc)) if exc.response else str(exc)
        st.error(f"API error: {detail}")
        st.stop()


def api_get(endpoint: str) -> dict:
    try:
        resp = requests.get(f"{API_BASE_URL}{endpoint}", timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to the backend. Make sure the FastAPI server is running on port 8000.")
        st.stop()
    except requests.exceptions.HTTPError as exc:
        detail = exc.response.json().get("detail", str(exc)) if exc.response else str(exc)
        st.error(f"API error: {detail}")
        st.stop()


def recommendation_badge(rec: str) -> str:
    badges = {
        "strong_hire": "🟢 Strong Hire",
        "hire": "🟩 Hire",
        "consider": "🟡 Consider",
        "no_hire": "🔴 No Hire",
        "strong_no_hire": "⛔ Strong No Hire",
    }
    return badges.get(rec, rec.replace("_", " ").title())


def score_bar(label: str, score: float):
    colour = "green" if score >= 7 else "orange" if score >= 5 else "red"
    st.markdown(f"**{label}:** {score:.1f}/10")
    st.progress(score / 10, text="")


# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------

defaults = {
    "page": "upload",           # upload | interview | report | dashboard
    "candidate_id": None,
    "candidate_name": "",
    "job_role": "",
    "analysis": {},
    "session_id": None,
    "agent_type": None,
    "chat_history": [],         # list of {"role": "agent"|"candidate", "content": str}
    "interview_done": False,
    "report": None,
    "all_reports": [],          # for the dashboard tab
}

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

with st.sidebar:
    st.image("https://img.icons8.com/color/96/restart--v1.png", width=60)
    st.title("HireLoop")
    st.markdown("---")

    pages = {
        "📄 Upload Resume": "upload",
        "💬 Interview": "interview",
        "📊 Report": "report",
        "🏢 Dashboard": "dashboard",
    }
    for label, page_key in pages.items():
        if st.button(label, use_container_width=True):
            st.session_state.page = page_key

    st.markdown("---")
    if st.session_state.candidate_name:
        st.info(f"👤 **Candidate:** {st.session_state.candidate_name}")
    if st.session_state.agent_type:
        agent_labels = {"hr": "HR", "technical": "Technical", "manager": "Manager"}
        st.info(f"🤖 **Agent:** {agent_labels.get(st.session_state.agent_type, '')}")


# ---------------------------------------------------------------------------
# Page: Upload Resume
# ---------------------------------------------------------------------------

if st.session_state.page == "upload":
    st.title("📄 Resume Upload & Analysis")
    st.markdown("Upload the candidate's resume to start the AI analysis and interview process.")

    col1, col2 = st.columns([1, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "Upload Resume (PDF, DOCX, or TXT)",
            type=["pdf", "docx", "txt"],
        )

        if uploaded_file:
            st.success(f"File selected: **{uploaded_file.name}**")

            if st.button("🔍 Analyse Resume", type="primary", use_container_width=True):
                with st.spinner("Parsing and analysing resume with AI..."):
                    result = api_post(
                        "/resume/upload",
                        files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)},
                    )

                st.session_state.candidate_id = result["candidate_id"]
                st.session_state.analysis = result["analysis"]
                st.session_state.candidate_name = result["analysis"].get("name", "Unknown")
                st.session_state.job_role = result["analysis"].get("job_role", "")
                st.success("✅ Resume analysed successfully!")

    with col2:
        if st.session_state.analysis:
            a = st.session_state.analysis
            st.subheader("📋 Extracted Candidate Profile")
            st.markdown(f"**Name:** {a.get('name', '—')}")
            st.markdown(f"**Email:** {a.get('email', '—')}")
            st.markdown(f"**Target Role:** {a.get('job_role', '—')}")
            st.markdown(f"**Experience:** {a.get('experience_years', 0)} years")
            st.markdown(f"**Education:** {a.get('education', '—')}")
            st.markdown(f"**Summary:** {a.get('summary', '—')}")

            if a.get("skills"):
                st.markdown("**Skills:**")
                skills_text = "  ".join([f"`{s}`" for s in a["skills"]])
                st.markdown(skills_text)

    if st.session_state.candidate_id:
        st.markdown("---")
        st.subheader("🎯 Start an Interview")
        agent_choice = st.selectbox(
            "Select Interviewer",
            options=["technical", "hr", "manager"],
            format_func=lambda x: {"technical": "⚙️ Technical Interviewer", "hr": "👥 HR Interviewer", "manager": "🏢 Manager Interviewer"}[x],
        )

        if st.button("🚀 Start Interview", type="primary"):
            with st.spinner("Creating interview session..."):
                sess = api_post("/sessions", json={"candidate_id": st.session_state.candidate_id, "agent_type": agent_choice})
                session_id = sess["session_id"]

                opening = api_post(f"/sessions/{session_id}/start")

            st.session_state.session_id = session_id
            st.session_state.agent_type = agent_choice
            st.session_state.chat_history = [{"role": "agent", "content": opening["message"]}]
            st.session_state.interview_done = False
            st.session_state.report = None
            st.session_state.page = "interview"
            st.rerun()


# ---------------------------------------------------------------------------
# Page: Interview
# ---------------------------------------------------------------------------

elif st.session_state.page == "interview":
    agent_labels = {"hr": "👥 HR Interviewer — Sarah", "technical": "⚙️ Technical Interviewer — Alex", "manager": "🏢 Manager Interviewer — Jordan"}
    st.title(agent_labels.get(st.session_state.agent_type, "Interview"))

    if not st.session_state.session_id:
        st.warning("No active interview session. Please upload a resume first.")
        st.stop()

    # Chat display
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history:
            if msg["role"] == "agent":
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(msg["content"])
            else:
                with st.chat_message("user", avatar="👤"):
                    st.markdown(msg["content"])

    if not st.session_state.interview_done:
        answer = st.chat_input("Type your answer here...")
        if answer:
            st.session_state.chat_history.append({"role": "candidate", "content": answer})

            with st.spinner("Agent is thinking..."):
                result = api_post(
                    f"/sessions/{st.session_state.session_id}/answer",
                    json={"answer": answer},
                )

            st.session_state.chat_history.append({"role": "agent", "content": result["message"]})
            st.rerun()

        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🏁 Finish Interview", type="secondary", use_container_width=True):
                with st.spinner("Scoring your interview..."):
                    report_data = api_post(f"/sessions/{st.session_state.session_id}/finish")

                closing = report_data["report"].get("closing_message", "")
                if closing:
                    st.session_state.chat_history.append({"role": "agent", "content": closing})

                st.session_state.interview_done = True
                st.session_state.report = report_data["report"]
                st.session_state.page = "report"
                st.rerun()
    else:
        st.success("Interview completed! View your report in the Report tab.")
        if st.button("📊 View Report"):
            st.session_state.page = "report"
            st.rerun()


# ---------------------------------------------------------------------------
# Page: Report
# ---------------------------------------------------------------------------

elif st.session_state.page == "report":
    st.title("📊 Interview Evaluation Report")

    if not st.session_state.report:
        st.warning("No report available yet. Complete an interview first.")
        st.stop()

    r = st.session_state.report

    # Header summary
    col1, col2, col3 = st.columns(3)
    col1.metric("Overall Score", f"{r.get('overall_score', 0):.1f} / 10")
    col2.markdown(f"**Recommendation**\n\n{recommendation_badge(r.get('recommendation', ''))}")
    col3.metric("Technical Score", f"{r.get('technical_score', 0):.1f} / 10")

    st.markdown("---")

    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("📈 Detailed Scores")
        score_bar("Overall", r.get("overall_score", 0))
        score_bar("Communication", r.get("communication_score", 0))
        score_bar("Technical", r.get("technical_score", 0))
        score_bar("Cultural Fit", r.get("cultural_fit_score", 0))

    with col_r:
        st.subheader("✅ Strengths")
        for s in r.get("strengths", []):
            st.markdown(f"- {s}")

        st.subheader("⚠️ Areas for Improvement")
        for w in r.get("weaknesses", []):
            st.markdown(f"- {w}")

    st.markdown("---")
    st.subheader("📝 Detailed Feedback")
    st.info(r.get("detailed_feedback", "No detailed feedback available."))

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔄 Start Another Interview", use_container_width=True):
            st.session_state.page = "upload"
            st.session_state.session_id = None
            st.session_state.chat_history = []
            st.session_state.interview_done = False
            st.session_state.report = None
            st.rerun()
    with col_b:
        if st.session_state.candidate_id:
            if st.button("📋 View All Candidate Reports", use_container_width=True):
                data = api_get(f"/candidates/{st.session_state.candidate_id}/reports")
                st.session_state.all_reports = data.get("reports", [])
                st.session_state.page = "dashboard"
                st.rerun()


# ---------------------------------------------------------------------------
# Page: Dashboard
# ---------------------------------------------------------------------------

elif st.session_state.page == "dashboard":
    st.title("🏢 Recruiter Dashboard")

    if st.session_state.candidate_id:
        data = api_get(f"/candidates/{st.session_state.candidate_id}/reports")
        reports = data.get("reports", [])

        st.subheader(f"Reports for: {data.get('candidate_name', 'Candidate')}")

        if not reports:
            st.info("No completed interviews yet for this candidate.")
        else:
            for rep in reports:
                agent_name = {"hr": "HR", "technical": "Technical", "manager": "Manager"}.get(
                    rep.get("agent_type", ""), "Interview"
                )
                with st.expander(
                    f"Session #{rep['session_id']} — {recommendation_badge(rep['recommendation'])} | Score: {rep['overall_score']:.1f}/10",
                    expanded=len(reports) == 1,
                ):
                    c1, c2 = st.columns(2)
                    with c1:
                        score_bar("Overall", rep["overall_score"])
                        score_bar("Communication", rep["communication_score"])
                        score_bar("Technical", rep["technical_score"])
                        score_bar("Cultural Fit", rep["cultural_fit_score"])
                    with c2:
                        st.markdown("**Strengths**")
                        for s in rep.get("strengths", []):
                            st.markdown(f"- {s}")
                        st.markdown("**Weaknesses**")
                        for w in rep.get("weaknesses", []):
                            st.markdown(f"- {w}")
                    st.markdown("**Feedback**")
                    st.info(rep.get("detailed_feedback", ""))
    else:
        st.info("Upload a resume and complete an interview to see the dashboard.")
