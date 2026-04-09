import json
import re
import uuid
import streamlit as st
from flowise import Flowise, PredictionData

st.set_page_config(page_title="Aanya Diagnostic Bot", layout="centered")

BASE_URL = "https://cloud.flowiseai.com"
FLOW_ID = "a6dfa1f4-f439-43eb-b613-97b1c67f5bc0"

client = Flowise(base_url=BASE_URL)

st.title("🩺 Aanya Diagnostic Bot")
st.caption("Aanya interacts with Malik while you guide the diagnostic path.")

def clean_text(text):
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("**", "").replace("---", "")
    return text.strip()

def is_final_diagnosis(text):
    upper = text.upper()
    return "FINAL DIAGNOSIS" in upper or "DIAGNOSIS LEVEL" in upper

def extract_options(text):
    text = clean_text(text)

    marker = "Choose what Aanya explores next:"
    idx = text.lower().find(marker.lower())
    if idx == -1:
        return []

    part = text[idx + len(marker):].strip()

    match = re.search(
        r"A\)\s*(.*?)\s*B\)\s*(.*?)\s*C\)\s*(.*)",
        part,
        flags=re.DOTALL | re.IGNORECASE
    )

    if not match:
        return []

    a_text = " ".join(match.group(1).split())
    b_text = " ".join(match.group(2).split())
    c_text = " ".join(match.group(3).split())

    c_text = re.split(
        r"ROUND\s+\d+|FINAL DIAGNOSIS|Malik:|Aanya:",
        c_text,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0].strip()
    c_text = " ".join(c_text.split())

    if a_text and b_text and c_text:
        return [("A", a_text), ("B", b_text), ("C", c_text)]

    return []

def stream_response(user_input, session_id):
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

def render_block(text):
    text = clean_text(text)

    round_match = re.search(r"ROUND\s+(\d+)", text, flags=re.IGNORECASE)
    if round_match:
        round_num = int(round_match.group(1))
        st.markdown(f"## Round {round_num}")
        st.progress(round_num / 4)

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    story_lines = []
    for line in lines:
        if line.lower().startswith("choose what aanya explores next"):
            break
        story_lines.append(line)

    with st.container(border=True):
        for line in story_lines:
            if line.startswith("Aanya:"):
                st.markdown(f"**Aanya:** {line.replace('Aanya:', '').strip()}")
            elif line.startswith("Malik:"):
                st.markdown(f"**Malik:** {line.replace('Malik:', '').strip()}")
            else:
                st.markdown(line)

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "history" not in st.session_state:
    st.session_state.history = []

if "started" not in st.session_state:
    st.session_state.started = False

if st.button("🔄 Restart Diagnostic"):
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.history = []
    st.session_state.started = False
    st.rerun()

if not st.session_state.started:
    st.markdown("### Start the automated diagnostic interaction")
    if st.button("▶ Start", use_container_width=True):
        first_output = st.write_stream(
            stream_response("Start the simulation", st.session_state.session_id)
        )
        st.session_state.history.append(first_output)
        st.session_state.started = True
        st.rerun()

for msg in st.session_state.history:
    render_block(msg)
    st.markdown("<br>", unsafe_allow_html=True)

if st.session_state.history:
    latest = clean_text(st.session_state.history[-1])

    if not is_final_diagnosis(latest):
        options = extract_options(latest)

        if options:
            st.subheader("Choose next diagnostic path")

            cols = st.columns(3)

            for i, (letter, text) in enumerate(options):
                with cols[i]:
                    with st.container(border=True):
                        st.markdown(f"**Option {letter}**")
                        st.write(text)

                        if st.button(
                            f"Select {letter}",
                            key=f"{letter}_{len(st.session_state.history)}",
                            use_container_width=True
                        ):
                            next_output = st.write_stream(
                                stream_response(letter, st.session_state.session_id)
                            )
                            st.session_state.history.append(next_output)
                            st.rerun()
        else:
            st.info("No options detected in the latest response.")
            with st.expander("Debug latest response"):
                st.code(latest)
