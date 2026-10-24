"""
Streamlit web application for the MCA Timetable Intelligent Assistant.
Deploy on Databricks Apps or run locally with: streamlit run app.py
"""
import streamlit as st
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agent import MCATimetableAgent
from src.config import config
from src.llm_client import init_llm_client


# ── Page Config ──
st.set_page_config(
    page_title="MCA Timetable Assistant",
    page_icon="\ud83d\udd52",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Initialize LLM client ──
init_llm_client()

# ── Sidebar: Student Profile ──
st.sidebar.title("\u2699\ufe0f Settings")
semester = st.sidebar.selectbox("Semester", [1, 2, 3], index=1)
section = st.sidebar.selectbox("Section", ["A", "B", "C", "D"], index=0)
track = st.sidebar.selectbox(
    "Track (optional)",
    ["", "Cloud Computing", "Data Science", "Cyber Security & Data Science"],
    index=0,
    help="Filter by academic track. Leave blank for all.",
)
track = track if track else None

st.sidebar.markdown("---")
missing = config.validate()
if missing:
    st.sidebar.warning(f"Missing env vars: {', '.join(missing)}")
else:
    st.sidebar.success("\u2705 Configuration OK")

# ── Initialize session state ──
if "agent" not in st.session_state or st.session_state.get("_agent_key") != f"{semester}_{section}_{track}":
    spark = None
    # Try to get Spark session (for Databricks Apps environment)
    try:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.getOrCreate()
    except Exception:
        pass
    
    st.session_state.agent = MCATimetableAgent(
        semester=semester, section=section, track=track,
        enable_logging=False, spark=spark,
    )
    st.session_state._agent_key = f"{semester}_{section}_{track}"
    st.session_state.chat_history = []

agent = st.session_state.agent

# ── Main UI ──
st.title("\ud83d\udd52\ufe0f MCA Timetable Intelligent Assistant")
st.markdown("Ask me about your class schedule, subjects, faculty, rooms, breaks, and more.")

# Quick action buttons
st.markdown("### \ud83d\udca1 Quick Questions")
col1, col2, col3, col4 = st.columns(4)
quick_questions = {
    "Today": "What classes do I have today?",
    "Tomorrow": "What classes do I have tomorrow?",
    "Full Week": "Show my full timetable for the week",
    "Conflicts": "Are there any timetable conflicts?",
}
for i, (label, q) in enumerate(quick_questions.items()):
    if [col1, col2, col3, col4][i].button(label, key=f"quick_{label}"):
        st.session_state.pending_question = q

# Chat interface
st.markdown("---")
chat_container = st.container()

# Display chat history
with chat_container:
    for entry in st.session_state.chat_history:
        with st.chat_message("user"):
            st.write(entry["question"])
        with st.chat_message("assistant"):
            st.markdown(entry["answer"])

# Input
user_input = st.chat_input("Ask about your timetable...")
question = user_input or st.session_state.pop("pending_question", None)

if question:
    with st.chat_message("user"):
        st.write(question)
    
    with st.chat_message("assistant"):
        with st.spinner("Looking up your timetable..."):
            response = agent.ask(question)
        st.markdown(response["answer"])
        
        # Show metadata
        with st.expander("Details", expanded=False):
            st.json({
                "tools": response.get("tools", []),
                "latency_ms": response.get("latency_ms", 0),
            })
    
    st.session_state.chat_history.append({
        "question": question,
        "answer": response["answer"],
    })
    st.rerun()

# ── Footer ──
st.markdown("---")
st.caption("MCA Timetable Intelligent Assistant | Powered by Databricks AI")
