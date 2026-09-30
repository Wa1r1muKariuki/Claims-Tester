import glob
import hashlib
import html
import os

import streamlit as st
from PIL import Image

import logic as L

st.set_page_config(page_title="Car Damage Check", page_icon="🚗", layout="wide")
try:  # optional: real model endpoint from .streamlit/secrets.toml
    if "MODEL_API_URL" in st.secrets:
        os.environ["MODEL_API_URL"] = st.secrets["MODEL_API_URL"]
except Exception:
    pass

st.markdown("""
<style>
#MainMenu, footer {visibility: hidden;}
.block-container {padding-top: 1.2rem; max-width: 1150px;}
.hero {background: linear-gradient(120deg,#0f766e,#1d4ed8); padding: 1.3rem 1.6rem; border-radius: 18px; margin-bottom: 1rem;}
.hero h1 {color:#fff !important; margin:0; font-size:1.8rem; padding:0;}
.hero p {color:#e0f2fe; margin:.3rem 0 0;}
.steps {display:flex; gap:.6rem; margin:.4rem 0 1rem; flex-wrap:wrap;}
.step {flex:1; min-width:140px; padding:.6rem .9rem; border-radius:12px; border:1px solid rgba(128,128,128,.35); font-weight:600; font-size:.9rem; opacity:.75;}
.step.done {background:rgba(16,185,129,.15); border-color:#10b981; opacity:1;}
.pill {display:inline-block; padding:.12rem .65rem; border-radius:999px; font-size:.78rem; font-weight:700;}
.pill.ok {background:#d1fae5; color:#065f46;} .pill.bad {background:#fee2e2; color:#991b1b;}
.pill.info {background:#dbeafe; color:#1e40af;} .pill.warn {background:#fef3c7; color:#92400e;}
.hint {opacity:.7; font-size:.85rem;}
.outcome {padding:1rem 1.3rem; border-radius:14px; font-size:1.2rem; font-weight:700; margin:.4rem 0 1rem;}
.outcome.ok {background:#d1fae5; color:#065f46;} .outcome.bad {background:#fee2e2; color:#991b1b;}
table.rep {width:100%; border-collapse:collapse; margin-bottom:1rem;}
table.rep th {text-align:left; font-size:.8rem; opacity:.7; padding:.5rem; border-bottom:2px solid rgba(128,128,128,.3);}
table.rep td {padding:.55rem .5rem; border-bottom:1px solid rgba(128,128,128,.2);}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='hero'><h1>🚗 Car Damage Check</h1>"
            "<p>Capture the car, declare the damage, and compare it against the model.</p></div>",
            unsafe_allow_html=True)


def pill(text, kind):
    return f"<span class='pill {kind}'>{html.escape(text)}</span>"


@st.cache_data(show_spinner=False)
def example(damage):
    for p in glob.glob(os.path.join("examples", damage.lower() + ".*")):
        return Image.open(p).convert("RGB")
    return L.example_image(damage)


@st.cache_data(show_spinner=False)
def check(data):
    return L.check_single(data)


@st.dialog("Damage guide", width="large")
def guide(selected):
    st.caption("Pick the type that best matches what you see. Your current choice is marked.")
    cols = st.columns(3)
    for i, dmg in enumerate(L.DAMAGES):
        with cols[i % 3]:
            st.image(example(dmg))
            st.markdown(f"**{'✅ ' if dmg == selected else ''}{dmg}**  \n<span class='hint'>{L.DAMAGE_INFO[dmg]}</span>",
                        unsafe_allow_html=True)


def add_item(key):
    it = (st.session_state[f"{key}_panel"], st.session_state[f"{key}_dmg"])
    if it not in st.session_state[key]:
        st.session_state[key].append(it)


def remove_item(key, i):
    st.session_state[key].pop(i)


def item_editor(key):
    st.session_state.setdefault(key, [])
    c1, c2, c3, c4 = st.columns([3, 3, 1.7, 1.3], vertical_alignment="bottom")
    c1.selectbox("Panel", L.PANELS, key=f"{key}_panel")
    c2.selectbox("Damage type", L.DAMAGES, key=f"{key}_dmg")
    if c3.button("ⓘ Examples", key=f"{key}_ex"):
        guide(st.session_state[f"{key}_dmg"])
    c4.button("＋ Add", key=f"{key}_add", type="primary", on_click=add_item, args=(key,))
    items = st.session_state[key]
    for i, (p, d) in enumerate(items):
        a, b = st.columns([8, 1], vertical_alignment="center")
        a.markdown(f"**{p}** &nbsp; {pill(d, 'info')}", unsafe_allow_html=True)
        b.button("✕", key=f"{key}_rm_{i}", on_click=remove_item, args=(key, i))
    if not items:
        st.caption("No items added yet.")
    return items


# ---------------- triage ----------------
with st.container(border=True):
    towed = st.radio("Was the vehicle towed?", ["No", "Yes"], horizontal=True, key="towed",
                     captions=["Car can still move: Journey 1 (minor)", "Journey 2 (major)"])
    st.caption("Picked the wrong one? Switch any time. Your photos are kept.")
minor = towed == "No"

steps_slot = st.empty()
tab1, tab2, tab3 = st.tabs(["1 · Photos", "2 · Damage form" if minor else "2 · Garage report", "3 · Results"])

# ---------------- photos ----------------
ACCEPT = ["jpg", "jpeg", "png", "webp"] + (["heic", "heif"] if L.HEIC else [])
photos, raw, slots = {}, {}, {}
with tab1:
    st.write("Add one photo per angle from your **gallery** or take it with the **camera**.")
    grid = st.columns(2)
    for i, v in enumerate(L.VIEWS):
        with grid[i % 2], st.container(border=True):
            st.markdown(f"**{i + 1}. {v}**  \n<span class='hint'>{L.VIEW_HINT[v]}</span>", unsafe_allow_html=True)
            src = st.radio("Source", ["🖼️ Gallery", "📷 Camera"], horizontal=True, key=f"src_{v}",
                           label_visibility="collapsed")
            if src.endswith("Gallery"):
                f = st.file_uploader(f"{v} photo", type=ACCEPT, key=f"up_{v}", label_visibility="collapsed")
            else:
                f = st.camera_input(f"{v} photo", key=f"cam_{v}", label_visibility="collapsed")
            slots[v] = st.container()
            if f is not None:
                raw[v] = f.getvalue()

    info = {v: check(d) for v, d in raw.items()}
    for idx, v in enumerate(L.VIEWS):
        if v not in raw:
            continue
        res, blocking = info[v], list(info[v]["blocking"])
        for earlier in L.VIEWS[:idx]:
            if earlier in info and res["hash"] is not None and info[earlier]["hash"] is not None \
                    and L.hamming(res["hash"], info[earlier]["hash"]) <= L.DUP_BITS:
                blocking.append(f"looks the same as the {earlier} photo; each angle needs its own photo")
        with slots[v]:
            if res["hash"] is not None:
                st.image(raw[v])
            if blocking:
                st.markdown(pill("Rejected", "bad"), unsafe_allow_html=True)
                for b in blocking:
                    st.error(b)
            elif res["soft"]:
                st.markdown(pill("Check quality", "warn"), unsafe_allow_html=True)
                st.warning("Photo is " + ", ".join(res["soft"]) + ".")
                if st.checkbox("Use anyway", key=f"ok_{v}"):
                    photos[v] = raw[v]
            else:
                st.markdown(pill("Photo OK", "ok"), unsafe_allow_html=True)
                photos[v] = raw[v]
    st.progress(len(photos) / 4, text=f"{len(photos)}/4 photos accepted")
    with st.expander("What is checked on every photo?"):
        st.markdown("- Readable image, under 12 MB, at least 640×480\n- Not blank, not a screenshot or panorama\n"
                    "- Blur, too dark, overexposed (you can override these)\n- Not a duplicate of another angle\n\n"
                    "These checks cannot tell whether the photo actually shows a car. That needs a classifier.")

# ---------------- form / garage report ----------------
form_missing = []
with tab2:
    if minor:
        st.write("Add every damage you can see. Use **ⓘ Examples** if you are unsure which type fits.")
        items = item_editor("declared")
        none_box = st.checkbox("No visible damage to declare", key="none_decl", disabled=bool(items))
        confirm = st.checkbox("I confirm this list is complete", key="confirm")
        ref_items = list(items)
        if not (items or none_box):
            form_missing.append("Add at least one damage item, or tick “No visible damage”.")
        if not confirm:
            form_missing.append("Confirm the damage list is complete.")
    else:
        up = st.file_uploader("Upload the garage report (PDF, image or CSV)", type=["pdf", "png", "jpg", "jpeg", "csv"],
                              key="garage_file")
        st.session_state.setdefault("garage", [])
        if up is None:
            form_missing.append("Upload the garage report.")
        else:
            data = up.getvalue()
            rep = L.validate_report(up.name, data)
            if rep["error"]:
                st.error(f"Garage report rejected: {rep['error']}.")
                form_missing.append("Upload a valid garage report.")
            else:
                st.success(f"{up.name} accepted. {rep['note']}")
                loaded = st.session_state.setdefault("garage_loaded", set())
                h = hashlib.md5(data).hexdigest()
                if h not in loaded:
                    loaded.add(h)
                    for it in rep["items"]:
                        if it not in st.session_state["garage"]:
                            st.session_state["garage"].append(it)
                if not up.name.lower().endswith((".pdf", ".csv")):
                    st.image(data, width=360)
        st.write("Damage items listed in the report:")
        items = item_editor("garage")
        none_box = st.checkbox("The report lists no damage", key="none_garage", disabled=bool(items))
        ref_items = list(items)
        if up is not None and not (items or none_box):
            form_missing.append("Add the report's damage items, or tick “The report lists no damage”.")

# ---------------- results ----------------
sig = hashlib.md5(b"".join(photos[v] for v in L.VIEWS if v in photos)).hexdigest()
result_ok = False
with tab3:
    missing = ([f"Accept all 4 photos ({len(photos)}/4 so far)."] if len(photos) < 4 else []) + form_missing
    if missing:
        st.info("**Still to do:**\n" + "\n".join(f"- {m}" for m in missing))
    if st.button("Run detection", type="primary", disabled=bool(missing)):
        with st.spinner("Detecting damage..."):
            try:
                st.session_state.dets = [d for v in L.VIEWS for d in L.detect_damage(v, photos[v])]
                st.session_state.dets_sig = sig
            except Exception as e:
                st.session_state.pop("dets", None)
                st.error(f"Model call failed: {e}")
    dets = st.session_state.get("dets")
    if not missing and dets is not None:
        if st.session_state.get("dets_sig") != sig:
            st.warning("Photos changed since the last run. Run detection again.")
        else:
            result_ok = True
            df = L.compare(ref_items, dets, minor)
            res = L.outcome(df)
            st.markdown(f"<div class='outcome {'ok' if res == 'Matched' else 'bad'}'>Outcome: {res}"
                        f"{' → sent to a human adjuster' if res != 'Matched' else ''}</div>", unsafe_allow_html=True)
            m = st.columns(3)
            m[0].metric("Matched", int((df.Status == "Matched").sum()))
            m[1].metric("Needs review", int((df.Status == "Needs review").sum()))
            m[2].metric("Model only", int(df.Status.isin(["Info", "Listed only"]).sum()))
            kind = {"Matched": "ok", "Needs review": "bad", "Info": "info", "Listed only": "info"}
            rows = "".join(
                f"<tr><td>{html.escape(r.Panel)}</td><td>{html.escape(r.Damage)}</td><td>{html.escape(r.Source)}</td>"
                f"<td>{'-' if r.Confidence is None or r.Confidence != r.Confidence else f'{r.Confidence:.0%}'}</td>"
                f"<td>{pill(r.Status, kind[r.Status])}</td></tr>" for r in df.itertuples())
            if rows:
                st.markdown("<table class='rep'><tr><th>PANEL</th><th>DAMAGE</th><th>SOURCE</th><th>MODEL CONF.</th>"
                            f"<th>STATUS</th></tr>{rows}</table>", unsafe_allow_html=True)
            else:
                st.success("No damage declared and none detected.")
            st.caption("Model-only findings are listed for information and are not flagged." if minor else
                       "Model-only findings are shown as info rows. Items in the report but not detected are flagged.")
            st.download_button("⬇️ Download report (CSV)", df.to_csv(index=False), "damage_report.csv", "text/csv")
            st.subheader("Model detections")
            cols = st.columns(2)
            for i, v in enumerate(L.VIEWS):
                cols[i % 2].image(L.annotate(photos[v], [d for d in dets if d["view"] == v]), caption=v)
    if not os.environ.get("MODEL_API_URL"):
        st.caption("Demo mode: a mock detector is generating these results. Set MODEL_API_URL to use your model.")

steps = [("1 · Photos", len(photos) == 4), ("2 · Form" if minor else "2 · Garage report", not form_missing),
         ("3 · Results", result_ok)]
steps_slot.markdown("<div class='steps'>" + "".join(
    f"<div class='step {'done' if ok else ''}'>{'✓ ' if ok else ''}{n}</div>" for n, ok in steps) + "</div>",
    unsafe_allow_html=True)
