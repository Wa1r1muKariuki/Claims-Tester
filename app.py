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
header[data-testid="stHeader"],#MainMenu,footer{display:none!important;}
.block-container{max-width:1240px;padding:0 1.5rem 4rem!important;}
h1,h2,h3,.disp{font-family:'Manrope',sans-serif!important;color:var(--fg);}
hr{border-color:var(--border)!important;}
:where([data-testid="stWidgetLabel"] p,[data-testid="stCheckbox"] p,[data-testid="stCaptionContainer"],[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li){color:var(--fg);}
:where([data-testid="stCaptionContainer"]){color:var(--mfg);}

/* ---------- hero (full bleed) ---------- */
.hero{position:relative;overflow:hidden;width:100vw;margin-left:calc(50% - 50vw);margin-bottom:2rem;min-height:400px;background:var(--ink);isolation:isolate;}
.hero img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.55;z-index:-3;}
.hero .shade{position:absolute;inset:0;z-index:-2;background:linear-gradient(90deg,var(--ink) 0%,rgba(13,27,34,.86) 42%,rgba(13,27,34,.15) 100%),
 radial-gradient(60% 90% at 85% 0%,rgba(20,179,168,.35),transparent 60%);}
.hero .grid{position:absolute;inset:0;z-index:-1;opacity:.18;background-image:linear-gradient(rgba(255,255,255,.25) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.25) 1px,transparent 1px);
 background-size:44px 44px;-webkit-mask-image:linear-gradient(180deg,#000,transparent 85%);mask-image:linear-gradient(180deg,#000,transparent 85%);}
.hero:after{content:"";position:absolute;left:0;right:0;bottom:0;height:70px;background:linear-gradient(180deg,transparent,var(--bg));}
.hero-in{max-width:1240px;margin:0 auto;padding:1.1rem 1.5rem 4.2rem;}
.nav{display:flex;justify-content:space-between;align-items:center;padding-right:4.2rem;}
.brand{display:flex;gap:.7rem;align-items:center;}
.logo{width:38px;height:38px;border-radius:11px;background:linear-gradient(135deg,var(--p1),var(--p2));display:flex;align-items:center;justify-content:center;box-shadow:0 8px 20px -6px var(--glow);}
.bt{font-family:'Manrope';font-weight:800;font-size:.85rem;line-height:1.1;color:#fff;letter-spacing:.02em;} .bs{font-size:.66rem;color:rgba(255,255,255,.65);letter-spacing:.14em;}
.pill{display:flex;gap:.45rem;align-items:center;font-size:.74rem;font-weight:600;color:#fff;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.22);
 backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);padding:.42rem .85rem;border-radius:99px;}
.dot{width:8px;height:8px;border-radius:50%;background:#4ade80;box-shadow:0 0 0 4px rgba(74,222,128,.25);}
.hero .txt{padding-top:3.2rem;max-width:660px;color:#fff;}
.kick{font-size:.7rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);}
.hero .kick{display:inline-block;color:#9df3ea!important;background:rgba(79,227,213,.14);border:1px solid rgba(79,227,213,.35);padding:.3rem .75rem;border-radius:99px;}
.hero h1{color:#fff!important;font-size:3.1rem;line-height:1.05;font-weight:800;margin:1rem 0 0;padding:0;letter-spacing:-.02em;}
.hero h1 em{font-style:normal;background:linear-gradient(90deg,#7ff5e9,#4aa8ff);-webkit-background-clip:text;background-clip:text;color:transparent;}
.hero p{color:rgba(255,255,255,.82)!important;margin:1rem 0 0;max-width:470px;font-size:1.02rem;line-height:1.55;}
.chips{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:1.4rem;}
.chips span{font-size:.75rem;font-weight:600;color:#fff;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);padding:.35rem .75rem;border-radius:99px;}
.st-key-theme_toggle{position:fixed;top:1.1rem;right:1.5rem;z-index:1000;width:auto!important;}
.st-key-theme_toggle button{width:44px!important;height:44px!important;min-height:44px!important;padding:0!important;border-radius:50%!important;color:#fff!important;
 background:rgba(255,255,255,.14)!important;border:1px solid rgba(255,255,255,.35)!important;backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);box-shadow:0 6px 20px -6px rgba(0,0,0,.5)!important;}
.st-key-theme_toggle button:hover{transform:rotate(18deg) scale(1.06)!important;background:rgba(255,255,255,.26)!important;}
.st-key-theme_toggle button *{color:#fff!important;font-size:1.25rem;}

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
[data-testid="stBaseButton-segmented_control"],[data-testid="stBaseButton-pills"]{background:var(--card2)!important;color:var(--fg)!important;border:1px solid var(--border)!important;border-radius:10px!important;}
[data-testid="stBaseButton-segmented_controlActive"],[data-testid="stBaseButton-pillsActive"]{background:var(--secondary)!important;color:var(--accent)!important;border:1px solid var(--accent)!important;border-radius:10px!important;}

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
@media(max-width:700px){.hero h1{font-size:2.2rem}.hero-in{padding-bottom:3rem}.stats{grid-template-columns:1fr}}
</style>
"""
ss = st.session_state
ss.setdefault("dark", False)
st.markdown(CSS.replace("__VARS__", DARK if ss.dark else LIGHT).replace("__SCHEME__", "dark" if ss.dark else "light"), unsafe_allow_html=True)
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
def example(damage, variant=0):
    pats = [f"{damage.lower()}_{variant + 1}.*"] + ([f"{damage.lower()}.*"] if variant == 0 else [])
    for pat in pats:
        for p in glob.glob(os.path.join("examples", pat)):
            if not p.endswith(".txt"):
                return Image.open(p).convert("RGB")
    return L.example_image(damage, variant)


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


def toggle_theme():
    ss.dark = not ss.dark


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
                "- Blurry, dark or overexposed photos: please don't upload them.\n"
                "- Each angle needs a different photo.")
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
form_ready = (bool(rep) and not rep["error"]) if towed \
    else bool((items or ss.flags["none_minor"]) and ss.flags["confirmed"])
sig = hashlib.md5(b"".join(ss.photos[v] for v in L.VIEWS if v in ss.photos)).hexdigest()
dets_ok = ss.get("dets") is not None and ss.get("dets_sig") == sig
stages = ["Photos", "Garage report" if towed else "Damage details", "Results"]

# ---------------- hero ----------------
img = f"<img src='{hero_uri()}' alt=''>" if hero_uri() else ""
st.markdown(f"""<div class='hero'>{img}<div class='shade'></div><div class='grid'></div><div class='hero-in'>
<div class='nav'><div class='brand'><div class='logo'><svg width='21' height='21' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2'
stroke-linecap='round' stroke-linejoin='round'><circle cx='11' cy='11' r='7'/><path d='m21 21-4.3-4.3'/><path d='m8 11 2 2 4-4'/></svg></div>
<div><div class='bt'>CAR DAMAGE CHECK</div><div class='bs'>VEHICLE INSPECTION</div></div></div>
<div class='pill'><span class='dot'></span> Demo workspace</div></div>
<div class='txt'><div class='kick'>AI vehicle inspection</div><h1>Car damage<br><em>detection demo</em></h1>
<p>Capture four angles, document the damage, and review your findings in one place.</p>
<div class='chips'><span>4 guided angles</span><span>6 damage types</span><span>Instant comparison report</span></div></div></div></div>""",
            unsafe_allow_html=True)
with st.container(key="theme_toggle"):
    st.button("", icon=":material/light_mode:" if ss.dark else ":material/dark_mode:", key="theme_btn", on_click=toggle_theme,
              help="Switch to light mode" if ss.dark else "Switch to dark mode")

left, right = st.columns([1, 3.6], gap="large")

# ---------------- sidebar ----------------
with left:
    st.markdown("<div class='side-h'>Your inspection</div>", unsafe_allow_html=True)
    done = [photo_ready, form_ready and photo_ready, dets_ok]
    icons = [":material/photo_camera:", ":material/description:", ":material/fact_check:"]
    for i, label in enumerate(stages):
        st.button(label, icon=":material/check_circle:" if done[i] else icons[i], key=f"{'navon' if ss.step == i else 'nav'}_{i}",
                  on_click=go, args=(i,))
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
        st.button(f"Continue to {stages[1].lower()}", icon=":material/arrow_forward:", icon_position="right", key="to1", type="primary", disabled=not photo_ready, on_click=go, args=(1,))

    elif ss.step == 1:
        head(2, "Garage report" if towed else "Document the damage",
             "Attach the garage report. We read it and summarise the damage it describes." if towed else "Add any visible damage you notice on the vehicle.")
        if towed:
            with st.container(key="card_report"):
                st.markdown("**Garage report**  \n<span class='hint'>PDF, image or CSV · up to 15 MB</span>", unsafe_allow_html=True)
                if rep:
                    st.markdown(f"<div class='note {'bad' if rep['error'] else 'ok'}'>"
                                f"{html.escape(rep['error'] or rep['name'] + ' accepted. ' + rep['note'])}</div>", unsafe_allow_html=True)
                    if st.button("Replace report", icon=":material/refresh:", key="rep_replace"):
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
            if rep and not rep["error"]:
                g = ss.garage
                st.markdown("### Garage report summary")
                st.markdown("<div class='stats'>" + "".join(f"<div class='stat'><b{cls}>{v}</b><span>{t}</span></div>" for t, v, cls in
                            [("Damage items", len(g), ""), ("Parts affected", len({p for p, _ in g}), ""),
                             ("Report file", html.escape(rep["name"]), " class='sm'")]) + "</div>", unsafe_allow_html=True)
                if g:
                    rows = "".join(f"<tr><td><b>{html.escape(p)}</b></td><td><span class='tag'>{html.escape(d)}</span></td></tr>" for p, d in g)
                    st.markdown(f"<div class='tbl'><h3>Damage listed in the report</h3><table><thead><tr><th>Part</th><th>Damage</th></tr></thead>"
                                f"<tbody>{rows}</tbody></table></div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='banner ok'><div><h3>No damage listed</h3><p>The garage report does not list any damage.</p></div></div>",
                                unsafe_allow_html=True)
                if not os.environ.get("MODEL_API_URL") and not rep["name"].lower().endswith(".csv"):
                    st.caption("Demo mode: PDF and image reports are read with a simulated extractor. CSV reports are read exactly.")
        else:
            key = "declared"
            with st.container(key="card_form"):
                a, b = st.columns([6, 1.6], vertical_alignment="center")
                a.markdown("**Declared damage**  \n<span class='hint'>Select a vehicle part and the type of damage.</span>", unsafe_allow_html=True)
                if b.button("Guide", icon=":material/help:", key="guide_btn"):
                    guide(ss.get(f"{key}_dmg", L.DAMAGES[0]))
                c1, c2, c3 = st.columns([3, 3, 1.4], vertical_alignment="bottom")
                c1.selectbox("Vehicle part", L.PANELS, key=f"{key}_panel")
                c2.selectbox("Damage type", L.DAMAGES, key=f"{key}_dmg")
                c3.button("Add", icon=":material/add:", key=f"{key}_add", type="primary", on_click=add_item, args=(key,))
                st.divider()
                for i, (p, d) in enumerate(ss[key]):
                    x, y = st.columns([9, 1], vertical_alignment="center")
                    x.markdown(f"<div class='item'><b>{html.escape(p)}</b>&nbsp;·&nbsp;<span style='color:var(--mfg)'>{html.escape(d)}</span></div>", unsafe_allow_html=True)
                    y.button("", icon=":material/delete:", key=f"{key}_rm_{i}", on_click=rm_item, args=(key, i))
                if not ss[key]:
                    st.caption("No damage items added yet.")
                st.checkbox("No visible damage to declare", value=ss.flags["none_minor"], key="cb_none_minor",
                            disabled=bool(ss[key]), on_change=_flag, args=("none_minor",))
                st.checkbox("I confirm this list is complete", value=ss.flags["confirmed"], key="cb_confirmed",
                            on_change=_flag, args=("confirmed",))
        p1, p2 = st.columns(2)
        p1.button("Photos", icon=":material/arrow_back:", key="back0", on_click=go, args=(0,))
        p2.button("Review results", icon=":material/arrow_forward:", icon_position="right", key="to2", type="primary",
                  disabled=not (form_ready and photo_ready), on_click=go, args=(2,))
        if not photo_ready:
            st.markdown("<div class='hint' style='color:var(--warn)'>Accept all four photos before continuing.</div>", unsafe_allow_html=True)

    else:
        head(3, "Inspection results", f"Compare {'the garage report' if towed else 'your notes'} against the photo findings.")
        if not (photo_ready and form_ready):
            msg = f"Accept all four photos ({len(good)} of 4 ready)." if not photo_ready else (
                "Upload a valid garage report." if towed
                else "Add damage or select no visible damage, then confirm your list.")
            with st.container(key="card_gate"):
                st.markdown(f"**Complete your inspection first**  \n<span class='hint'>{msg}</span>", unsafe_allow_html=True)
                st.button("Go to " + ("photos" if not photo_ready else stages[1]), key="gate", on_click=go, args=(0 if not photo_ready else 1,))
        else:
            with st.container(key="card_run"):
                a, b = st.columns([4, 1.3], vertical_alignment="center")
                a.markdown(f"**Ready to compare**  \n<span class='hint'>Four photos and {'garage report' if towed else 'damage details'} complete</span>", unsafe_allow_html=True)
                if b.button("Run again" if dets_ok else "Run detection", icon=":material/play_arrow:", key="run", type="primary"):
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
                st.download_button("Download CSV", df.to_csv(index=False), "car-damage-report.csv", "text/csv", icon=":material/download:")
                st.markdown("### Photo findings")
                cols = st.columns(2)
                for i, v in enumerate(L.VIEWS):
                    dv = [d for d in ss.dets if d["view"] == v]
                    with cols[i % 2], st.container(key=f"card_find_{v}"):
                        st.image(L.annotate(ss.photos[v], dv))
                        st.markdown(f"**{v}** <span class='hint'>· {len(dv)} finding(s)</span>", unsafe_allow_html=True)
            elif ss.get("dets") is not None:
                st.warning("Photos changed since the last run. Run detection again.")
