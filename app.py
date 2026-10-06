import html
import os

import streamlit as st

import api
import client
import logic as L

st.set_page_config(page_title="Car Damage Check | Vehicle inspection", page_icon="🔍", layout="wide")
try:  # backend settings from .streamlit/secrets.toml or Streamlit Cloud secrets
    for _k in ("API_BASE_URL", "API_KEY", "RUN_GLM"):
        if _k in st.secrets:
            os.environ.setdefault(_k, str(st.secrets[_k]))
except Exception:
    pass

LIGHT = """--bg:#f4f6f9;--card:#ffffff;--card2:#f1f4f8;--fg:#0f1a22;--mfg:#63707a;--border:#dde3e8;--accent:#00706d;
--p1:#0a8f89;--p2:#00605d;--secondary:#dcf1f0;--glow:rgba(0,112,109,.45);--shadow:0 1px 2px rgba(15,26,34,.06),0 8px 24px -12px rgba(15,26,34,.12);
--bad:#c13234;--ok:#00623b;--oksoft:#dcf6e5;--warn:#934f00;--warnsoft:#fff3d8;--ink:#0d1b22;--chrome:#dde1e7;"""
DARK = """--bg:#0a1116;--card:#121c23;--card2:#19252d;--fg:#e8eff3;--mfg:#93a2ac;--border:#233340;--accent:#4fe3d5;
--p1:#14b3a8;--p2:#0b7c75;--secondary:rgba(79,227,213,.12);--glow:rgba(20,179,168,.5);--shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px -12px rgba(0,0,0,.6);
--bad:#ff8a8c;--ok:#5fe0a0;--oksoft:rgba(95,224,160,.12);--warn:#ffc36b;--warnsoft:rgba(255,195,107,.12);--ink:#070d11;--chrome:#05090c;"""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@700;800&display=swap');
:root{__VARS__ color-scheme:__SCHEME__;}
html,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:var(--bg)!important;color:var(--fg);font-family:'DM Sans',sans-serif;}
.stApp,[data-testid="stMain"]{overflow-x:hidden;}
header[data-testid="stHeader"],[data-testid="stDecoration"],[data-testid="stToolbar"],#MainMenu,footer{display:none!important;}
[data-testid="stElementContainer"]:has(style){position:absolute;height:0;width:0;overflow:hidden;margin:0;padding:0;}
.block-container,[data-testid="stMainBlockContainer"],[data-testid="stAppViewBlockContainer"]{max-width:1240px;padding:48px 1.5rem 4rem!important;margin-top:0!important;}
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
.st-key-topstatus{position:fixed;top:.65rem;right:3.7rem;z-index:1000;width:auto!important;}
.st-key-topstatus .pill{height:34px;padding:0 .85rem;background:rgba(13,27,34,.78);border:1px solid rgba(255,255,255,.25);box-shadow:0 6px 18px -8px rgba(0,0,0,.5);}
.st-key-theme_toggle{position:fixed;top:.65rem;right:1.2rem;z-index:1000;width:auto!important;}
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

/* ---------- browser-style view tabs ---------- */
.st-key-tabbar{position:fixed;top:0;left:0;right:0;z-index:999;height:48px;background:var(--chrome);padding:8px 1rem 0;border-bottom:1px solid var(--border);}
.st-key-tabbar [data-testid="stHorizontalBlock"]{gap:0!important;flex-wrap:nowrap!important;align-items:flex-end;max-width:1240px;margin:0 auto;}
.st-key-tabbar [data-testid="stColumn"]{width:auto!important;flex:0 0 auto!important;min-width:0!important;overflow:visible!important;}
.st-key-tabbar [data-testid="stElementContainer"],.st-key-tabbar .stButton{overflow:visible!important;width:auto!important;}
[class*="st-key-vtab_"] button,[class*="st-key-vtabon_"] button{position:relative;width:220px;height:40px;min-height:40px;border:0!important;border-radius:12px 12px 0 0!important;box-shadow:none!important;
 justify-content:flex-start;padding:0 1rem;font-size:.86rem;transform:none!important;overflow:visible;}
[class*="st-key-vtab_"] button{background:transparent!important;color:var(--mfg)!important;height:32px;min-height:32px;margin-bottom:0;border-radius:9px!important;}
[class*="st-key-vtab_"] button:hover{background:rgba(255,255,255,.55)!important;color:var(--fg)!important;}
[class*="st-key-vtabon_"] button{background:var(--bg)!important;color:var(--fg)!important;font-weight:700;}
[class*="st-key-vtabon_"] button *{color:var(--fg)!important;}
[class*="st-key-vtabon_"] button:before,[class*="st-key-vtabon_"] button:after{content:"";position:absolute;bottom:0;width:10px;height:10px;pointer-events:none;}
[class*="st-key-vtabon_"] button:before{left:-10px;background:radial-gradient(circle at 0 0,transparent 9.5px,var(--bg) 10px);}
[class*="st-key-vtabon_"] button:after{right:-10px;background:radial-gradient(circle at 100% 0,transparent 9.5px,var(--bg) 10px);}
@media(max-width:700px){[class*="st-key-vtab_"] button,[class*="st-key-vtabon_"] button{width:44vw;}}
</style>
"""
ss = st.session_state
ss.setdefault("dark", False)
ss.setdefault("view", "Client")
ss.setdefault("claims", [])
st.markdown(CSS.replace("__VARS__", DARK if ss.dark else LIGHT).replace("__SCHEME__", "dark" if ss.dark else "light"), unsafe_allow_html=True)


# ---------------- backend (same lists the Client tab uses) ----------------
@st.cache_data(ttl=45, show_spinner=False)
def backend_health(base):
    try:
        return {"ok": True, **api.health()}
    except api.ApiError as ex:
        return {"ok": False, "error": str(ex)}


@st.cache_data(ttl=600, show_spinner=False)
def backend_taxonomy(base):
    try:
        return {"parts": api.parts(), "detectors": api.detectors()}
    except api.ApiError:
        return {"parts": [], "detectors": []}


BACKEND = api.enabled()
_H = backend_health(api.base_url()) if BACKEND else None
_T = backend_taxonomy(api.base_url()) if (_H and _H["ok"]) else {"parts": [], "detectors": []}
PART_ID = {(p.get("label") or p.get("part_name")): p["part_id"] for p in _T["parts"]}
LIVE = bool(_H and _H["ok"] and PART_ID)
PANEL_OPTIONS = list(PART_ID) if LIVE else L.PANELS
PID = PART_ID if LIVE else {p: i + 1 for i, p in enumerate(L.PANELS)}
DEFAULT_LABEL = {"Scratch": "Scratch", "Dent": "Dent", "Dislodged": "Dislodged", "Torn": "Torn",
                 "Smashed": "Smashed glass", "Broken": "Broken lamp"}
DTYPES = [(d["key"], d.get("label") or d["key"]) for d in _T["detectors"]] if (LIVE and _T["detectors"]) else list(DEFAULT_LABEL.items())
DLABEL = dict(DTYPES)


def norm_other(x):
    """Client damage label -> detector key."""
    x = str(x).lower()
    for tid, lab in DTYPES:
        if x in (tid.lower(), lab.lower()):
            return tid
    return None


def e(x):
    return html.escape(str(x))


def pretty(x):
    s = str(x or "").replace("_", " ").strip()
    if s.isupper():
        s = s.lower()
    return s[:1].upper() + s[1:]


# ---------------- claim analysis ----------------
# Not towed: the detector for the client's damage type must confirm it in the photo.
# Towed:     the severity model's Repair/Replace verdict must equal what the client chose.
# Every item matched -> claim approved automatically; otherwise it waits for an adjuster.
def check_item(it):
    t = norm_other(it["detail"])
    row = {"panel": it["panel"], "client": it["detail"], "model": "—", "conf": None, "severity": None, "fix": "", "other": [],
           "image": it["data"], "status": "Needs review", "reason": ""}
    if t is None:
        row["reason"] = "No detector exists for this damage type."
        return row
    try:
        r = api.minor_check(t, it["data"], None, True) if LIVE else L.mock_minor_check(t, it["data"], None)
    except Exception as ex:
        row["reason"] = str(ex)
        return row
    if r.get("available") is False or r.get("error"):
        row["reason"] = r.get("error") or "This detector is not available."
        return row
    sev = r.get("severity") or {}
    ok = bool(r.get("confirmed"))
    row.update(model="Confirmed" if ok else "Not found", conf=r.get("max_conf"), fix=pretty(r.get("fix_type")),
               severity=round(sev["composite"]) if sev.get("ok") and sev.get("composite") is not None else None,
               other=[DLABEL.get(x, x) for x in dict.fromkeys(norm_other(y) for y in (r.get("other_damage") or [])) if x and x != t],
               image=api.b64_bytes(r.get("image_jpeg_b64")) or it["data"], status="Matched" if ok else "Needs review",
               reason="The model found the damage the client reported." if ok else "The model did not find this damage in the photo.")
    return row


def grade_item(it):
    row = {"panel": it["panel"], "client": it["detail"], "model": "—", "conf": None, "severity": None, "fix": "", "other": [],
           "image": it["data"], "status": "Needs review", "reason": ""}
    try:
        r = api.severity(it["data"]) if LIVE else L.mock_severity(it["data"])
    except Exception as ex:
        row["reason"] = str(ex)
        return row
    verdict = pretty(r.get("verdict")) if r.get("ok", True) else ""
    if not verdict:
        row["reason"] = r.get("note") or "The model could not grade this photo."
        return row
    ok = verdict == it["detail"]
    row.update(model=verdict, severity=None if r.get("composite") is None else round(r["composite"]), status="Matched" if ok else "Needs review",
               reason="The model agrees with the client." if ok else f"The client chose {it['detail'].lower()}; the model suggests {verdict.lower()}.")
    return row


def analyse(c):
    c["analysis"] = [(grade_item if c["mode"] == "Towed" else check_item)(it) for it in c["items"]]
    auto = bool(c["analysis"]) and all(r["status"] == "Matched" for r in c["analysis"])
    c["status"], c["decided_by"] = ("Approved", "Automatic") if auto else ("Needs review", None)


def decide(cid, status):
    c = next(x for x in ss.claims if x["id"] == cid)
    c["status"], c["decided_by"] = status, "Adjuster"


def recheck(cid):
    c = next(x for x in ss.claims if x["id"] == cid)
    c["analysis"], c["status"], c["decided_by"] = None, "New", None


def set_view(v):
    ss.view = v


def toggle_theme():
    ss.dark = not ss.dark


# ---------------- view tabs (Client claim / Insurance review) ----------------
with st.container(key="tabbar"):
    _tc = st.columns([1, 1, 4])
    _todo = sum(c["status"] in ("New", "Needs review") for c in ss.claims)
    for _c, (_id, _label, _icon) in zip(_tc, [("Client", "Client claim", ":material/person:"),
                                              ("Insurance", f"Insurance review ({_todo})" if _todo else "Insurance review", ":material/apartment:")]):
        _c.button(_label, icon=_icon, key=f"{'vtabon' if ss.view == _id else 'vtab'}_{_id.lower()}", on_click=set_view, args=(_id,))
with st.container(key="topstatus"):
    st.markdown(f"<div class='pill'><span class='dot'></span><span class='ptxt'>{'Connected' if LIVE else 'Demo workspace'}</span></div>", unsafe_allow_html=True)
with st.container(key="theme_toggle"):
    st.button("", icon=":material/light_mode:" if ss.dark else ":material/dark_mode:", key="theme_btn", on_click=toggle_theme,
              help="Switch to light mode" if ss.dark else "Switch to dark mode")

if ss.view == "Client":
    client.render(panels=PANEL_OPTIONS, part_ids=PID, damages=[lab for _, lab in DTYPES], live=LIVE)
    st.stop()

# ---------------- insurance review ----------------
client.hero("Insurance review", "Client", "claims", "Each claim is checked against the model automatically. Matches are approved; the rest wait for you.")
_pending = [c for c in ss.claims if c["analysis"] is None]
if _pending:
    with st.spinner(f"Checking {len(_pending)} claim(s) with the model…"):
        for _c in _pending:
            analyse(_c)
    st.rerun()

claims = ss.claims
count = lambda s: sum(c["status"] == s for c in claims)
st.markdown("<div class='stats'>" + "".join(f"<div class='stat'><b>{n}</b><span>{t}</span></div>" for t, n in
            [("Needs review", count("Needs review")), ("Approved", count("Approved")), ("Rejected", count("Rejected"))]) + "</div>", unsafe_allow_html=True)
if not claims:
    st.markdown("<div class='mc-empty'>No claims yet. Submit one on the Client tab and it will appear here, already checked.</div>", unsafe_allow_html=True)
    st.stop()

COLOR = {"Approved": "var(--ok)", "Needs review": "var(--warn)", "Rejected": "var(--bad)", "New": "var(--mfg)"}


def render_claim(c):
    tow = c["mode"] == "Towed"
    for r in c["analysis"]:
        a, b = st.columns([1, 3], vertical_alignment="center")
        a.image(r["image"], use_container_width=True)
        kv = [("Client said", r["client"]), ("Model", r["model"])]
        if r["conf"] is not None:
            kv.append(("Confidence", f"{float(r['conf']):.0%}"))
        if r["severity"] is not None:
            kv.append(("Severity", f"{r['severity']}/100"))
        if r["fix"] and not tow:
            kv.append(("Fix", r["fix"]))
        b.markdown(f"<b>{e(r['panel'])}</b> <span class='{'s-Matched' if r['status'] == 'Matched' else 's-NeedsReview'}' style='margin-left:.5rem'>{e(r['status'])}</span>"
                   f"<div class='kv'>" + "".join(f"<span>{e(k)} <b>{e(v)}</b></span>" for k, v in kv) + "</div>"
                   f"<div class='hint'>{e(r['reason'])}</div>"
                   + (f"<div class='note warn'>The model also sees: {e(', '.join(r['other']))}.</div>" if r["other"] else ""), unsafe_allow_html=True)
    if c["status"] == "Needs review":
        b1, b2, b3 = st.columns(3)
        b1.button("Approve", icon=":material/check_circle:", key=f"ap_{c['id']}", type="primary", on_click=decide, args=(c["id"], "Approved"))
        b2.button("Reject", icon=":material/cancel:", key=f"rj_{c['id']}", on_click=decide, args=(c["id"], "Rejected"))
        b3.button("Re-run check", icon=":material/refresh:", key=f"rr_{c['id']}", on_click=recheck, args=(c["id"],))
    else:
        st.markdown(f"<div class='hint'>{e(c['status'])} · {'matched the model, no review needed' if c['decided_by'] == 'Automatic' else 'decided by the adjuster'}</div>", unsafe_allow_html=True)
        st.button("Re-run check", icon=":material/refresh:", key=f"rr_{c['id']}", on_click=recheck, args=(c["id"],))


for c in sorted(reversed(claims), key=lambda x: x["status"] != "Needs review"):   # claims needing a decision first
    head = f"{c['id']} · {c['mode']} · {len(c['items'])} item(s)"
    if c["status"] == "Needs review":
        with st.container(key=f"card_claim_{c['id']}"):
            st.markdown(f"<div class='ph-head'><span class='badge'>{e(c['id'][2:])}</span><div><b>{e(head)}</b></div>"
                        f"<span class='tick' style='color:{COLOR[c['status']]}'>{e(c['status'])}</span></div>", unsafe_allow_html=True)
            render_claim(c)
    else:
        with st.expander(f"{head} · {c['status']}"):
            render_claim(c)
