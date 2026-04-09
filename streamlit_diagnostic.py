import json
import re
import uuid
import streamlit as st
from flowise import Flowise, PredictionData

st.set_page_config(page_title="Aanya Diagnostic Bot", layout="centered")

BASE_URL = "https://cloud.flowiseai.com"
FLOW_ID = "a6dfa1f4-f439-43eb-b613-97b1c67f5bc0"  # replace if needed

client = Flowise(base_url=BASE_URL)

st.title("🩺 Aanya Diagnostic Bot")
st.caption("Provide a few intake inputs first, then watch Aanya and Malik complete an automated diagnostic conversation.")

PATIENT = {
    "name": "Malik",
    "age": 22,
    "condition_hint": "Social anxiety",
    "summary": "Malik struggles with overthinking, fear of judgment, and avoiding group situations."
}

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("**", "").replace("---", "")
    return text.strip()

def is_final_diagnosis(text: str) -> bool:
    upper = text.upper()
    return "FINAL DIAGNOSIS" in upper or "DIAGNOSIS LEVEL" in upper

def stream_response(user_input: str, session_id: str):
    completion = client.create_prediction(
        PredictionData(
            chatflowId=FLOW_ID,
            question=user_input,
            overrideConfig={"sessionId": session_id},
            streaming=True
        )
    )

    for chunk in completion:
        try:
            parsed = json.loads(chunk)
            if parsed.get("event") == "token" and parsed.get("data"):
                yield str(parsed["data"])
        except Exception:
            continue

def render_conversation(text: str):
    text = clean_text(text)

    rounds = re.findall(r"ROUND\s+\d+", text, flags=re.IGNORECASE)
    if rounds:
        st.markdown(f"### Automated Diagnostic Conversation")
        st.progress(min(len(rounds) / 4, 1.0))

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    with st.container(border=True):
        for line in lines:
            if re.match(r"^ROUND\s+\d+", line, flags=re.IGNORECASE):
                st.markdown(f"#### {line.title()}")
            elif line.upper().startswith("FINAL DIAGNOSIS"):
                st.markdown("### Final Diagnosis")
            elif line.startswith("Aanya:"):
                st.markdown(f"**Aanya:** {line.replace('Aanya:', '', 1).strip()}")
            elif line.startswith("Malik:"):
                st.markdown(f"**Malik:** {line.replace('Malik:', '', 1).strip()}")
            else:
                st.markdown(line)

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "started" not in st.session_state:
    st.session_state.started = False

if "conversation_output" not in st.session_state:
    st.session_state.conversation_output = ""

if st.button("🔄 Restart"):
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.started = False
    st.session_state.conversation_output = ""
    st.rerun()

st.markdown("### Patient Scenario")
st.info(
    f"**{PATIENT['name']}**, age {PATIENT['age']}. "
    f"{PATIENT['summary']}"
)

if not st.session_state.started:
    st.markdown("### Intake Guidance")
    st.write("Answer these short setup questions before the automated conversation begins.")

    strongest_concern = st.selectbox(
        "1. Which concern seems strongest in this case?",
        [
            "Fear of judgment in social situations",
            "Stress and overwhelm in daily life",
            "Low mood and lack of motivation",
        ]
    )

    daily_impact = st.selectbox(
        "2. Which area seems most affected?",
        [
            "Work or study",
            "Sleep and energy",
            "Social comfort and relationships",
        ]
    )

    symptom_focus = st.selectbox(
        "3. Which symptom stands out most?",
        [
            "Overthinking and racing thoughts",
            "Physical tension or nervousness",
            "Avoidance and withdrawal",
        ]
    )

    severity_guess = st.selectbox(
        "4. How severe does this seem at first glance?",
        [
            "Mild",
            "Moderate",
            "Severe",
        ]
    )

    coping_pattern = st.selectbox(
        "5. What coping pattern seems most likely?",
        [
            "Avoids the situation",
            "Tries to push through quietly",
            "Seeks reassurance from one trusted person",
        ]
    )

    if st.button("▶ Start Automated Diagnostic Conversation", use_container_width=True):
        intake_prompt = f"""
Start the automated diagnostic conversation using this patient scenario:

Patient Name: {PATIENT['name']}
Age: {PATIENT['age']}
Scenario Summary: {PATIENT['summary']}

User intake guidance:
- Strongest concern: {strongest_concern}
- Main life impact: {daily_impact}
- Symptom focus: {symptom_focus}
- Initial severity impression: {severity_guess}
- Likely coping pattern: {coping_pattern}

Now begin the 4-round automated diagnostic conversation between Aanya and Malik, then provide the final diagnosis.
"""
        with st.spinner("Running automated diagnostic conversation..."):
            output = st.write_stream(
                stream_response(intake_prompt, st.session_state.session_id)
            )
        st.session_state.conversation_output = output
        st.session_state.started = True
        st.rerun()

else:
    render_conversation(st.session_state.conversation_output)
