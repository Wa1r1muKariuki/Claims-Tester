import base64, json, mimetypes, os, re

import gradio as gr
from openai import OpenAI

# Set these in the Space's "Variables and secrets" (never in the code)
client = OpenAI(
    api_key=os.environ.get("ZAI_API_KEY", ""),
    base_url=os.environ.get("GLM_BASE_URL", "https://api.z.ai/api/paas/v4"),
)
MODEL = os.environ.get("GLM_MODEL", "glm-4.6v")  # must be a vision model

# Historical rule: high severity = replace
DECISION = {"low": "Repair", "medium": "Repair", "high": "Replace"}

PROMPT = """You are a vehicle damage assessor. Look at the car image(s) and reply with ONLY this JSON:
{"severity": "low|medium|high", "confidence": 0.0-1.0, "damaged_parts": ["..."], "rationale": "one or two sentences"}"""


def to_data_url(path):
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    with open(path, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"


def assess(images, report_text, report_file, recorded):
    if not images:
        raise gr.Error("Add at least one car image.")
    text = (report_text or "").strip()
    if not text and report_file and report_file.lower().endswith((".txt", ".json", ".csv")):
        text = open(report_file, encoding="utf-8", errors="ignore").read()

    content = [{"type": "text", "text": PROMPT}]
    for p in images:
        content.append({"type": "image_url", "image_url": {"url": to_data_url(p)}})

    try:
        res = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": content}], temperature=0
        )
    except Exception as e:
        raise gr.Error(f"GLM request failed: {e}")

    raw = res.choices[0].message.content or ""
    match = re.search(r"\{.*\}", raw, re.S)
    try:
        data = json.loads(match.group(0))
    except Exception:
        raise gr.Error("Model did not return valid JSON:\n" + raw[:500])

    sev = str(data.get("severity", "")).lower()
    decision = DECISION.get(sev, "Unknown")
    if recorded == "Not stated":
        verdict = "No recorded outcome to compare."
    else:
        verdict = "Match" if decision == recorded else "Mismatch"

    conf = data.get("confidence")
    summary = (
        f"## Model: {decision}\n"
        f"**Severity:** {sev}"
        + (f"  \n**Confidence:** {round(float(conf) * 100)}%" if conf is not None else "")
        + f"  \n**Parts:** {', '.join(data.get('damaged_parts', [])) or 'none listed'}"
        + f"  \n**Report says:** {recorded}"
        + f"\n\n### {verdict}\n\n{data.get('rationale', '')}"
    )
    return summary, text, data


with gr.Blocks(title="Claim severity tester") as demo:
    gr.Markdown("# Claim severity tester\nCompare the GLM model's assessment of the car photos with what the claim report recorded.")
    with gr.Row():
        with gr.Column():
            images = gr.File(label="Car images", file_count="multiple", file_types=["image"], type="filepath")
            report_text = gr.Textbox(label="Claim report (paste text)", lines=6)
            report_file = gr.File(label="Or attach report (.txt, .json, .csv)", type="filepath")
            recorded = gr.Radio(["Not stated", "Repair", "Replace"], value="Not stated", label="Outcome recorded in the report")
            run = gr.Button("Assess claim", variant="primary")
        with gr.Column():
            result = gr.Markdown()
            shown_report = gr.Textbox(label="Report text used", lines=6, interactive=False)
            raw = gr.JSON(label="Raw model output")
    run.click(assess, [images, report_text, report_file, recorded], [result, shown_report, raw])

user, pw = os.environ.get("APP_USER"), os.environ.get("APP_PASS")
demo.launch(auth=(user, pw) if user and pw else None)
