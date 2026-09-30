import base64
import glob
import hashlib
import html
import os

import streamlit as st
from PIL import Image

import logic as L

st.set_page_config(page_title="Car Damage Check | Vehicle inspection", page_icon="🔍", layout="wide")
try:  # optional real model endpoint (.streamlit/secrets.toml)
    if "MODEL_API_URL" in st.secrets:
        os.environ["MODEL_API_URL"] = st.secrets["MODEL_API_URL"]
except Exception:
    pass

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@700;800&display=swap');
:root{--bg:#f5f7f9;--fg:#111c23;--primary:#005c5a;--secondary:#dfefef;--muted:#eef1f4;--mfg:#667078;--border:#d6dcdf;
--bad:#c13234;--ok:#005a35;--oksoft:#dcf6e5;--warn:#934f00;--warnsoft:#fff3d8;--ink:#1e2e35;}
html,body,.stApp,[data-testid="stAppViewContainer"]{background:var(--bg)!important;color:var(--fg);font-family:'DM Sans',sans-serif;}
header[data-testid="stHeader"],#MainMenu,footer{display:none!important;}
.block-container{max-width:1240px;padding:1rem 1.5rem 4rem!important;}
h1,h2,h3,.disp{font-family:'Manrope',sans-serif!important;color:var(--fg);}
.topbar{display:flex;justify-content:space-between;align-items:center;background:#fff;border:1px solid var(--border);border-radius:5px;padding:.8rem 1.2rem;}
.brand{display:flex;gap:.75rem;align-items:center;} .logo{width:36px;height:36px;border-radius:5px;background:var(--primary);display:flex;align-items:center;justify-content:center;}
.bt{font-family:'Manrope';font-weight:800;font-size:.85rem;line-height:1.1;} .bs{font-size:.68rem;color:var(--mfg);letter-spacing:.04em;}
.ws{font-size:.75rem;font-weight:600;color:var(--mfg);display:flex;gap:.4rem;align-items:center;} .dot{width:8px;height:8px;border-radius:50%;background:var(--ok);}
.hero{position:relative;overflow:hidden;border-radius:5px;background:var(--ink);margin:1.1rem 0 1.5rem;min-height:240px;}
.hero img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.7;}
.hero .shade{position:absolute;inset:0;background:linear-gradient(90deg,var(--ink) 0%,rgba(30,46,53,.85) 45%,transparent 100%);}
.hero .txt{position:relative;padding:2.6rem 2.8rem;color:#fff;max-width:640px;}
.hero h1{color:#fff!important;font-size:2.5rem;line-height:1.12;font-weight:800;margin:.6rem 0 0;padding:0;}
.hero p{color:rgba(255,255,255,.85);margin:.9rem 0 0;max-width:420px;}
.kick{font-size:.7rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--primary);}
.hero .kick{color:rgba(255,255,255,.75);}
.stitle{font-family:'Manrope';font-weight:800;font-size:1.9rem;margin:.3rem 0 0;} .sub{color:var(--mfg);font-size:.9rem;margin:.3rem 0 1.2rem;}
[class*="st-key-card"]{background:#fff;border:1px solid var(--border);border-radius:5px;box-shadow:0 1px 2px rgba(0,0,0,.05);padding:1rem 1.1rem;}
.ph-head{display:flex;gap:.75rem;align-items:flex-start;border-bottom:1px solid var(--border);padding-bottom:.8rem;margin-bottom:.8rem;}
.badge{width:32px;height:32px;border-radius:5px;background:var(--secondary);color:var(--primary);font-weight:700;font-size:.75rem;display:flex;align-items:center;justify-content:center;flex:none;}
.ph-head b{font-size:.9rem;} .hint{color:var(--mfg);font-size:.75rem;} .tick{margin-left:auto;color:var(--ok);font-weight:700;}
.ph-empty{border:1px dashed var(--border);background:var(--muted);border-radius:5px;height:150px;display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--mfg);font-size:.8rem;margin-bottom:.6rem;}
.note{border-radius:5px;padding:.55rem .75rem;font-size:.78rem;line-height:1.5;margin:.5rem 0;}
.note.bad{background:rgba(193,50,52,.1);color:var(--bad);} .note.warn{background:var(--warnsoft);color:var(--warn);} .note.ok{background:var(--oksoft);color:var(--ok);}
.okline{color:var(--ok);font-size:.78rem;font-weight:600;margin:.4rem 0;}
.stButton>button,.stDownloadButton>button{border-radius:5px;font-weight:600;border:1px solid var(--border);background:#fff;color:var(--fg);width:100%;}
.stButton>button[data-testid="stBaseButton-primary"]{background:var(--primary);border-color:var(--primary);color:#fff;}
[class*="st-key-nav_"] button,[class*="st-key-navon_"] button{border:0!important;justify-content:flex-start;height:3rem;}
[class*="st-key-nav_"] button{background:transparent!important;color:var(--mfg)!important;}
[class*="st-key-navon_"] button{background:var(--secondary)!important;color:var(--primary)!important;}
.side-h{font-size:.68rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--mfg);margin:.4rem 0 .6rem;}
.prog{display:flex;justify-content:space-between;font-size:.75rem;font-weight:600;margin-top:1.2rem;border-top:1px solid var(--border);padding-top:1.1rem;}
.bar{height:6px;border-radius:9px;background:var(--muted);margin:.6rem 0;overflow:hidden;} .bar i{display:block;height:100%;background:var(--primary);}
.banner{display:flex;gap:.8rem;border-radius:5px;padding:1.1rem 1.3rem;margin:1rem 0;}
.banner.bad{background:var(--warnsoft);color:var(--warn);} .banner.ok{background:var(--oksoft);color:var(--ok);}
.banner h3{margin:0;color:inherit!important;font-size:1.15rem;} .banner p{margin:.2rem 0 0;font-size:.85rem;}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem;margin-bottom:1.2rem;}
.stat{background:#fff;border:1px solid var(--border);border-radius:5px;padding:.9rem 1rem;} .stat b{font-family:'Manrope';font-size:1.6rem;display:block;} .stat span{font-size:.75rem;color:var(--mfg);}
.tbl{background:#fff;border:1px solid var(--border);border-radius:5px;overflow-x:auto;margin-bottom:.6rem;}
.tbl h3{margin:0;padding:.9rem 1.2rem;font-size:1rem;border-bottom:1px solid var(--border);}
.tbl table{width:100%;border-collapse:collapse;font-size:.85rem;min-width:520px;} .tbl th{background:var(--muted);color:var(--mfg);font-size:.72rem;text-align:left;padding:.65rem 1.2rem;}
.tbl td{padding:.7rem 1.2rem;border-top:1px solid var(--border);} .s-Matched{color:var(--ok);font-weight:600;} .s-NeedsReview{color:var(--warn);font-weight:600;} .s-Info,.s-ListedOnly{color:var(--primary);font-weight:600;}
.item{display:flex;background:var(--muted);border-radius:5px;padding:.6rem .8rem;font-size:.88rem;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)
ss = st.session_state
for k, v in {"step": 0, "photos": {}, "seq": {}, "counter": 0, "nonce": {x: 0 for x in L.VIEWS}, "accepted": {},
             "declared": [], "garage": [], "report": None, "rep_n": 0, "towed_ui": "Not towed", "_prev_towed": "Not towed",
             "flags": {"none_minor": False, "none_major": False, "confirmed": False}}.items():
    ss.setdefault(k, v)


# ---------------- helpers ----------------
@st.cache_data(show_spinner=False)
def hero_uri():
    p = os.path.join("assets", "hero.jpg")
    return "data:image/jpeg;base64," + base64.b64encode(open(p, "rb").read()).decode() if os.path.exists(p) else ""


@st.cache_data(show_spinner=False)
def check(data):
    return L.check_single(data)


@st.cache_data(show_spinner=False)
def example(damage):
    for p in glob.glob(os.path.join("examples", damage.lower() + ".*")):
        if not p.endswith(".txt"):
            return Image.open(p).convert("RGB")
    return L.example_image(damage)


def photo_status():
    out = {}
    for v, d in ss.photos.items():
        r = check(d)
        blocking = list(r["blocking"])
        for e, ed in ss.photos.items():  # block the newer of two look-alike photos
            if e != v and ss.seq.get(e, 0) < ss.seq.get(v, 0) and r["hash"] is not None \
                    and check(ed)["hash"] is not None and L.hamming(r["hash"], check(ed)["hash"]) <= L.DUP_BITS:
                blocking.append(f"This looks the same as your {e.lower()} photo. Use a different angle.")
                break
        out[v] = {**r, "blocking": blocking}
    return out


def _acc(v):
    ss.accepted[v] = ss[f"acc_{v}"]


def _flag(k):
    ss.flags[k] = ss[f"cb_{k}"]


def _seg():
    if ss.towed_ui is None:
        ss.towed_ui = ss._prev_towed
    ss._prev_towed = ss.towed_ui


def go(i):
    ss.step = i


def drop_photo(v):
    ss.photos.pop(v, None)
    ss.nonce[v] += 1
    ss.accepted[v] = False


def add_item(key):
    it = (ss[f"{key}_panel"], ss[f"{key}_dmg"])
    if it not in ss[key]:
        ss[key].append(it)


def rm_item(key, i):
    ss[key].pop(i)


@st.dialog("Damage guide", width="large")
def guide(selected):
    st.caption("Choose the description closest to what you see.")
    cols = st.columns(3)
    for i, d in enumerate(L.DAMAGES):
        with cols[i % 3]:
            st.image(example(d))
            st.markdown(f"**{'✓ ' if d == selected else ''}{d}**  \n<span class='hint'>{L.DAMAGE_INFO[d]}</span>",
                        unsafe_allow_html=True)


@st.dialog("Photo requirements")
def requirements():
    st.markdown("- JPG, PNG, WebP or HEIC, under 12 MB.\n- At least 640 × 480 pixels; no panoramas or blank photos.\n"
                "- Blurry, dark, or overexposed photos need your confirmation.\n- Each angle needs a different photo.")
    st.caption("Image checks do not verify that a vehicle is pictured.")


def head(n, title, sub):
    st.markdown(f"<div class='kick'>Step 0{n} / 03</div><div class='stitle'>{title}</div><div class='sub'>{sub}</div>",
                unsafe_allow_html=True)


# ---------------- derived state ----------------
towed = ss.towed_ui == "Towed"
stat = photo_status()
good = [v for v in L.VIEWS if v in stat and not stat[v]["blocking"] and (not stat[v]["soft"] or ss.accepted.get(v))]
photo_ready = len(good) == 4
items = ss.garage if towed else ss.declared
rep = ss.report
form_ready = (bool(rep) and not rep["error"] and bool(items or ss.flags["none_major"])) if towed \
    else bool((items or ss.flags["none_minor"]) and ss.flags["confirmed"])
sig = hashlib.md5(b"".join(ss.photos[v] for v in L.VIEWS if v in ss.photos)).hexdigest()
dets_ok = ss.get("dets") is not None and ss.get("dets_sig") == sig
stages = ["Photos", "Garage report" if towed else "Damage details", "Results"]

# ---------------- header + hero ----------------
st.markdown("""<div class='topbar'><div class='brand'><div class='logo'><svg width='21' height='21' viewBox='0 0 24 24' fill='none'
stroke='white' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><circle cx='11' cy='11' r='7'/><path d='m21 21-4.3-4.3'/>
<path d='m8 11 2 2 4-4'/></svg></div><div><div class='bt'>CAR DAMAGE CHECK</div><div class='bs'>VEHICLE INSPECTION</div></div></div>
<div class='ws'><span class='dot'></span> Inspection workspace</div></div>""", unsafe_allow_html=True)
img = f"<img src='{hero_uri()}' alt=''>" if hero_uri() else ""
st.markdown(f"<div class='hero'>{img}<div class='shade'></div><div class='txt'><div class='kick'>Guided vehicle assessment</div>"
            "<h1>A clearer picture of<br>vehicle damage.</h1><p>Capture four angles, document the damage, and review "
            "your findings in one place.</p></div></div>", unsafe_allow_html=True)

left, right = st.columns([1, 3.6], gap="large")

# ---------------- sidebar ----------------
with left:
    st.markdown("<div class='side-h'>Your inspection</div>", unsafe_allow_html=True)
    done = [photo_ready, form_ready and photo_ready, dets_ok]
    for i, label in enumerate(stages):
        mark = "✓" if done[i] else f"0{i + 1}"
        st.button(f"{mark}   {label}", key=f"{'navon' if ss.step == i else 'nav'}_{i}", on_click=go, args=(i,))
    st.markdown(f"<div class='prog'><span>Photo progress</span><span style='color:var(--primary)'>{len(good)} of 4</span></div>"
                f"<div class='bar'><i style='width:{len(good) * 25}%'></i></div>"
                "<div class='hint'>Each angle is checked before it can be used.</div>", unsafe_allow_html=True)
    st.markdown("<div class='prog'><span>INSPECTION TYPE</span></div>", unsafe_allow_html=True)
    st.segmented_control("Inspection type", ["Not towed", "Towed"], key="towed_ui", on_change=_seg, label_visibility="collapsed")
    st.markdown("<div class='hint'>You can switch at any time. Your photos will stay in place.</div>", unsafe_allow_html=True)

# ---------------- main ----------------
with right:
    if ss.step == 0:
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        with c1:
            head(1, "Capture the vehicle", "Add one clear photo from each angle.")
        if c2.button("? Photo requirements", key="req"):
            requirements()
        cols = st.columns(2)
        for i, view in enumerate(L.VIEWS):
            s, data = stat.get(view), ss.photos.get(view)
            blocked = bool(s and s["blocking"])
            ok = view in good
            with cols[i % 2], st.container(key=f"card_photo_{view}"):
                st.markdown(f"<div class='ph-head'><span class='badge'>0{i + 1}</span><div><b>{view} view</b><br>"
                            f"<span class='hint'>{L.VIEW_HINT[view]}</span></div>{'<span class=tick>✓</span>' if ok else ''}</div>",
                            unsafe_allow_html=True)
                if data and s["hash"] is not None and not blocked:
                    st.image(data)
                else:
                    st.markdown(f"<div class='ph-empty'>📷<br>{'Photo needs replacing' if blocked else 'No photo added yet'}</div>",
                                unsafe_allow_html=True)
                if s and (blocked or s["soft"]):
                    txt = html.escape(" ".join(s["blocking"] + s["soft"]))
                    st.markdown(f"<div class='note {'bad' if blocked else 'warn'}'>{txt}</div>", unsafe_allow_html=True)
                    if not blocked:
                        st.checkbox("Use anyway", value=ss.accepted.get(view, False), key=f"acc_{view}", on_change=_acc, args=(view,))
                if ok:
                    st.markdown(f"<div class='okline'>✓ Photo accepted · {s['size'][0]} × {s['size'][1]}</div>", unsafe_allow_html=True)
                if data:
                    st.button("Replace", key=f"rep_{view}", on_click=drop_photo, args=(view,))
                else:
                    mode = st.segmented_control("Source", ["🖼️ Upload", "📷 Camera"], default="🖼️ Upload",
                                                key=f"mode_{view}", label_visibility="collapsed")
                    n = ss.nonce[view]
                    if mode == "📷 Camera":
                        f = st.camera_input(f"{view} photo", key=f"cam_{view}_{n}", label_visibility="collapsed")
                    else:
                        f = st.file_uploader(f"{view} photo", type=["jpg", "jpeg", "png", "webp"] + (["heic", "heif"] if L.HEIC else []),
                                             key=f"up_{view}_{n}", label_visibility="collapsed")
                    if f is not None:
                        ss.counter += 1
                        ss.photos[view], ss.seq[view], ss.accepted[view] = f.getvalue(), ss.counter, False
                        ss.nonce[view] += 1
                        st.rerun()
        st.button(f"Continue to {stages[1].lower()} →", key="to1", type="primary", disabled=not photo_ready, on_click=go, args=(1,))

    elif ss.step == 1:
        head(2, "Garage report" if towed else "Document the damage",
             "Attach the garage report and list the damage it describes." if towed else "Add any visible damage you notice on the vehicle.")
        if towed:
            with st.container(key="card_report"):
                st.markdown("**Garage report**  \n<span class='hint'>PDF, image or CSV · up to 15 MB</span>", unsafe_allow_html=True)
                if rep:
                    st.markdown(f"<div class='note {'bad' if rep['error'] else 'ok'}'>"
                                f"{html.escape(rep['error'] or rep['name'] + ' accepted. ' + rep['note'])}</div>", unsafe_allow_html=True)
                    if st.button("Replace report", key="rep_replace"):
                        ss.report, ss.garage = None, []
                        ss.rep_n += 1
                        st.rerun()
                else:
                    up = st.file_uploader("Upload report", type=["pdf", "csv", "jpg", "jpeg", "png"], key=f"rep_up_{ss.rep_n}",
                                          label_visibility="collapsed")
                    if up is not None:
                        r = L.validate_report(up.name, up.getvalue())
                        ss.report = {"name": up.name, "error": r["error"] and r["error"] + ".", "note": r["note"]}
                        ss.garage = list(r["items"])
                        st.rerun()
        key = "garage" if towed else "declared"
        with st.container(key="card_form"):
            a, b = st.columns([6, 1.4], vertical_alignment="center")
            a.markdown(f"**{'Damage in the report' if towed else 'Declared damage'}**  \n<span class='hint'>Select a vehicle part and the type of damage.</span>",
                       unsafe_allow_html=True)
            if b.button("? Guide", key="guide_btn"):
                guide(ss.get(f"{key}_dmg", L.DAMAGES[0]))
            c1, c2, c3 = st.columns([3, 3, 1.3], vertical_alignment="bottom")
            c1.selectbox("Vehicle part", L.PANELS, key=f"{key}_panel")
            c2.selectbox("Damage type", L.DAMAGES, key=f"{key}_dmg")
            c3.button("＋ Add", key=f"{key}_add", type="primary", on_click=add_item, args=(key,))
            st.divider()
            for i, (p, d) in enumerate(ss[key]):
                x, y = st.columns([9, 1], vertical_alignment="center")
                x.markdown(f"<div class='item'><b>{html.escape(p)}</b>&nbsp;·&nbsp;<span style='color:var(--mfg)'>{html.escape(d)}</span></div>", unsafe_allow_html=True)
                y.button("🗑", key=f"{key}_rm_{i}", on_click=rm_item, args=(key, i))
            if not ss[key]:
                st.caption("No damage items added yet.")
            nk = "none_major" if towed else "none_minor"
            st.checkbox("The report lists no damage" if towed else "No visible damage to declare", value=ss.flags[nk],
                        key=f"cb_{nk}", disabled=bool(ss[key]), on_change=_flag, args=(nk,))
            if not towed:
                st.checkbox("I confirm this list is complete", value=ss.flags["confirmed"], key="cb_confirmed",
                            on_change=_flag, args=("confirmed",))
        p1, p2 = st.columns(2)
        p1.button("← Photos", key="back0", on_click=go, args=(0,))
        p2.button("Review results →", key="to2", type="primary", disabled=not (form_ready and photo_ready), on_click=go, args=(2,))
        if not photo_ready:
            st.markdown("<div class='hint' style='color:var(--warn)'>Accept all four photos before continuing.</div>", unsafe_allow_html=True)

    else:
        head(3, "Inspection results", f"Compare {'the garage report' if towed else 'your notes'} against the photo findings.")
        if not (photo_ready and form_ready):
            msg = f"Accept all four photos ({len(good)} of 4 ready)." if not photo_ready else (
                "Upload a valid report and list its damage, or select no damage." if towed
                else "Add damage or select no visible damage, then confirm your list.")
            with st.container(key="card_gate"):
                st.markdown(f"**Complete your inspection first**  \n<span class='hint'>{msg}</span>", unsafe_allow_html=True)
                st.button("Go to " + ("photos" if not photo_ready else stages[1]), key="gate", on_click=go, args=(0 if not photo_ready else 1,))
        else:
            with st.container(key="card_run"):
                a, b = st.columns([4, 1.3], vertical_alignment="center")
                a.markdown(f"**Ready to compare**  \n<span class='hint'>Four photos and {'garage report' if towed else 'damage details'} complete</span>", unsafe_allow_html=True)
                if b.button("Run again" if dets_ok else "Run detection", key="run", type="primary"):
                    with st.spinner("Checking…"):
                        try:
                            ss.dets = [d for v in L.VIEWS for d in L.detect_damage(v, ss.photos[v])]
                            ss.dets_sig = sig
                        except Exception as e:
                            ss.pop("dets", None)
                            st.error(f"Model call failed: {e}")
                    st.rerun()
            if not os.environ.get("MODEL_API_URL"):
                st.caption("Demo mode: findings are simulated until a real detection service is connected.")
            if dets_ok:
                df = L.compare(items, ss.dets, not towed)
                bad = L.outcome(df) == "Needs review"
                st.markdown(f"<div class='banner {'bad' if bad else 'ok'}'><div><h3>{'Needs review' if bad else 'Matched'}</h3><p>"
                            f"{'Some reported damage was not found in the photos. A human adjuster should review it.' if bad else 'No differences needing review were found.'}</p></div></div>",
                            unsafe_allow_html=True)
                n = lambda *s: int(df.Status.isin(s).sum())
                st.markdown("<div class='stats'>" + "".join(f"<div class='stat'><b>{c}</b><span>{t}</span></div>" for t, c in
                            [("Matched", n("Matched")), ("Needs review", n("Needs review")), ("Model only", n("Info", "Listed only"))]) + "</div>",
                            unsafe_allow_html=True)
                rows = "".join(f"<tr><td><b>{html.escape(r.Panel)}</b></td><td>{html.escape(r.Damage)}</td><td style='color:var(--mfg)'>{html.escape(r.Source)}</td>"
                               f"<td>{'—' if r.Confidence != r.Confidence or r.Confidence is None else f'{r.Confidence:.0%}'}</td>"
                               f"<td class='s-{r.Status.replace(' ', '')}'>{r.Status}</td></tr>" for r in df.itertuples())
                body = f"<table><thead><tr><th>Part</th><th>Damage</th><th>Source</th><th>Confidence</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>" \
                    if rows else "<p style='padding:1rem 1.2rem'>No damage declared and none detected.</p>"
                st.markdown(f"<div class='tbl'><h3>Comparison report</h3>{body}</div>", unsafe_allow_html=True)
                st.caption("Model-only findings are shown for information and are not flagged.")
                st.download_button("⬇ Download CSV", df.to_csv(index=False), "car-damage-report.csv", "text/csv")
                st.markdown("### Photo findings")
                cols = st.columns(2)
                for i, v in enumerate(L.VIEWS):
                    dv = [d for d in ss.dets if d["view"] == v]
                    with cols[i % 2], st.container(key=f"card_find_{v}"):
                        st.image(L.annotate(ss.photos[v], dv))
                        st.markdown(f"**{v}** <span class='hint'>· {len(dv)} finding(s)</span>", unsafe_allow_html=True)
            elif ss.get("dets") is not None:
                st.warning("Photos changed since the last run. Run detection again.")
