import base64
import hashlib
import json
import html
import os

import streamlit as st
from PIL import Image, ImageOps

import api
import logic as L

st.set_page_config(page_title="Car Damage Check | Vehicle inspection", page_icon="🔍", layout="wide")
try:  # backend settings from .streamlit/secrets.toml or Streamlit Cloud secrets
    for _k in ("API_BASE_URL", "API_KEY", "RUN_GLM"):
        if _k in st.secrets:
            os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass

LIGHT = """--bg:#f4f6f9;--card:#ffffff;--card2:#f1f4f8;--fg:#0f1a22;--mfg:#63707a;--border:#dde3e8;--accent:#00706d;
--p1:#0a8f89;--p2:#00605d;--secondary:#dcf1f0;--glow:rgba(0,112,109,.45);--shadow:0 1px 2px rgba(15,26,34,.06),0 8px 24px -12px rgba(15,26,34,.12);
--bad:#c13234;--ok:#00623b;--oksoft:#dcf6e5;--warn:#934f00;--warnsoft:#fff3d8;--ink:#0d1b22;"""
DARK = """--bg:#0a1116;--card:#121c23;--card2:#19252d;--fg:#e8eff3;--mfg:#93a2ac;--border:#233340;--accent:#4fe3d5;
--p1:#14b3a8;--p2:#0b7c75;--secondary:rgba(79,227,213,.12);--glow:rgba(20,179,168,.5);--shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px -12px rgba(0,0,0,.6);
--bad:#ff8a8c;--ok:#5fe0a0;--oksoft:rgba(95,224,160,.12);--warn:#ffc36b;--warnsoft:rgba(255,195,107,.12);--ink:#070d11;"""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@700;800&display=swap');
:root{__VARS__ color-scheme:__SCHEME__;}
html,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:var(--bg)!important;color:var(--fg);font-family:'DM Sans',sans-serif;}
.stApp,[data-testid="stMain"]{overflow-x:hidden;}
header[data-testid="stHeader"],[data-testid="stDecoration"],[data-testid="stToolbar"],#MainMenu,footer{display:none!important;}
[data-testid="stElementContainer"]:has(style){position:absolute;height:0;width:0;overflow:hidden;margin:0;padding:0;}
.block-container,[data-testid="stMainBlockContainer"],[data-testid="stAppViewBlockContainer"]{max-width:1240px;padding:0 1.5rem 4rem!important;margin-top:0!important;}
[data-testid="stAppViewContainer"]>.main,[data-testid="stMain"],section.main{padding-top:0!important;}
[data-testid="stMainBlockContainer"]>[data-testid="stVerticalBlock"]>[data-testid="stElementContainer"]:first-child{margin-top:0;}
h1,h2,h3,.disp{font-family:'Manrope',sans-serif!important;color:var(--fg);}
hr{border-color:var(--border)!important;}
:where([data-testid="stWidgetLabel"] p,[data-testid="stCheckbox"] p,[data-testid="stCaptionContainer"],[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li){color:var(--fg);}
:where([data-testid="stCaptionContainer"]){color:var(--mfg);}

/* ---------- hero (full bleed) ---------- */
.hero{position:relative;overflow:hidden;width:100vw;margin-left:calc(50% - 50vw);margin-bottom:1.6rem;min-height:210px;background:var(--ink);isolation:isolate;}
.hero img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.55;z-index:-3;}
.hero .shade{position:absolute;inset:0;z-index:-2;background:linear-gradient(90deg,var(--ink) 0%,rgba(13,27,34,.86) 42%,rgba(13,27,34,.15) 100%),
 radial-gradient(60% 90% at 85% 0%,rgba(20,179,168,.35),transparent 60%);}
.hero .grid{position:absolute;inset:0;z-index:-1;opacity:.18;background-image:linear-gradient(rgba(255,255,255,.25) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.25) 1px,transparent 1px);
 background-size:44px 44px;-webkit-mask-image:linear-gradient(180deg,#000,transparent 85%);mask-image:linear-gradient(180deg,#000,transparent 85%);}
.hero:after{content:"";position:absolute;left:0;right:0;bottom:0;height:44px;background:linear-gradient(180deg,transparent,var(--bg));}
.hero-in{max-width:1240px;margin:0 auto;padding:.9rem 1.5rem 2.6rem;}
.nav{display:flex;align-items:center;min-height:38px;}
.brand{display:flex;gap:.7rem;align-items:center;}
.logo{width:38px;height:38px;border-radius:11px;background:linear-gradient(135deg,var(--p1),var(--p2));display:flex;align-items:center;justify-content:center;box-shadow:0 8px 20px -6px var(--glow);}
.bt{font-family:'Manrope';font-weight:800;font-size:.85rem;line-height:1.1;color:#fff;letter-spacing:.02em;}
.pill{display:flex;gap:.45rem;align-items:center;font-size:.74rem;font-weight:600;color:#fff;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.22);
 backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);padding:.42rem .85rem;border-radius:99px;}
.dot{width:8px;height:8px;border-radius:50%;background:#4ade80;box-shadow:0 0 0 4px rgba(74,222,128,.25);}
.hero .txt{padding-top:.8rem;max-width:660px;color:#fff;}
.kick{font-size:.7rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);}
.hero h1{color:#fff!important;font-size:2.4rem;line-height:1.08;font-weight:800;margin:.4rem 0 0;padding:0;letter-spacing:-.02em;}
.hero h1 em{font-style:normal;background:linear-gradient(90deg,#7ff5e9,#4aa8ff);-webkit-background-clip:text;background-clip:text;color:transparent;}
.st-key-topstatus{position:fixed;top:.9rem;right:3.7rem;z-index:1000;width:auto!important;}
.st-key-topstatus .pill{height:34px;padding:0 .85rem;background:rgba(13,27,34,.78);border:1px solid rgba(255,255,255,.25);box-shadow:0 6px 18px -8px rgba(0,0,0,.5);}
.st-key-theme_toggle{position:fixed;top:.9rem;right:1.2rem;z-index:1000;width:auto!important;}
.st-key-theme_toggle button{width:34px!important;height:34px!important;min-height:34px!important;padding:0!important;border-radius:50%!important;color:#fff!important;
 background:rgba(13,27,34,.78)!important;border:1px solid rgba(255,255,255,.3)!important;backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);box-shadow:0 6px 18px -8px rgba(0,0,0,.5)!important;}
.st-key-theme_toggle button:hover{transform:rotate(18deg) scale(1.08)!important;background:rgba(13,27,34,.95)!important;color:#fff!important;}
.st-key-theme_toggle button *{color:#fff!important;font-size:1.05rem;}

/* ---------- typography + cards ---------- */
.stitle{font-family:'Manrope';font-weight:800;font-size:1.9rem;margin:.3rem 0 0;letter-spacing:-.01em;} .sub{color:var(--mfg);font-size:.92rem;margin:.3rem 0 1.2rem;}
[class*="st-key-card"]{background:var(--card);border:1px solid var(--border);border-radius:18px;box-shadow:var(--shadow);padding:1.1rem 1.2rem;transition:border-color .2s,transform .2s;}
[class*="st-key-card_photo"]:hover{border-color:var(--accent);transform:translateY(-2px);}
.ph-head{display:flex;gap:.75rem;align-items:flex-start;border-bottom:1px solid var(--border);padding-bottom:.8rem;margin-bottom:.8rem;}
.badge{width:34px;height:34px;border-radius:11px;background:var(--secondary);color:var(--accent);font-weight:700;font-size:.75rem;display:flex;align-items:center;justify-content:center;flex:none;}
.ph-head b{font-size:.92rem;} .hint{color:var(--mfg);font-size:.75rem;} .tick{margin-left:auto;color:var(--ok);font-weight:700;}
.ph-empty{border:1.5px dashed var(--border);background:var(--card2);border-radius:14px;height:150px;display:flex;flex-direction:column;gap:.4rem;align-items:center;justify-content:center;color:var(--mfg);font-size:.8rem;margin-bottom:.6rem;}
.note{border-radius:12px;padding:.6rem .8rem;font-size:.78rem;line-height:1.5;margin:.5rem 0;}
.note.bad{background:rgba(193,50,52,.1);color:var(--bad);} .note.warn{background:var(--warnsoft);color:var(--warn);} .note.ok{background:var(--oksoft);color:var(--ok);}
.okline{color:var(--ok);font-size:.78rem;font-weight:600;margin:.4rem 0;}

/* ---------- buttons ---------- */
.stButton>button,.stDownloadButton>button,[data-testid="stFileUploaderDropzone"] button{border-radius:12px;font-weight:600;min-height:2.75rem;border:1px solid var(--border);background:var(--card);color:var(--fg);
 box-shadow:0 1px 2px rgba(0,0,0,.06);transition:transform .15s,box-shadow .15s,border-color .15s,background .15s;}
.stButton>button,.stDownloadButton>button{width:100%;}
.stButton>button:hover,.stDownloadButton>button:hover,[data-testid="stFileUploaderDropzone"] button:hover{transform:translateY(-1px);border-color:var(--accent);color:var(--accent);box-shadow:0 8px 18px -10px var(--glow);}
.stButton>button:active,.stDownloadButton>button:active{transform:translateY(0);}
.stButton>button:focus-visible,.stDownloadButton>button:focus-visible{outline:3px solid var(--glow);outline-offset:2px;}
.stButton>button[data-testid="stBaseButton-primary"]{background:linear-gradient(135deg,var(--p1),var(--p2));border:0;color:#fff;box-shadow:0 10px 22px -10px var(--glow);}
.stButton>button[data-testid="stBaseButton-primary"] *{color:#fff!important;}
.stButton>button[data-testid="stBaseButton-primary"]:hover{filter:brightness(1.08);box-shadow:0 14px 26px -10px var(--glow);}
.stButton>button:disabled,.stDownloadButton>button:disabled{opacity:.45;transform:none;box-shadow:none;cursor:not-allowed;}
[class*="st-key-nav_"] button,[class*="st-key-navon_"] button{border:0!important;justify-content:flex-start;height:3rem;box-shadow:none!important;border-radius:12px!important;}
[class*="st-key-nav_"] button{background:transparent!important;color:var(--mfg)!important;}
[class*="st-key-navon_"] button{background:var(--secondary)!important;color:var(--accent)!important;}
[class*="st-key-navon_"] button *{color:var(--accent)!important;}
[class*="_rm_"] button{color:var(--bad)!important;}
[data-testid="stButtonGroup"] button,[data-testid="stSegmentedControl"] button,[data-testid^="stBaseButton-segmented"],[data-testid^="stBaseButton-pills"]{
 background:var(--card2)!important;color:var(--fg)!important;border:1px solid var(--border)!important;border-radius:10px!important;}
[data-testid="stButtonGroup"] button *,[data-testid="stSegmentedControl"] button *{color:inherit!important;}
[data-testid="stButtonGroup"] button:hover{border-color:var(--accent)!important;}
[data-testid="stButtonGroup"] button[data-testid$="Active"],[data-testid="stButtonGroup"] button[aria-checked="true"],[data-testid="stButtonGroup"] button[aria-pressed="true"],
[data-testid$="Active"][data-testid^="stBaseButton-"]{background:var(--secondary)!important;color:var(--accent)!important;border:1px solid var(--accent)!important;font-weight:700;}

/* ---------- inputs / dialogs (follow theme) ---------- */
[data-baseweb="select"]>div{background:var(--card2)!important;border-color:var(--border)!important;border-radius:12px!important;color:var(--fg)!important;}
[data-baseweb="select"] *{color:var(--fg)!important;}
[data-baseweb="popover"] ul,[data-baseweb="popover"] [role="listbox"],[data-baseweb="menu"]{background:var(--card)!important;color:var(--fg)!important;}
[data-baseweb="popover"] li:hover{background:var(--secondary)!important;}
[data-testid="stFileUploaderDropzone"]{background:var(--card2)!important;border:1.5px dashed var(--border)!important;border-radius:14px!important;color:var(--fg)!important;}
[data-testid="stFileUploaderDropzone"] *{color:var(--mfg);}
[data-testid="stFileUploaderDropzone"] button *{color:inherit;}
[data-testid="stCameraInput"]>div{border-radius:14px;overflow:hidden;background:var(--card2);}
[data-testid="stDialog"] [role="dialog"]{background:var(--card)!important;color:var(--fg)!important;border:1px solid var(--border);border-radius:20px!important;}
[data-testid="stDialog"] [role="dialog"] *{color:inherit;}
[data-testid="stDialog"] [role="dialog"] .hint{color:var(--mfg);}
[data-testid="stDialog"] [role="dialog"] button[aria-label="Close"]{color:var(--fg)!important;}
[data-testid="stImage"] img{border-radius:12px;}

/* ---------- layout blocks ---------- */
.side-h{font-size:.68rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--mfg);margin:.4rem 0 .6rem;}
.prog{display:flex;justify-content:space-between;font-size:.75rem;font-weight:600;margin-top:1.2rem;border-top:1px solid var(--border);padding-top:1.1rem;}
.bar{height:7px;border-radius:9px;background:var(--card2);margin:.6rem 0;overflow:hidden;} .bar i{display:block;height:100%;background:linear-gradient(90deg,var(--p1),var(--accent));border-radius:9px;transition:width .4s;}
.banner{display:flex;gap:.8rem;border-radius:16px;padding:1.1rem 1.3rem;margin:1rem 0;}
.banner.bad{background:var(--warnsoft);color:var(--warn);} .banner.ok{background:var(--oksoft);color:var(--ok);}
.banner h3{margin:0;color:inherit!important;font-size:1.15rem;} .banner p{margin:.2rem 0 0;font-size:.85rem;color:inherit!important;}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem;margin-bottom:1.2rem;}
.stat{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:.9rem 1rem;box-shadow:var(--shadow);} .stat b{font-family:'Manrope';font-size:1.6rem;display:block;} .stat span{font-size:.75rem;color:var(--mfg);}
.stat b.sm{font-size:.95rem;padding:.55rem 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.tbl{background:var(--card);border:1px solid var(--border);border-radius:16px;overflow-x:auto;margin-bottom:.6rem;box-shadow:var(--shadow);}
.tbl h3{margin:0;padding:.9rem 1.2rem;font-size:1rem;border-bottom:1px solid var(--border);}
.tbl table{width:100%;border-collapse:collapse;font-size:.85rem;min-width:360px;} .tbl th{background:var(--card2);color:var(--mfg);font-size:.72rem;text-align:left;padding:.65rem 1.2rem;}
.tbl td{padding:.7rem 1.2rem;border-top:1px solid var(--border);} .s-Matched{color:var(--ok);font-weight:600;} .s-NeedsReview{color:var(--warn);font-weight:600;} .s-Info,.s-ListedOnly{color:var(--accent);font-weight:600;}
.tag{display:inline-block;background:var(--secondary);color:var(--accent);border-radius:99px;padding:.15rem .65rem;font-size:.78rem;font-weight:600;}
.item{display:flex;background:var(--card2);border-radius:12px;padding:.6rem .8rem;font-size:.88rem;}
@media(max-width:700px){.hero h1{font-size:2rem}.hero-in{padding-bottom:2.4rem}.stats{grid-template-columns:1fr}
.st-key-topstatus .pill{width:34px;padding:0;justify-content:center}.st-key-topstatus .ptxt{display:none}}
.mc-h{font-size:.72rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--mfg);margin:.2rem 0 .5rem;}
.mc-empty{border:1px dashed var(--border);background:var(--card2,var(--card));border-radius:14px;padding:1.8rem 1rem;text-align:center;color:var(--mfg);font-size:.85rem;}
.kv{display:flex;flex-wrap:wrap;gap:.3rem .9rem;font-size:.8rem;color:var(--mfg);margin:.4rem 0;} .kv b{color:var(--fg);}
</style>
"""
ss = st.session_state
ss.setdefault("dark", False)
st.markdown(CSS.replace("__VARS__", DARK if ss.dark else LIGHT).replace("__SCHEME__", "dark" if ss.dark else "light"), unsafe_allow_html=True)
for k, v in {"step": 0, "mn_types": [], "mn_inst": {}, "mn_seq": 0, "thr_mode": "prod", "thr_val": 0.5, "estimate": [], "photos": {}, "seq": {}, "counter": 0, "nonce": {x: 0 for x in L.VIEWS}, "accepted": {},
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


EX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples")


def find_example(damage, variant):
    """Case-insensitive lookup: dent_1.jpg / Dent_1.JPEG / dent_1.png ... (plain dent.jpg counts as image 1)."""
    want = [f"{damage.lower()}_{variant + 1}"] + ([damage.lower()] if variant == 0 else [])
    try:
        files = sorted(os.listdir(EX_DIR))
    except OSError:
        return None
    for w in want:
        for f in files:
            stem, ext = os.path.splitext(f)
            if stem.lower() == w and ext.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                return os.path.join(EX_DIR, f)
    return None


@st.cache_data(show_spinner=False)
def load_example(path, mtime):  # mtime in the key -> a replaced file is picked up without clearing the cache
    try:
        im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        im.thumbnail((900, 900))
        return im
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def drawn_example(damage, variant):
    return L.example_image(damage, variant)


def example(damage, variant=0):
    p = find_example(damage, variant)
    if p:
        im = load_example(p, os.path.getmtime(p))
        if im is not None:
            return im
    return drawn_example(damage, variant)


# ---------------- backend ----------------
@st.cache_data(ttl=45, show_spinner=False)
def backend_health(base):
    try:
        return {"ok": True, **api.health()}
    except api.ApiError as e:
        return {"ok": False, "error": str(e)}


@st.cache_data(ttl=600, show_spinner=False)
def backend_taxonomy(base):
    try:
        return {"parts": api.parts(), "detectors": api.detectors()}
    except api.ApiError:
        return {"parts": [], "detectors": []}


@st.cache_data(show_spinner=False)
def api_quality(base, data):
    try:
        return api.quality(data)
    except api.ApiError:
        return None


BACKEND = api.enabled()
_H = backend_health(api.base_url()) if BACKEND else None
_T = backend_taxonomy(api.base_url()) if (_H and _H["ok"]) else {"parts": [], "detectors": []}
PART_ID = {(p.get("label") or p.get("part_name")): p["part_id"] for p in _T["parts"]}
LIVE = bool(_H and _H["ok"] and PART_ID)
PANEL_OPTIONS = list(PART_ID) if LIVE else L.PANELS
PID = PART_ID if LIVE else {p: i + 1 for i, p in enumerate(L.PANELS)}
# damage types: live = exactly what the backend's detectors offer; demo = the six local types
DEFAULT_LABEL = {"Scratch": "Scratch", "Dent": "Dent", "Dislodged": "Dislodged", "Torn": "Torn",
                 "Smashed": "Smashed glass", "Broken": "Broken lamp"}
DTYPES = [(d["key"], d.get("label") or d["key"]) for d in _T["detectors"]] if (LIVE and _T["detectors"]) else list(DEFAULT_LABEL.items())
DLABEL = dict(DTYPES)


def guide_name(tid):
    """Map a detector to one of the local example types (for the guide popup)."""
    s = f"{tid} {DLABEL.get(tid, '')}".lower()
    for n in L.DAMAGES:
        if n.lower() in s:
            return n
    for word, n in (("glass", "Smashed"), ("lamp", "Broken"), ("light", "Broken")):
        if word in s:
            return n
    return None


def norm_other(x):
    x = str(x).lower()
    for tid, lab in DTYPES:
        if x in (tid.lower(), lab.lower()):
            return tid
    return None


def run_major(rep_text):
    est = [{"part_id": PART_ID[p], "severity": int(s)} for p, s in ss.estimate if p in PART_ID]
    res = api.major(ss.photos, rep_text, est, run_glm=os.environ.get("RUN_GLM", "true").lower() != "false")
    return {"kind": "major", "res": res}


def pretty(x):
    s = str(x or "").replace("_", " ").strip()
    if s.isupper():
        s = s.lower()
    return s[:1].upper() + s[1:]


def pct(x):
    return "—" if x is None else f"{float(x):.0%}"


def e(x):
    return html.escape(str(x))


def live_table(title, heads, rows):
    th = "".join(f"<th>{e(h)}</th>" for h in heads)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    st.markdown(f"<div class='tbl'><h3>{e(title)}</h3><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>", unsafe_allow_html=True)


def status_cell(status):
    return f"<span class='{'s-NeedsReview' if 'review' in str(status).lower() else 's-Matched'}'>{e(pretty(status))}</span>"


def render_live(live):
    kind = live["kind"]
    src = live["final"] if kind == "minor" else (live.get("res") or {})
    if kind == "none":
        outcome, summary, rows_in = "matched", "No damage was declared, so there is nothing to compare.", []
        stats = [("Declared", 0), ("Needs review", 0), ("Hidden damage flag", "No")]
    elif kind == "minor":
        outcome, summary, rows_in = src.get("outcome"), src.get("summary"), src.get("rows") or []
        stats = [("Damage types checked", len(rows_in)), ("Needs review", src.get("needs_review_count", 0)),
                 ("Hidden damage flag", "Yes" if src.get("hidden_damage_flag") else "No")]
    else:
        outcome, summary, rows_in = src.get("outcome"), src.get("summary"), src.get("visible_report") or []
        stats = [("Damage seen in photos", len(src.get("visible_detected") or [])), ("Damage in report", len(src.get("garage_items") or [])),
                 ("Needs review", sum("review" in str(r.get("status", "")).lower() for r in rows_in))]
    bad = "review" in str(outcome).lower()
    st.markdown(f"<div class='banner {'bad' if bad else 'ok'}'><div><h3>{e(pretty(outcome))}</h3><p>{e(summary or '')}</p></div></div>", unsafe_allow_html=True)
    st.markdown("<div class='stats'>" + "".join(f"<div class='stat'><b>{e(v)}</b><span>{e(t)}</span></div>" for t, v in stats) + "</div>", unsafe_allow_html=True)
    if kind == "minor":
        live_table("Declared damage vs model", ["Parts", "Damage", "Confidence", "Severity", "Fix", "Status", "Reason"],
                   [[e(", ".join(x for x in (r.get("part_names") or []) if x) or "—"), e(r.get("damage") or pretty(r.get("damage_type"))), pct(r.get("max_conf")),
                     e(round(r["severity"]) if r.get("severity") is not None else "—"), e(pretty(r.get("fix_type"))), status_cell(r.get("status")),
                     e(r.get("reason") or "")] for r in rows_in])
    elif kind == "major":
        if src.get("garage_items"):
            st.markdown("**Damage read from the garage report**  \n" + " ".join(f"<span class='tag'>{e(g)}</span>" for g in src["garage_items"]), unsafe_allow_html=True)
        mark = {True: "Yes", False: "No", None: "—"}
        live_table("Garage report vs photos", ["Damage", "In report", "Seen in photos", "Status", "Reason"],
                   [[e(r.get("damage")), mark[r.get("in_garage_report")], mark[r.get("model_detected")], status_cell(r.get("status")), e(r.get("reason") or "")] for r in rows_in])
        sev = src.get("severity") or {}
        if sev.get("ran"):
            st.caption(f"Severity grading ran. Highest score: {sev.get('max')}. " + " ".join(sev.get("notes") or []))
    hd, note = src.get("hidden_damage"), src.get("hidden_damage_note")
    if hd or note:
        with st.container(key="card_hidden"):
            st.markdown("**Hidden damage assessment**")
            if hd:
                st.markdown(f"<div class='note {'warn' if hd.get('hidden_damage_likely') else 'ok'}'><b>{e(pretty(hd.get('verdict')))}</b>. {e(hd.get('summary') or '')}</div>", unsafe_allow_html=True)
                with st.expander("Details"):
                    st.json(hd)
            if note:
                st.caption(note)
    if src.get("estimate"):
        live_table("Repair estimate", ["Part", "Severity", "Fix"], [[e(r.get("part_name") or r.get("part_id")), e(round(r.get("severity") or 0)), e(pretty(r.get("fix_type")))] for r in src["estimate"]])
    imgs = live.get("images") if kind == "minor" else [(p.get("caption") or p.get("key"), p.get("image_jpeg_b64")) for p in (src.get("photos") or [])]
    imgs = [(c, api.b64_bytes(b) if isinstance(b, str) else b) for c, b in (imgs or []) if b]
    if imgs:
        st.markdown("### Photo findings")
        cols = st.columns(2)
        for i, (cap, data) in enumerate(imgs):
            with cols[i % 2], st.container(key=f"card_live_{i}"):
                st.image(data)
                st.markdown(f"<span class='hint'>{e(cap)}</span>", unsafe_allow_html=True)


# ---------------- journey 1: the damage you can see (one photo + model check per damage) ----------------
def cur_thr():
    return None if ss.thr_mode == "prod" else float(ss.thr_val)


def new_inst(data=None, parts=None):
    ss.mn_seq += 1
    return {"id": ss.mn_seq, "data": data, "parts": list(parts or []), "chk": None, "thr": None, "err": None, "n": 0}


def slots(t):
    lst = ss.mn_inst.setdefault(t, [])
    if not lst:
        lst.append(new_inst())
    return lst


def find_inst(iid):
    for t, lst in ss.mn_inst.items():
        for i in lst:
            if i["id"] == iid:
                return t, i
    return None, None


def run_check(t, inst):
    inst["chk"], inst["err"] = None, None
    r = check(inst["data"])
    if r["blocking"]:
        inst["err"] = " ".join(r["blocking"])
        return
    thr = cur_thr()
    try:
        c = api.minor_check(t, inst["data"], thr, True) if LIVE else L.mock_minor_check(t, inst["data"], thr)
    except Exception as ex:
        inst["err"] = str(ex)
        return
    if c.get("available") is False or c.get("error"):
        inst["err"] = c.get("error") or "This detector is not available on the backend."
        return
    inst["chk"], inst["thr"] = c, thr


def _types_changed():
    sel = ss.pills_types or []
    ss.mn_types = [tid for tid, lab in DTYPES if lab in sel]
    ss.flags["confirmed"] = ss["cb_confirmed"] = False   # the list changed: ask again


def _thr_mode():
    ss.thr_mode = "prod" if ss.thr_radio.startswith("Use") else "custom"


def _thr_val():
    ss.thr_val = ss.thr_slider


def _parts(iid):
    t, i = find_inst(iid)
    if i is not None:
        i["parts"] = list(ss[f"parts_{iid}"])


def replace_photo(iid):
    t, i = find_inst(iid)
    if i is not None:
        i.update(data=None, chk=None, err=None, thr=None, n=i["n"] + 1)


def remove_inst(t, iid):
    ss.mn_inst[t] = [i for i in ss.mn_inst.get(t, []) if i["id"] != iid]


def add_slot(t):
    ss.mn_inst.setdefault(t, []).append(new_inst())


def add_other(iid, other):
    """The model saw another damage type in this photo: declare it and reuse the photo."""
    t, i = find_inst(iid)
    if i is None or other in [x for x in ss.mn_types if any(j["data"] == i["data"] for j in ss.mn_inst.get(x, []))]:
        return
    ni = new_inst(i["data"], i["parts"])
    run_check(other, ni)
    ss.mn_inst[other] = [x for x in ss.mn_inst.get(other, []) if x["data"]] + [ni]
    ss.mn_types = [tid for tid, _ in DTYPES if tid in set(ss.mn_types) | {other}]
    ss.pills_types = [DLABEL[tid] for tid in ss.mn_types]
    ss.flags["confirmed"] = ss["cb_confirmed"] = False


CONFIRM_MSG = "Confirm the list is complete."


def minor_problems():
    p = []
    if not ss.mn_types and not ss.flags["none_minor"]:
        p.append("Tick the damage you can see, or select “No visible damage”.")
    for t in ss.mn_types:
        lab = DLABEL.get(t, t).lower()
        with_data = [i for i in ss.mn_inst.get(t, []) if i["data"]]
        if not with_data:
            p.append(f"Choose where the {lab} is and add a photo." if not any(i["parts"] for i in ss.mn_inst.get(t, [])) else f"Add a photo of the {lab}.")
        for i in with_data:
            if i["err"] or not i["chk"]:
                p.append(f"The {lab} photo did not pass: replace it.")
            elif i["thr"] != cur_thr():
                p.append("Re-check the photos you checked with the old threshold.")
            if not i["parts"]:
                p.append(f"Choose where the {lab} is on the vehicle.")
    if not ss.flags["confirmed"]:
        p.append(CONFIRM_MSG)
    return list(dict.fromkeys(p))


def minor_items():
    out = []
    for t in ss.mn_types:
        insts = [i for i in ss.mn_inst.get(t, []) if i["data"] and i["chk"] and not i["err"] and i["parts"]]
        ids = sorted({PID[p] for i in insts for p in i["parts"] if p in PID})
        if not insts or not ids:
            continue
        best = max((i["chk"] for i in insts), key=lambda c: c.get("max_conf") or 0)
        it = api.minor_item(best, ids[0], t)
        it.update(confirmed=any(bool(i["chk"].get("confirmed")) for i in insts), part_ids=ids,
                  severity=max(api.minor_item(i["chk"], ids[0], t)["severity"] for i in insts))
        out.append(it)
    return out


def run_minor_final():
    items = minor_items()
    if not items:
        return {"kind": "none"}
    imgs = [(f"{DLABEL.get(t, t)} · {', '.join(i['parts'])}", i["chk"].get("image_jpeg_b64")) for t in ss.mn_types
            for i in ss.mn_inst.get(t, []) if i["data"] and i["chk"]]
    fin = api.minor_finalize(items) if LIVE else L.mock_minor_finalize(items)
    return {"kind": "minor", "final": fin, "images": imgs}


def photo_side(t, j, total, inst, lab):
    iid = inst["id"]
    if total > 1:
        st.markdown(f"**Photo {j}**")
    # 1 · location comes first: the photo slot only opens once we know where the damage is
    st.markdown("<div class='mc-h'>1 · Location</div>", unsafe_allow_html=True)
    st.multiselect(f"Where is the {lab.lower()} on the vehicle?", PANEL_OPTIONS, default=[p for p in inst["parts"] if p in PANEL_OPTIONS], key=f"parts_{iid}",
                   on_change=_parts, args=(iid,), placeholder=f"Choose the part(s) with the {lab.lower()}")
    st.markdown("<div class='mc-h'>2 · Photo</div>", unsafe_allow_html=True)
    if not inst["data"]:
        if not inst["parts"]:
            st.markdown("<div class='mc-empty'>Choose the location first. The photo upload opens next.</div>", unsafe_allow_html=True)
            if total > 1:
                st.button("Cancel", key=f"cx_{iid}", icon=":material/close:", on_click=remove_inst, args=(t, iid))
            return
        st.caption(f"Upload a clear photo of the {lab.lower()} on the {' / '.join(inst['parts']).lower()}.")
        mode = st.segmented_control("Source", ["Upload", "Camera"], default="Upload", key=f"mode_{iid}", label_visibility="collapsed")
        k = f"{iid}_{inst['n']}"
        if mode == "Camera":
            f = st.camera_input(f"{lab} photo", key=f"cam_{k}", label_visibility="collapsed")
        else:
            f = st.file_uploader(f"{lab} photo", type=["jpg", "jpeg", "png", "webp"] + (["heic", "heif"] if L.HEIC else []), key=f"up_{k}", label_visibility="collapsed")
        if f is not None:
            data = f.getvalue()
            if any(o is not inst and o["data"] == data for o in ss.mn_inst.get(t, [])):
                inst["err"], inst["data"] = None, None
                st.error("You already added this photo for this damage.")
                return
            inst["data"], inst["n"] = data, inst["n"] + 1
            with st.spinner("Running model check…"):
                run_check(t, inst)
            st.rerun()
        if total > 1:
            st.button("Cancel", key=f"cx_{iid}", icon=":material/close:", on_click=remove_inst, args=(t, iid))
        return
    st.image(inst["data"])
    b1, b2 = st.columns(2)
    b1.button("Replace", key=f"rp_{iid}", icon=":material/refresh:", on_click=replace_photo, args=(iid,))
    b2.button("Remove", key=f"rm_{iid}", icon=":material/delete:", on_click=remove_inst, args=(t, iid))


def check_panel(t, n, j, total, inst, lab):
    st.markdown("<div class='mc-h'>3 · Model check</div>", unsafe_allow_html=True)
    if not inst["data"]:
        st.markdown(f"<div class='mc-empty'>{'Waiting for a photo.' if inst['parts'] else 'Waiting for the location and a photo.'}</div>", unsafe_allow_html=True)
        return
    if inst["err"]:
        st.markdown(f"<div class='note bad'>{e(inst['err'])}</div>", unsafe_allow_html=True)
        return
    c = inst["chk"]
    ok = bool(c.get("confirmed"))
    st.markdown(f"<div class='note {'ok' if ok else 'warn'}'><b>{'Confirmed' if ok else 'Not confirmed'}</b> · the model "
                f"{'found' if ok else 'did not find'} {e(lab.lower())} in this photo.</div>", unsafe_allow_html=True)
    sev = c.get("severity") or {}
    kv = [("Confidence", pct(c.get("max_conf"))), ("Threshold", pct(c.get("thr")))]
    if sev.get("ok") and sev.get("composite") is not None:
        kv.append(("Severity", f"{round(sev['composite'])}/100 · {pretty(sev.get('verdict'))}"))
    if c.get("fix_type"):
        kv.append(("Fix", pretty(c["fix_type"])))
    st.markdown("<div class='kv'>" + "".join(f"<span>{e(k)} <b>{e(v)}</b></span>" for k, v in kv) + "</div>", unsafe_allow_html=True)
    if sev.get("what_you_see"):
        st.caption(sev["what_you_see"])
    q = c.get("quality") or {}
    if q.get("ok") is False:
        st.markdown(f"<div class='note warn'>Photo quality: {e(' '.join(q.get('notes') or ['check the photo']))}</div>", unsafe_allow_html=True)
    img = api.b64_bytes(c.get("image_jpeg_b64"))
    if img:
        st.image(img)
    for o in dict.fromkeys(x for x in (norm_other(y) for y in (c.get("other_damage") or [])) if x and x != t):
        have = any(i["data"] == inst["data"] for i in ss.mn_inst.get(o, []))
        if not have:
            st.button(f"The model also sees {DLABEL.get(o, o).lower()}. Add it", key=f"oth_{inst['id']}_{o}", icon=":material/add_circle:",
                      on_click=add_other, args=(inst["id"], o))


def damage_card(n, t):
    lst = slots(t)
    lab = DLABEL.get(t, t)
    done = [i for i in lst if i["data"]]
    if not done:
        chip, col = ("Add a photo", "var(--mfg)") if any(i["parts"] for i in lst) else ("Add location", "var(--mfg)")
    elif not all(i["parts"] for i in done):
        chip, col = "Add location", "var(--warn)"
    elif all(i["chk"] and i["chk"].get("confirmed") for i in done):
        chip, col = "Confirmed", "var(--ok)"
    else:
        chip, col = "Needs review", "var(--warn)"
    with st.container(key=f"card_dmg_{t}"):
        st.markdown(f"<div class='ph-head'><span class='badge'>{n}</span><div><b>Damage {n} · {e(lab)}</b><br>"
                    f"<span class='hint'>Say where the {e(lab.lower())} is, then upload a clear photo of it. Add more photos if it appears in several places.</span></div>"
                    f"<span class='tick' style='color:{col}'>{chip}</span></div>", unsafe_allow_html=True)
        for j, inst in enumerate(lst, 1):
            if j > 1:
                st.divider()
            lc, rc = st.columns(2, gap="medium")
            with lc:
                photo_side(t, j, len(lst), inst, lab)
            with rc:
                check_panel(t, n, j, len(lst), inst, lab)
        if all(i["data"] for i in lst):
            st.button(f"Add another {lab.lower()} photo", key=f"more_{t}", icon=":material/add_a_photo:", on_click=add_slot, args=(t,))


def minor_step():
    c1, c2 = st.columns([3, 1.3], vertical_alignment="bottom")
    with c1:
        head(1, "Damage you can see", "Tick every type of damage on the vehicle.")
    if c2.button("Damage guide", icon=":material/help:", key="guide_btn"):
        guide(guide_name(ss.mn_types[0]) if ss.mn_types and guide_name(ss.mn_types[0]) else "Scratch")
    st.pills("Damage types", [lab for _, lab in DTYPES], selection_mode="multi", default=None if "pills_types" in ss else [DLABEL[t] for t in ss.mn_types if t in DLABEL],
             key="pills_types", on_change=_types_changed, label_visibility="collapsed")
    with st.container(key="card_thr"):
        st.markdown("**Detection threshold**  \n<span class='hint'>Higher is stricter. Photos keep the threshold they were checked with.</span>", unsafe_allow_html=True)
        st.radio("Threshold mode", ["Use each detector's production threshold", "Custom threshold"], index=0 if ss.thr_mode == "prod" else 1,
                 key="thr_radio", horizontal=True, on_change=_thr_mode, label_visibility="collapsed")
        if ss.thr_mode == "custom":
            st.slider("Custom threshold", 0.05, 0.95, float(ss.thr_val), 0.05, key="thr_slider", on_change=_thr_val)
    stale = [i for t in ss.mn_types for i in ss.mn_inst.get(t, []) if i["data"] and i["chk"] and i["thr"] != cur_thr()]
    if stale:
        st.warning(f"{len(stale)} photo(s) were checked with a different threshold.")
        if st.button(f"Re-check {len(stale)} photo(s) with the new threshold", key="recheck", type="primary", icon=":material/refresh:"):
            with st.spinner("Re-checking…"):
                for t in ss.mn_types:
                    for i in ss.mn_inst.get(t, []):
                        if i["data"]:
                            run_check(t, i)
            st.rerun()
    if not ss.mn_types:
        st.checkbox("No visible damage to declare", value=ss.flags["none_minor"], key="cb_none_minor", on_change=_flag, args=("none_minor",))
    for n, t in enumerate(ss.mn_types, 1):
        damage_card(n, t)
    probs = minor_problems()
    open_items = [p for p in probs if p != CONFIRM_MSG]
    st.checkbox("I confirm this list is complete", value=ss.flags["confirmed"], key="cb_confirmed", on_change=_flag, args=("confirmed",),
                disabled=bool(open_items), help="Available once every damage has a location and a checked photo." if open_items else None)
    if probs:
        st.markdown("<div class='hint' style='color:var(--warn)'>Still to do: " + e(" · ".join(probs)) + "</div>", unsafe_allow_html=True)
    st.button("Review results", icon=":material/arrow_forward:", icon_position="right", key="to1", type="primary", disabled=bool(probs), on_click=go, args=(1,))


def _est_add():
    ss.estimate = [x for x in ss.estimate if x[0] != ss.est_part] + [(ss.est_part, int(ss.est_sev))]


def _est_rm(i):
    ss.estimate.pop(i)


def estimate_card():
    with st.container(key="card_estimate"):
        st.markdown("**Parts on the repair estimate**  \n<span class='hint'>Optional. Add each visible part from the estimate with a severity from 0 to 100. "
                    "It is used for the hidden-damage assessment.</span>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([3, 3, 1.4], vertical_alignment="bottom")
        c1.selectbox("Part", PANEL_OPTIONS, key="est_part")
        c2.slider("Severity", 0, 100, 50, key="est_sev")
        c3.button("Add", key="est_add", type="primary", icon=":material/add:", on_click=_est_add)
        for i, (p, s) in enumerate(ss.estimate):
            a, b = st.columns([9, 1], vertical_alignment="center")
            a.markdown(f"<div class='item'><b>{e(p)}</b>&nbsp;·&nbsp;<span style='color:var(--mfg)'>severity {s}</span></div>", unsafe_allow_html=True)
            b.button("", key=f"est_rm_{i}", icon=":material/delete:", on_click=_est_rm, args=(i,))


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
        if LIVE and r["hash"] is not None:
            q = api_quality(api.base_url(), d)
            if q and not q.get("ok", True):
                blocking.append(" ".join(q.get("notes") or [q.get("summary") or "Photo did not pass the quality check."]))
        out[v] = {**r, "blocking": blocking}
    return out


def _acc(v):
    ss.accepted[v] = ss[f"acc_{v}"]


def _flag(k):
    ss.flags[k] = ss[f"cb_{k}"]


def toggle_theme():
    ss.dark = not ss.dark


def _seg():
    if ss.towed_ui is None:
        ss.towed_ui = ss._prev_towed
    if ss.towed_ui != ss._prev_towed:
        ss.step = 0
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


@st.dialog("Damage guide", width="small")
def guide(selected):
    pick = st.pills("Damage type", L.DAMAGES, default=selected, selection_mode="single", label_visibility="collapsed") or selected
    st.caption(L.DAMAGE_INFO[pick])
    c1, c2 = st.columns(2)
    c1.image(example(pick, 0), caption="Example 1")
    c2.image(example(pick, 1), caption="Example 2")


@st.dialog("Photo requirements", width="small")
def requirements():
    st.markdown("- JPG, PNG, WebP or HEIC, under 12 MB.\n"
                "- Please don't upload blurry, dark or overexposed photos.\n"
                "- Each angle needs a different photo.")
    st.caption("Image checks do not verify that a vehicle is pictured.")


def head(n, title, sub):
    st.markdown(f"<div class='kick'>Step 0{n} / 0{3 if ss.towed_ui == 'Towed' else 2}</div><div class='stitle'>{title}</div><div class='sub'>{sub}</div>",
                unsafe_allow_html=True)


# ---------------- derived state ----------------
towed = ss.towed_ui == "Towed"
stat = photo_status()
good = [v for v in L.VIEWS if v in stat and not stat[v]["blocking"] and (not stat[v]["soft"] or ss.accepted.get(v))]
photo_ready = len(good) == 4
items = ss.garage
rep = ss.report
sig = hashlib.md5(b"".join(ss.photos[v] for v in L.VIEWS if v in ss.photos)).hexdigest()
rep_text = (rep or {}).get("text", "") if towed else ""
if towed:
    form_ready = bool(rep) and not rep["error"] and (not LIVE or bool((rep.get("text") or "").strip()))
    run_sig = hashlib.md5((sig + rep_text + repr(ss.estimate)).encode()).hexdigest()
else:
    form_ready = not minor_problems()
    run_sig = hashlib.md5(json.dumps(minor_items(), sort_keys=True, default=str).encode()).hexdigest()
dets_ok = (ss.get("live") is not None and ss.get("live_sig") == run_sig) if (LIVE or not towed) else (ss.get("dets") is not None and ss.get("dets_sig") == sig)
stages = ["Photos", "Garage report", "Results"] if towed else ["Damage you can see", "Results"]

# ---------------- hero ----------------
img = f"<img src='{hero_uri()}' alt=''>" if hero_uri() else ""
st.markdown(f"""<div class='hero'>{img}<div class='shade'></div><div class='grid'></div><div class='hero-in'>
<div class='nav'><div class='brand'><div class='logo'><svg width='21' height='21' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2'
stroke-linecap='round' stroke-linejoin='round'><circle cx='11' cy='11' r='7'/><path d='m21 21-4.3-4.3'/><path d='m8 11 2 2 4-4'/></svg></div>
<div><div class='bt'>CAR DAMAGE CHECK</div></div></div></div>
<div class='txt'><h1>Car damage<br><em>detection demo</em></h1></div></div></div>""",
            unsafe_allow_html=True)
with st.container(key="topstatus"):
    st.markdown("<div class='pill'><span class='dot'></span><span class='ptxt'>Demo workspace</span></div>", unsafe_allow_html=True)
with st.container(key="theme_toggle"):
    st.button("", icon=":material/light_mode:" if ss.dark else ":material/dark_mode:", key="theme_btn", on_click=toggle_theme,
              help="Switch to light mode" if ss.dark else "Switch to dark mode")

left, right = st.columns([1, 3.6], gap="large")

# ---------------- sidebar ----------------
with left:
    st.markdown("<div class='side-h'>Your inspection</div>", unsafe_allow_html=True)
    done = [photo_ready, form_ready, dets_ok] if towed else [form_ready, dets_ok]
    icons = [":material/photo_camera:", ":material/description:", ":material/fact_check:"] if towed else [":material/add_a_photo:", ":material/fact_check:"]
    for i, label in enumerate(stages):
        st.button(label, icon=":material/check_circle:" if done[i] else icons[i], key=f"{'navon' if ss.step == i else 'nav'}_{i}",
                  on_click=go, args=(i,))
    if towed:
        st.markdown(f"<div class='prog'><span>Photo progress</span><span style='color:var(--accent)'>{len(good)} of 4</span></div>"
                    f"<div class='bar'><i style='width:{len(good) * 25}%'></i></div>"
                    "<div class='hint'>Each angle is checked before it can be used.</div>", unsafe_allow_html=True)
    else:
        _all = [i for t in ss.mn_types for i in ss.mn_inst.get(t, []) if i["data"]]
        _ok = sum(1 for i in _all if i["chk"] and not i["err"])
        st.markdown(f"<div class='prog'><span>Damage photos checked</span><span style='color:var(--accent)'>{_ok} of {len(_all)}</span></div>"
                    f"<div class='bar'><i style='width:{int(100 * _ok / len(_all)) if _all else 0}%'></i></div>"
                    "<div class='hint'>Each photo is checked as soon as you add it.</div>", unsafe_allow_html=True)
    st.markdown("<div class='prog'><span>INSPECTION TYPE</span></div>", unsafe_allow_html=True)
    st.segmented_control("Inspection type", ["Not towed", "Towed"], key="towed_ui", on_change=_seg, label_visibility="collapsed")
    st.markdown("<div class='hint'>You can switch at any time. Your photos will stay in place.</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='hint' style='margin-top:.8rem'>{'● Connected to the detection API' if LIVE else '○ Demo mode: no backend connected'}</div>", unsafe_allow_html=True)
    if BACKEND and not LIVE:
        st.caption("Backend not available: " + (_H.get("error") if _H and not _H["ok"] else "it returned no parts list."))

# ---------------- main ----------------
with right:
    if not towed and ss.step == 0:
        minor_step()
    elif towed and ss.step == 1:
        head(2, "Garage report", "Attach the garage report and, optionally, its parts estimate.")
        if towed:
            with st.container(key="card_report"):
                st.markdown("**Garage report**  \n<span class='hint'>PDF, CSV, text or image · up to 15 MB</span>", unsafe_allow_html=True)
                if rep:
                    st.markdown(f"<div class='note {'bad' if rep['error'] else 'ok'}'>"
                                f"{html.escape(rep['error'] or rep['name'] + ' accepted. ' + rep['note'])}</div>", unsafe_allow_html=True)
                    if st.button("Replace report", icon=":material/refresh:", key="rep_replace"):
                        ss.report, ss.garage = None, []
                        ss.rep_n += 1
                        st.rerun()
                else:
                    up = st.file_uploader("Upload report", type=["pdf", "csv", "txt", "jpg", "jpeg", "png"], key=f"rep_up_{ss.rep_n}",
                                          label_visibility="collapsed")
                    if up is not None:
                        r = L.validate_report(up.name, up.getvalue())
                        ss.report = {"name": up.name, "error": r["error"] and r["error"] + ".", "note": r["note"], "text": r.get("text", "")}
                        ss.garage = list(r["items"])
                        st.rerun()
            if rep and not rep["error"]:
                g = ss.garage
                exact = rep["name"].lower().endswith(".csv")
                st.markdown("### Garage report summary")
                if LIVE and not exact:  # the backend reads the text; do not show the mock extractor's items
                    txt = (rep.get("text") or "").strip()
                    st.markdown("<div class='stats'>" + "".join(f"<div class='stat'><b{c}>{v}</b><span>{t}</span></div>" for t, v, c in
                                [("Report file", html.escape(rep["name"]), " class='sm'"), ("Characters read", len(txt), "")]) + "</div>", unsafe_allow_html=True)
                    if txt:
                        with st.expander("Text that will be sent to the backend"):
                            st.text(txt[:1500])
                        st.caption("The backend reads the damage from this text when you run the check.")
                    else:
                        st.markdown("<div class='note bad'>No text could be read from this file. Upload a PDF with selectable text, a CSV or a text file.</div>", unsafe_allow_html=True)
                    g = None
                if g is not None:
                  st.markdown("<div class='stats'>" + "".join(f"<div class='stat'><b{cls}>{v}</b><span>{t}</span></div>" for t, v, cls in
                            [("Damage items", len(g), ""), ("Parts affected", len({p for p, _ in g}), ""),
                             ("Report file", html.escape(rep["name"]), " class='sm'")]) + "</div>", unsafe_allow_html=True)
                if g is None:
                    pass
                elif g:
                    rows = "".join(f"<tr><td><b>{html.escape(p)}</b></td><td><span class='tag'>{html.escape(d)}</span></td></tr>" for p, d in g)
                    st.markdown(f"<div class='tbl'><h3>Damage listed in the report</h3><table><thead><tr><th>Part</th><th>Damage</th></tr></thead>"
                                f"<tbody>{rows}</tbody></table></div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='banner ok'><div><h3>No damage listed</h3><p>The garage report does not list any damage.</p></div></div>",
                                unsafe_allow_html=True)
                if not LIVE and not rep["name"].lower().endswith(".csv"):
                    st.caption("Demo mode: PDF and image reports are read with a simulated extractor. CSV reports are read exactly.")
        if LIVE and rep and not rep["error"]:
            estimate_card()
        b1, b2 = st.columns(2)
        b1.button(stages[0], icon=":material/arrow_back:", key="back0", on_click=go, args=(0,))
        b2.button("Review results", icon=":material/arrow_forward:", icon_position="right", key="to2", type="primary",
                  disabled=not (photo_ready and form_ready), on_click=go, args=(2,))
        if not photo_ready:
            st.markdown("<div class='hint' style='color:var(--warn)'>Add and accept all four photos before reviewing results.</div>", unsafe_allow_html=True)
    elif towed and ss.step == 0:
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        with c1:
            head(1, "Capture the vehicle", "Add one clear photo from each angle.")
        if c2.button("Photo requirements", icon=":material/info:", key="req"):
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
                    st.markdown("<div class='ph-empty'><svg width='30' height='30' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.6' "
                                "stroke-linecap='round' stroke-linejoin='round'><path d='M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z'/>"
                                "<circle cx='12' cy='13' r='4'/></svg>"
                                f"{'Photo needs replacing' if blocked else 'No photo added yet'}</div>", unsafe_allow_html=True)
                if s and (blocked or s["soft"]):
                    txt = html.escape(" ".join(s["blocking"] + s["soft"]))
                    txt = txt[:1].upper() + txt[1:]
                    st.markdown(f"<div class='note {'bad' if blocked else 'warn'}'>{txt}</div>", unsafe_allow_html=True)
                    if not blocked:
                        st.checkbox("Use anyway", value=ss.accepted.get(view, False), key=f"acc_{view}", on_change=_acc, args=(view,))
                if ok:
                    st.markdown(f"<div class='okline'>✓ Photo accepted · {s['size'][0]} × {s['size'][1]}</div>", unsafe_allow_html=True)
                if data:
                    st.button("Replace photo", icon=":material/refresh:", key=f"rep_{view}", on_click=drop_photo, args=(view,))
                else:
                    mode = st.segmented_control("Source", ["Upload", "Camera"], default="Upload",
                                                key=f"mode_{view}", label_visibility="collapsed")
                    n = ss.nonce[view]
                    if mode == "Camera":
                        f = st.camera_input(f"{view} photo", key=f"cam_{view}_{n}", label_visibility="collapsed")
                    else:
                        f = st.file_uploader(f"{view} photo", type=["jpg", "jpeg", "png", "webp"] + (["heic", "heif"] if L.HEIC else []),
                                             key=f"up_{view}_{n}", label_visibility="collapsed")
                    if f is not None:
                        ss.counter += 1
                        ss.photos[view], ss.seq[view], ss.accepted[view] = f.getvalue(), ss.counter, False
                        ss.nonce[view] += 1
                        st.rerun()
        st.button("Continue to garage report", icon=":material/arrow_forward:", icon_position="right", key="to1", type="primary",
                  disabled=not photo_ready, on_click=go, args=(1,))
        if not photo_ready:
            st.markdown(f"<div class='hint' style='color:var(--warn)'>{len(good)} of 4 photos accepted. Add the remaining angles to continue.</div>", unsafe_allow_html=True)

    else:
        head(3 if towed else 2, "Inspection results", "Compare the garage report against the photo findings." if towed else "Your declared damage, checked against the model.")
        if not ((photo_ready and form_ready) if towed else form_ready):
            target = 0 if (not towed or not photo_ready) else 1
            msg = ((f"Accept all four photos ({len(good)} of 4 ready)." if not photo_ready else "Upload a valid garage report.") if towed
                   else (minor_problems() or [""])[0])
            with st.container(key="card_gate"):
                st.markdown(f"**Complete your inspection first**  \n<span class='hint'>{msg}</span>", unsafe_allow_html=True)
                st.button("Go to " + stages[target].lower(), key="gate", on_click=go, args=(target,))
        else:
            with st.container(key="card_run"):
                a, b = st.columns([4, 1.3], vertical_alignment="center")
                a.markdown(f"**Ready to compare**  \n<span class='hint'>{'Four photos and the garage report are complete' if towed else 'Every damage photo has been checked'}</span>", unsafe_allow_html=True)
                if b.button(("Run again" if dets_ok else "Run detection") if towed else ("Update outcome" if dets_ok else "Get outcome"), icon=":material/play_arrow:", key="run", type="primary"):
                    ss.run_error = None
                    with st.spinner("Checking…"):
                        try:
                            if not towed:
                                ss.live, ss.live_sig = run_minor_final(), run_sig
                            elif LIVE:
                                ss.live, ss.live_sig = run_major(rep_text), run_sig
                            else:
                                ss.dets = [d for v in L.VIEWS for d in L.detect_damage(v, ss.photos[v])]
                                ss.dets_sig = sig
                        except Exception as ex:
                            ss.pop("live", None)
                            ss.pop("dets", None)
                            ss.run_error = f"Check failed: {ex}"
                    st.rerun()
            if ss.get("run_error"):
                st.error(ss.run_error)
            if not LIVE:
                st.caption("Demo mode: findings are simulated until a real detection service is connected.")
            if dets_ok and (LIVE or not towed):
                render_live(ss.live)
            elif dets_ok:
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
                st.download_button("Download CSV", df.to_csv(index=False), "car-damage-report.csv", "text/csv", icon=":material/download:")
                st.markdown("### Photo findings")
                cols = st.columns(2)
                for i, v in enumerate(L.VIEWS):
                    dv = [d for d in ss.dets if d["view"] == v]
                    with cols[i % 2], st.container(key=f"card_find_{v}"):
                        st.image(L.annotate(ss.photos[v], dv))
                        st.markdown(f"**{v}** <span class='hint'>· {len(dv)} finding(s)</span>", unsafe_allow_html=True)
            elif ss.get("dets") is not None or ss.get("live") is not None:
                st.warning("Your inputs changed since the last run. Run detection again.")
