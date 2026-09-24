import base64
import json
import random
import re

import requests
import streamlit as st

st.set_page_config(page_title="Claims Severity Tester", page_icon="🚗", layout="wide")

# ---------- Config (all from Streamlit secrets; all optional) ----------
API_KEY = st.secrets.get("ZAI_API_KEY", "")
MODEL = st.secrets.get("GLM_MODEL", "glm-4.6v")
BASE_URL = st.secrets.get("GLM_BASE_URL", "https://api.z.ai/api/paas/v4").rstrip("/")
APP_PASS = st.secrets.get("APP_PASS", "")
DEMO_MODE = not API_KEY

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

PROMPT = """You are a vehicle damage assessor. Look at the car image(s) and the claim report.
Rate damage severity from 1 (cosmetic) to 10 (total structural damage), using the same
standards as our historical claims where high severity meant the part was replaced and
low severity meant it was repaired.

Claim report:
{report}

Reply with ONLY JSON, no other text:
{{"severity": <integer 1-10>, "damaged_parts": [<strings>], "reasoning": "<2-3 sentences>"}}"""


def read_report(uploaded, pasted):
    text = pasted.strip()
    if uploaded is not None:
        name = uploaded.name.lower()
        if name.endswith(".pdf"):
            try:
                from pypdf import PdfReader

                reader = PdfReader(uploaded)
                text += "\n" + "\n".join((p.extract_text() or "") for p in reader.pages)
            except Exception as e:
                st.warning(f"Could not read PDF: {e}")
        else:
            text += "\n" + uploaded.getvalue().decode("utf-8", errors="ignore")
    return text.strip()


def call_model(images, report):
    content = [{"type": "text", "text": PROMPT.format(report=report or "(none provided)")}]
    for img in images:
        b64 = base64.b64encode(img.getvalue()).decode()
        mime = img.type or "image/jpeg"
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
    resp = requests.post(
        f"{BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"model": MODEL, "messages": [{"role": "user", "content": content}], "temperature": 0.1},
        timeout=120,
    )
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"]
    match = re.search(r"\{.*\}", raw, re.S)
    return json.loads(match.group(0))


def demo_result():
    sev = random.randint(1, 10)
    return {
        "severity": sev,
        "damaged_parts": ["front bumper", "bonnet"],
        "reasoning": "DEMO MODE: placeholder output. Add your model API key in Secrets to get real predictions.",
    }


# ---------- UI ----------
st.title("🚗 Claims Severity Tester")
st.caption("Upload car images and the claim report. High severity = Replace, low = Repair.")

if DEMO_MODE:
    st.info("Demo mode: no model connected yet, so results are random placeholders.")

threshold = st.sidebar.slider("Replace threshold (severity ≥)", 1, 10, 7)

left, right = st.columns(2)
with left:
    images = st.file_uploader(
        "Car images", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True
    )
    if images:
        st.image([i.getvalue() for i in images], width=200)
with right:
    report_file = st.file_uploader("Claim report (PDF or TXT)", type=["pdf", "txt"])
    report_text = st.text_area("...or paste the report text", height=150)

if st.button("Assess claim", type="primary", disabled=not images):
    report = read_report(report_file, report_text)
    with st.spinner("Assessing..."):
        try:
            result = demo_result() if DEMO_MODE else call_model(images, report)
        except Exception as e:
            st.error(f"Model call failed: {e}")
            st.stop()

    sev = int(result.get("severity", 0))
    decision = "REPLACE" if sev >= threshold else "REPAIR"
    color = "#c62828" if decision == "REPLACE" else "#2e7d32"
    st.markdown(
        f"<div style='padding:16px;border-radius:10px;background:{color};color:white;"
        f"font-size:28px;font-weight:700'>{decision} &nbsp;·&nbsp; severity {sev}/10</div>",
        unsafe_allow_html=True,
    )
    st.progress(min(max(sev, 0), 10) / 10)
    st.write("**Damaged parts:**", ", ".join(result.get("damaged_parts", [])) or "n/a")
    st.write("**Reasoning:**", result.get("reasoning", ""))
    with st.expander("Raw output"):
        st.json(result)
