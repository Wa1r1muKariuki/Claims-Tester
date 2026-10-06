"""Client side of the claim flow. Rendered by app.py when the "Client claim" tab is active.

Not towed: pick the damaged part + damage type, then attach one photo per item.
Towed:     list the parts and mark each Repair or Replace, then attach one photo per part.
The client never sees model detections; those stay on the insurance tab.
"""
import base64
import html
import os

import streamlit as st

import logic as L

ss = st.session_state
MODES = ["Not towed", "Towed"]
ACTIONS = ["Repair", "Replace"]
CFG = {"panels": L.PANELS, "part_ids": {}, "damages": L.DAMAGES, "live": False}   # set by render()


def _info(damage):
    """One-line description for a damage type; backend labels like 'Smashed glass' map to the closest local type."""
    for name in L.DAMAGES:
        if name.lower() in damage.lower() or damage.lower() in name.lower():
            return L.DAMAGE_INFO[name]
    return ""


def _init():
    ss.setdefault("cl", {
        "mode": "Not towed",
        "items": {m: [] for m in MODES},   # each mode keeps its own list
        "step": {m: 0 for m in MODES},
        "done": {m: None for m in MODES},
        "seq": 0,
        "pseq": 0,
    })


@st.cache_data(show_spinner=False)
def _check(data):
    return L.check_single(data)


def e(x):
    return html.escape(str(x))


HERO_CSS = """<style>
.hero.sm{min-height:0;margin-bottom:1.4rem;}
.hero.sm .hero-in{padding:1.6rem 1.5rem 2.4rem;}
.hero.sm .txt{padding-top:0;}
.hero.sm h1{font-size:1.8rem;}
.hero.sm p{margin:.5rem 0 0;font-size:.9rem;color:rgba(255,255,255,.85);}
</style>"""


@st.cache_data(show_spinner=False)
def _hero_uri():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "hero.jpg")
    return "data:image/jpeg;base64," + base64.b64encode(open(p, "rb").read()).decode() if os.path.exists(p) else ""


def _hero(title, em, sub):
    img = f"<img src='{_hero_uri()}' alt=''>" if _hero_uri() else ""
    st.markdown(HERO_CSS + f"<div class='hero sm'>{img}<div class='shade'></div><div class='grid'></div><div class='hero-in'><div class='txt'>"
                f"<div class='kick'>Client claim</div><h1>{e(title)}<br><em>{e(em)}</em></h1><p>{e(sub)}</p></div></div></div>", unsafe_allow_html=True)


# ---------------- callbacks ----------------
def _set_mode():
    v = ss.get("cl_mode_ui")
    if v is None:                       # clicking the active option deselects it: keep the current mode
        ss.cl_mode_ui = ss.cl["mode"]
    else:
        ss.cl["mode"] = v


def _add(m):
    part = ss.get("cl_part") or CFG["panels"][0]
    detail = (ss.get("cl_act") or "Repair") if m == "Towed" else (ss.get("cl_dmg") or CFG["damages"][0])
    lst = ss.cl["items"][m]
    if any(i["panel"] == part and i["detail"] == detail for i in lst):
        return
    ss.cl["seq"] += 1
    lst.append({"id": ss.cl["seq"], "panel": part, "part_id": CFG["part_ids"].get(part), "detail": detail, "data": None, "pseq": 0, "accepted": False, "n": 0})


def _remove(m, iid):
    ss.cl["items"][m] = [i for i in ss.cl["items"][m] if i["id"] != iid]


def _step(m, n):
    ss.cl["step"][m] = n


def _drop_photo(m, iid):
    for i in ss.cl["items"][m]:
        if i["id"] == iid:
            i.update(data=None, accepted=False, n=i["n"] + 1)


def _accept(m, iid):
    for i in ss.cl["items"][m]:
        if i["id"] == iid:
            i["accepted"] = bool(ss.get(f"cl_acc_{iid}"))


def _submit(m):
    """Save the claim in the session so the Insurance tab can list and open it."""
    claims = ss.setdefault("claims", [])
    cid = f"C-{len(claims) + 1:03d}"
    items = [{k: i.get(k) for k in ("panel", "part_id", "detail", "data")} for i in ss.cl["items"][m]]
    claims.append({"id": cid, "mode": m, "items": items, "status": "New", "analysis": None})
    ss.cl["done"][m] = {"id": cid, "count": len(items)}


def _reset(m):
    ss.cl["items"][m] = []
    ss.cl["step"][m] = 0
    ss.cl["done"][m] = None


# ---------------- helpers ----------------
def _statuses(items):
    """Per item: blocking / soft messages. The newer of two look-alike photos is blocked."""
    out = {}
    for it in items:
        if not it["data"]:
            continue
        r = _check(it["data"])
        blocking = list(r["blocking"])
        if r["hash"] is not None:
            for o in items:
                if o is it or not o["data"] or o["pseq"] >= it["pseq"]:
                    continue
                ro = _check(o["data"])
                if ro["hash"] is not None and L.hamming(r["hash"], ro["hash"]) <= L.DUP_BITS:
                    blocking.append(f"This looks the same as the {o['panel'].lower()} photo. Use a different photo.")
                    break
        out[it["id"]] = {**r, "blocking": blocking}
    return out


def _head(step, labels):
    pills = " <span class='hint'>→</span> ".join(
        f"<span class='tag' style='{'' if i == step else 'opacity:.55'}'>{i + 1} · {e(l)}</span>" for i, l in enumerate(labels))
    st.markdown(f"<div style='margin-bottom:1rem'>{pills}</div>", unsafe_allow_html=True)


# ---------------- steps ----------------
def _list_step(m, towed, items):
    with st.container(key="card_cl_form"):
        st.markdown(f"**{'Parts to fix' if towed else 'Damaged parts'}**  \n<span class='hint'>"
                    f"{'Choose each part and whether it needs repair or replacement.' if towed else 'Choose each part and the type of damage.'}</span>",
                    unsafe_allow_html=True)
        c1, c2, c3 = st.columns([3, 3, 1.4], vertical_alignment="bottom")
        c1.selectbox("Vehicle part", CFG["panels"], key="cl_part")
        if towed:
            c2.segmented_control("Repair or replace", ACTIONS, default="Repair", key="cl_act")
        else:
            dmg = c2.selectbox("Damage type", CFG["damages"], key="cl_dmg")
        c3.button("Add", icon=":material/add:", key="cl_add", type="primary", on_click=_add, args=(m,))
        if not towed:
            st.caption(_info(dmg))
        st.markdown("<div class='mc-h' style='margin-top:1rem'>Your list</div>", unsafe_allow_html=True)
        if not items:
            st.markdown("<div class='mc-empty'>Nothing added yet.</div>", unsafe_allow_html=True)
        for it in items:
            a, b = st.columns([9, 1], vertical_alignment="center")
            a.markdown(f"<div class='item'><b>{e(it['panel'])}</b>&nbsp;·&nbsp;<span style='color:var(--mfg)'>{e(it['detail'])}</span></div>", unsafe_allow_html=True)
            b.button("", icon=":material/delete:", key=f"cl_rm_{it['id']}", on_click=_remove, args=(m, it["id"]))
    st.button("Continue to photos", icon=":material/arrow_forward:", icon_position="right", key="cl_to_photos", type="primary",
              disabled=not items, on_click=_step, args=(m, 1))


def _photo_step(m, items):
    stat = _statuses(items)

    def good(it):
        s = stat.get(it["id"])
        return bool(s) and not s["blocking"] and (not s["soft"] or it["accepted"])

    ready = sum(good(i) for i in items)
    st.markdown(f"<div class='prog' style='border:0;margin-top:0;padding-top:0'><span>Attach one clear photo for each item</span>"
                f"<span style='color:var(--accent)'>{ready} of {len(items)} ready</span></div>", unsafe_allow_html=True)
    cols = st.columns(2)
    for n, it in enumerate(items):
        iid, s = it["id"], stat.get(it["id"])
        blocked = bool(s and s["blocking"])
        ok = good(it)
        with cols[n % 2], st.container(key=f"card_cl_{iid}"):
            st.markdown(f"<div class='ph-head'><span class='badge'>{n + 1}</span><div><b>{e(it['panel'])}</b><br>"
                        f"<span class='hint'>{e(it['detail'])}</span></div>{'<span class=tick>✓</span>' if ok else ''}</div>", unsafe_allow_html=True)
            if it["data"] and not blocked:
                st.image(it["data"])
            else:
                st.markdown("<div class='ph-empty'><svg width='30' height='30' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.6' "
                            "stroke-linecap='round' stroke-linejoin='round'><path d='M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z'/>"
                            f"<circle cx='12' cy='13' r='4'/></svg>{'Photo needs replacing' if blocked else 'No photo yet'}</div>", unsafe_allow_html=True)
            if s and (blocked or s["soft"]):
                txt = e(" ".join(s["blocking"] + s["soft"]))
                st.markdown(f"<div class='note {'bad' if blocked else 'warn'}'>{txt[:1].upper() + txt[1:]}</div>", unsafe_allow_html=True)
                if not blocked:
                    st.checkbox("Use anyway", value=it["accepted"], key=f"cl_acc_{iid}", on_change=_accept, args=(m, iid))
            if ok:
                st.markdown("<div class='okline'>✓ Photo accepted</div>", unsafe_allow_html=True)
            if it["data"]:
                st.button("Replace photo", icon=":material/refresh:", key=f"cl_rp_{iid}", on_click=_drop_photo, args=(m, iid))
            else:
                mode = st.segmented_control("Source", ["Upload", "Camera"], default="Upload", key=f"cl_src_{iid}", label_visibility="collapsed")
                k = f"{iid}_{it['n']}"
                if mode == "Camera":
                    f = st.camera_input(f"{it['panel']} photo", key=f"cl_cam_{k}", label_visibility="collapsed")
                else:
                    f = st.file_uploader(f"{it['panel']} photo", type=["jpg", "jpeg", "png", "webp"] + (["heic", "heif"] if L.HEIC else []),
                                         key=f"cl_up_{k}", label_visibility="collapsed")
                if f is not None:
                    ss.cl["pseq"] += 1
                    it.update(data=f.getvalue(), pseq=ss.cl["pseq"], accepted=False, n=it["n"] + 1)
                    st.rerun()
    b1, b2 = st.columns(2)
    b1.button("Back", icon=":material/arrow_back:", key="cl_back", on_click=_step, args=(m, 0))
    b2.button("Submit claim", icon=":material/check:", icon_position="right", key="cl_submit", type="primary",
              disabled=not (items and ready == len(items)), on_click=_submit, args=(m,))
    if ready != len(items):
        st.markdown("<div class='hint' style='color:var(--warn)'>Add an accepted photo for every item to submit.</div>", unsafe_allow_html=True)


def _success(m, done):
    count = done["count"]
    st.markdown(f"<div class='banner ok'><div><h3>Success: your claim was submitted</h3>"
                f"<p>Thank you. We received {count} item{'s' if count != 1 else ''} with photos. Your reference is <b>{e(done['id'])}</b>. Your insurer will review them and contact you.</p></div></div>",
                unsafe_allow_html=True)
    st.button("Start a new claim", icon=":material/add:", key="cl_new", type="primary", on_click=_reset, args=(m,))


# ---------------- entry point ----------------
def render(panels=None, part_ids=None, damages=None, live=False):
    """panels/part_ids/damages come from the backend (list parts / detectors) when connected; local demo lists otherwise."""
    CFG.update(panels=list(panels or L.PANELS), part_ids=dict(part_ids or {}), damages=list(damages or L.DAMAGES), live=live)
    _init()
    m = ss.cl["mode"]
    towed = m == "Towed"
    items = ss.cl["items"][m]
    _hero("Report your", "vehicle damage", "Tell us what was damaged and attach a photo of each item.")
    left, right = st.columns([1, 3.6], gap="large")
    with left:
        st.markdown("<div class='side-h'>Vehicle status</div>", unsafe_allow_html=True)
        st.segmented_control("Vehicle status", MODES, default=m, key="cl_mode_ui", on_change=_set_mode, label_visibility="collapsed")
        st.markdown("<div class='hint'>You can switch at any time. Each list is kept separately.</div>", unsafe_allow_html=True)
    with right:
        if ss.cl["done"][m] is not None:
            _success(m, ss.cl["done"][m])
            return
        labels = ["List parts", "Add photos"] if towed else ["Select damage", "Add photos"]
        step = ss.cl["step"][m]
        if step == 1 and not items:
            step = ss.cl["step"][m] = 0
        _head(step, labels)
        if step == 0:
            _list_step(m, towed, items)
        else:
            _photo_step(m, items)
