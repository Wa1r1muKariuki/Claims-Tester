import random

import requests
import streamlit as st

st.set_page_config(page_title="Claims Severity Tester", page_icon="🚗", layout="centered")

# ---------- Config (all from Streamlit secrets; all optional) ----------
ENDPOINT_URL = st.secrets.get("ENDPOINT_URL", "")        # the backend that runs the VLLM
ENDPOINT_KEY = st.secrets.get("ENDPOINT_KEY", "")        # sent as Bearer token, if they need one
FILE_FIELD = st.secrets.get("FILE_FIELD", "file")        # multipart field name for the image
APP_PASS = st.secrets.get("APP_PASS", "")
DEMO_MODE = not ENDPOINT_URL

# ---------- Optional password gate ----------
if APP_PASS:
    if "authed" not in st.session_state:
        st.session_state.authed = False
    if not st.session_state.authed:
        pw = st.text_input("Password", type="password")
        if st.button("Enter"):
            if pw == APP_PASS:
                st.session_state.authed = True
                st.rerun()
            else:
                st.error("Wrong password")
        st.stop()

SCORE_KEYS = ("score", "severity", "severity_score")
DECISION_KEYS = ("decision", "recommendation", "action", "verdict")


def find_key(data, keys):
    """Look for the first matching key at the top level or one level down."""
    if isinstance(data, dict):
        for k in keys:
            if k in data and data[k] is not None:
                return data[k]
        for v in data.values():
            if isinstance(v, dict):
                found = find_key(v, keys)
                if found is not None:
                    return found
    return None


def call_endpoint(image):
    headers = {"Authorization": f"Bearer {ENDPOINT_KEY}"} if ENDPOINT_KEY else {}
    files = {FILE_FIELD: (image.name, image.getvalue(), image.type or "image/jpeg")}
    resp = requests.post(ENDPOINT_URL, headers=headers, files=files, timeout=120)
    resp.raise_for_status()
    return resp.json()


# ---------- UI ----------
st.title("🚗 Claims Severity Tester")
st.caption("Upload a car image. The backend scores the damage; high severity = Replace, low = Repair.")

if DEMO_MODE:
    st.info("Demo mode: no backend connected yet, so results are random placeholders.")

# Scores in the historical data run from 0 (no damage) to about 100.
threshold = st.sidebar.slider("Replace threshold (score ≥)", 1, 100, 60)
st.sidebar.caption("Scores below this are Repair, at or above are Replace.")

image = st.file_uploader("Car image", type=["jpg", "jpeg", "png", "webp"])
if image:
    st.image(image.getvalue(), use_container_width=True)

if st.button("Assess", type="primary", disabled=image is None):
    with st.spinner("Assessing..."):
        try:
            result = {"score": round(random.choice([0, 0, random.uniform(5, 100)]), 1)} if DEMO_MODE else call_endpoint(image)
        except Exception as e:
            st.error(f"Backend call failed: {e}")
            st.stop()

    score = find_key(result, SCORE_KEYS)
    decision_text = find_key(result, DECISION_KEYS)

    if score is None and decision_text is None:
        st.error("Couldn't find a score in the backend response. Check the raw output below.")
    else:
        if score is not None:
            score = float(score)
            if score <= 0:
                label, color = "NO VISIBLE DAMAGE", "#546e7a"
            elif score >= threshold:
                label, color = "REPLACE", "#c62828"
            else:
                label, color = "REPAIR", "#2e7d32"
            detail = f"score {score:g}"
        else:
            label = "REPLACE" if "replace" in str(decision_text).lower() else "REPAIR"
            color = "#c62828" if label == "REPLACE" else "#2e7d32"
            detail = "from backend"

        st.markdown(
            f"<div style='padding:16px;border-radius:10px;background:{color};color:white;"
            f"font-size:28px;font-weight:700;text-align:center'>{label} &nbsp;·&nbsp; {detail}</div>",
            unsafe_allow_html=True,
        )
        if score is not None:
            st.progress(min(max(score, 0), 100) / 100)

    with st.expander("Raw backend response"):
        st.json(result)
