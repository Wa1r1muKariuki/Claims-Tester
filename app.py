import hashlib
import io
import random

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageOps

st.set_page_config(page_title="Car Damage Detection Demo", layout="wide")

VIEWS = ["Front", "Rear", "Left", "Right"]
PANELS = ["Front bumper", "Rear bumper", "Hood", "Trunk", "Roof", "Windshield",
          "Left front door", "Left rear door", "Right front door", "Right rear door",
          "Left fender", "Right fender", "Headlight", "Taillight", "Wheel/Tire"]
DAMAGES = ["Scratch", "Dent", "Crack", "Broken", "Torn", "Dislodged", "Flat tire", "Rust"]
VIEW_PANELS = {
    "Front": ["Front bumper", "Hood", "Headlight", "Windshield"],
    "Rear": ["Rear bumper", "Trunk", "Taillight"],
    "Left": ["Left front door", "Left rear door", "Left fender", "Wheel/Tire"],
    "Right": ["Right front door", "Right rear door", "Right fender", "Wheel/Tire"],
}
EMPTY = lambda: pd.DataFrame({"Panel": pd.Series(dtype=str), "Damage": pd.Series(dtype=str)})
COLS = {
    "Panel": st.column_config.SelectboxColumn(options=PANELS, required=True),
    "Damage": st.column_config.SelectboxColumn(options=DAMAGES, required=True),
}


# ---------- photo quality check ----------
def quality_check(img: Image.Image):
    issues = []
    w, h = img.size
    if min(w, h) < 480:
        issues.append(f"low resolution ({w}x{h})")
    small = img.copy()
    small.thumbnail((800, 800))
    g = np.asarray(small.convert("L"), dtype=np.float32)
    lap = -4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
    if lap.var() < 60:
        issues.append("blurry")
    if g.mean() < 50:
        issues.append("too dark")
    elif g.mean() > 215:
        issues.append("overexposed")
    return issues


# ---------- model (mock, swap for real API) ----------
def detect_damage(view: str, data: bytes):
    """Returns [{view, Panel, Damage, conf, bbox(rel x1,y1,x2,y2)}].
    MOCK: deterministic from image bytes. Replace with your real model/API call."""
    url = st.secrets.get("MODEL_API_URL", None) if hasattr(st, "secrets") else None
    if url:
        import requests
        r = requests.post(url, files={"image": data}, timeout=60)
        r.raise_for_status()
        return [{**d, "view": view} for d in r.json()]
    rng = random.Random(hashlib.md5(data).hexdigest())
    out = []
    for panel in rng.sample(VIEW_PANELS[view], k=rng.randint(0, 2)):
        x, y = rng.uniform(0.1, 0.5), rng.uniform(0.1, 0.5)
        out.append({"view": view, "Panel": panel, "Damage": rng.choice(DAMAGES),
                    "conf": round(rng.uniform(0.55, 0.97), 2),
                    "bbox": [x, y, x + rng.uniform(0.15, 0.35), y + rng.uniform(0.15, 0.35)]})
    return out


def annotate(data: bytes, dets):
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    d = ImageDraw.Draw(img)
    W, H = img.size
    for det in dets:
        x1, y1, x2, y2 = det["bbox"]
        box = [x1 * W, y1 * H, x2 * W, y2 * H]
        d.rectangle(box, outline="red", width=max(3, W // 250))
        d.text((box[0] + 4, box[1] + 4), f'{det["Panel"]} / {det["Damage"]} {det["conf"]:.0%}', fill="red")
    return img


# ---------- sidebar: triage ----------
st.title("Car Damage Detection Demo")
with st.sidebar:
    st.header("Triage")
    towed = st.radio("Was the vehicle towed?", ["No", "Yes"], key="towed",
                     help="A wrong pick can be switched at any point. Photos are kept.")
    st.caption("Journey 1: Minor" if towed == "No" else "Journey 2: Major")
minor = towed == "No"

tab1, tab2, tab3 = st.tabs(["1. Photos", "2. Damage form" if minor else "2. Garage report", "3. Results"])

# ---------- photos ----------
photos = {}
with tab1:
    st.write("Take or upload a photo from each angle. On a phone the uploader opens the camera.")
    cols = st.columns(4)
    for col, view in zip(cols, VIEWS):
        with col:
            f = st.file_uploader(view, type=["jpg", "jpeg", "png"], key=f"up_{view}")
            if not f:
                continue
            img = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
            st.image(img, use_container_width=True)
            issues = quality_check(img)
            if issues:
                st.error("Quality check failed: " + ", ".join(issues))
                if not st.checkbox("Use anyway", key=f"ok_{view}"):
                    st.caption("Please retake.")
                    continue
            else:
                st.success("Quality check passed")
            photos[view] = f.getvalue()
    st.progress(len(photos) / 4, text=f"{len(photos)}/4 photos accepted")

# ---------- form / garage report ----------
with tab2:
    if minor:
        st.write("Tick the damage you can see. Uses the same panel and damage list as the model.")
        declared = st.data_editor(EMPTY(), column_config=COLS, num_rows="dynamic",
                                  use_container_width=True, key="declared")
        confirmed = st.checkbox("I confirm nothing has been missed", key="confirm")
        reference, ref_label = declared, "User-declared"
    else:
        up = st.file_uploader("Garage report (PDF, image or CSV)", type=["pdf", "png", "jpg", "jpeg", "csv"])
        st.write("List the damage items from the report below. A CSV with `Panel` and `Damage` columns pre-fills it.")
        base = EMPTY()
        if up is not None and up.name.lower().endswith(".csv"):
            try:
                csv = pd.read_csv(up)
                base = csv[["Panel", "Damage"]].astype(str)
            except Exception:
                st.warning("CSV needs `Panel` and `Damage` columns.")
        reference = st.data_editor(base, column_config=COLS, num_rows="dynamic",
                                   use_container_width=True, key=f"garage_{up.name if up else 'none'}")
        confirmed = up is not None
        ref_label = "Garage report"

# ---------- results ----------
with tab3:
    ready = len(photos) == 4 and confirmed
    if not ready:
        st.info("Complete all 4 photos" + (" and confirm the damage form." if minor else " and upload the garage report."))
    if st.button("Run detection", type="primary", disabled=not ready):
        with st.spinner("Detecting damage..."):
            st.session_state.dets = [d for v in VIEWS for d in detect_damage(v, photos[v])]
    if ready and "dets" in st.session_state:
        dets = st.session_state.dets
        det_keys = {(d["Panel"], d["Damage"]) for d in dets}
        ref = reference.dropna().drop_duplicates()
        ref_keys = set(zip(ref["Panel"], ref["Damage"]))
        rows = []
        for p, dmg in ref_keys:
            hit = (p, dmg) in det_keys
            conf = max([d["conf"] for d in dets if (d["Panel"], d["Damage"]) == (p, dmg)], default=None)
            rows.append({"Item": f"{p} / {dmg}", "Source": ref_label, "Model confidence": conf,
                         "Status": "Matched" if hit else "Needs review"})
        for p, dmg in det_keys - ref_keys:
            conf = max(d["conf"] for d in dets if (d["Panel"], d["Damage"]) == (p, dmg))
            rows.append({"Item": f"{p} / {dmg}", "Source": "Model only", "Model confidence": conf,
                         "Status": "Info" if not minor else "Listed (not flagged)"})
        report = pd.DataFrame(rows).sort_values("Status")
        flagged = (report["Status"] == "Needs review").any()
        (st.error if flagged else st.success)(
            "Outcome: Needs review, sent to a human adjuster" if flagged else "Outcome: Matched")
        st.dataframe(report, use_container_width=True, hide_index=True)
        st.download_button("Download report (CSV)", report.to_csv(index=False), "damage_report.csv")
        if minor:
            st.caption("Damage the model found but the user did not tick is listed only. It is not flagged.")
        st.subheader("Model detections")
        cols = st.columns(4)
        for col, v in zip(cols, VIEWS):
            with col:
                st.image(annotate(photos[v], [d for d in dets if d["view"] == v]), caption=v,
                         use_container_width=True)
        st.caption("Mock detector in use. Set MODEL_API_URL in secrets to call your real model.")
