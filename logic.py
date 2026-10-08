"""Logic for the car damage claims demo. No Streamlit imports, so it can be unit tested.

The `mock_*` functions are demo-mode stand-ins, used only when no backend is connected
(API_BASE_URL unset or unreachable). They are shaped like the real API responses.
"""
import base64
import hashlib
import io
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageOps

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC = True
except Exception:
    HEIC = False

PANELS = ["Front bumper", "Rear bumper", "Hood", "Trunk", "Roof", "Windshield",
          "Left front door", "Left rear door", "Right front door", "Right rear door",
          "Left fender", "Right fender", "Headlight", "Taillight", "Wheel/Tire"]
DAMAGES = ["Scratch", "Dent", "Smashed", "Broken", "Torn", "Dislodged"]
DAMAGE_INFO = {
    "Scratch": "Surface marks or lines in the paint. The panel keeps its shape.",
    "Dent": "Panel pushed inward with no break.",
    "Smashed": "Cracked or shattered glass on the windscreen, side windows or rear screen.",
    "Broken": "A headlight or taillight that has snapped, split into pieces or has a piece missing.",
    "Torn": "A long scratch that has slightly ripped the surface, leaving a jagged edge.",
    "Dislodged": "Part is still attached but knocked out of position, with an uneven gap.",
}


def local_damage(label):
    """Map any damage label (local 'Smashed' or backend 'Smashed glass' / 'Broken lamp') to a local type, or None."""
    s = str(label or "").strip().lower()
    if not s:
        return None
    for n in DAMAGES:
        if n.lower() in s or s in n.lower():
            return n
    for word, n in (("glass", "Smashed"), ("lamp", "Broken"), ("light", "Broken")):
        if word in s:
            return n
    return None


# ---------------- example photos (examples/<damage>_<1|2>.<jpg|jpeg|png|webp>) ----------------
EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples")


def find_example(damage, variant=0):
    """Path of the example photo for a damage type (variant 0 or 1), or None. Case-insensitive."""
    want = f"{str(damage).lower()}_{variant + 1}"
    try:
        files = sorted(os.listdir(EXAMPLES_DIR))
    except OSError:
        return None
    for f in files:
        stem, ext = os.path.splitext(f)
        if stem.lower() == want and ext.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            return os.path.join(EXAMPLES_DIR, f)
    return None


# ---------------- image validity ----------------
MAX_BYTES = 12 * 1024 * 1024


def check_single(data: bytes, min_short=100, min_long=100):
    """Validity + quality checks on one photo. 'blocking' must be fixed by a retake;
    'soft' can be overridden by the user."""
    blocking, soft = [], []
    if len(data) > MAX_BYTES:
        return {"blocking": ["file is larger than 12 MB"], "soft": [], "size": None}
    try:
        Image.open(io.BytesIO(data)).verify()
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    except Exception:
        return {"blocking": ["not a readable image (corrupt or unsupported file)"], "soft": [],
                "size": None}
    w, h = im.size
    if min(w, h) < min_short or max(w, h) < min_long:
        blocking.append(f"resolution too low ({w}x{h}); need at least {min_long}x{min_short}")
    if max(w, h) / min(w, h) > 3:
        blocking.append("unusual shape (screenshot or panorama?)")
    small = im.copy()
    small.thumbnail((800, 800))
    g = np.asarray(small.convert("L"), dtype=np.float32)
    mean, std = g.mean(), g.std()
    if std < 3 or (std < 12 and 50 <= mean <= 215):
        blocking.append("image looks blank or uniform")
    else:
        lap = -4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
        if lap.var() < 40:
            blocking.append("Photo is blurry. Please don't upload it; hold steady and retake.")
        if mean < 50:
            blocking.append("Photo is too dark. Please don't upload it; retake in better light.")
        elif mean > 215:
            blocking.append("Photo is overexposed. Please don't upload it; retake away from glare.")
    return {"blocking": blocking, "soft": soft, "size": (w, h)}


# ---------------- demo-mode stand-ins (used only when no backend is connected) ----------------
BOX_COLORS = [(239, 68, 68), (37, 99, 235), (234, 138, 0), (124, 58, 237), (5, 150, 105), (219, 39, 119)]


def mock_annotate(data, marks):
    """Demo-mode annotated photo: one box per damage on a single image. marks = [(label, confidence, (x0, y0, x1, y1) as fractions)]. Returns JPEG bytes."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    W, H = img.size
    d = ImageDraw.Draw(img)
    for n, (label, conf, (x0, y0, x1, y1)) in enumerate(marks):
        col = BOX_COLORS[n % len(BOX_COLORS)]
        box = [x0 * W, y0 * H, x1 * W, y1 * H]
        d.rectangle(box, outline=col, width=max(3, W // 250))
        d.text((box[0] + 4, box[1] + 4), f"{label} {conf:.0%}", fill=col)
    img.thumbnail((900, 900))
    b = io.BytesIO()
    img.save(b, "JPEG", quality=80)
    return b.getvalue()


def mock_minor_check(damage_type, data, threshold=None):
    """Shaped like the backend's /journeys/minor/check response. Deterministic per photo. (`box` is a demo-only extra.)"""
    rng = random.Random(hashlib.md5(damage_type.encode() + data).hexdigest())
    thr = 0.5 if threshold is None else float(threshold)
    conf = round(rng.uniform(0.25, 0.96), 2)
    others = [d for d in DAMAGES if d != damage_type and rng.random() < 0.12][:1]
    sev = round(rng.uniform(15, 90))
    x, y = rng.uniform(0.15, 0.5), rng.uniform(0.15, 0.5)
    box = (x, y, x + 0.3, y + 0.3)
    return {"damage_type": damage_type, "label": damage_type, "confirmed": conf >= thr, "available": True, "error": None,
            "max_conf": conf, "thr": thr, "other_damage": others, "quality": {}, "box": box,
            "severity": {"ok": True, "configured": False, "composite": sev}, "fix_type": "replace" if sev > 70 else "repair",
            "image_jpeg_b64": base64.b64encode(mock_annotate(data, [(damage_type, conf, box)])).decode()}


def mock_hidden_damage(findings):
    """Demo-mode hidden-damage assessment, shaped like the backend's `hidden_damage` block.

    `findings` must list EVERY damage present on the vehicle, not only the ones that were graded: dicts like
    {"part": "Hood", "damage": "Dent", "severity": 62 or None}. Damage that could not be graded, or that was only seen
    in a photo, has severity None but still counts. Plain numbers (severities only) are accepted too.
    Risk starts from the worst severity and grows with how many different damages and parts are affected.
    """
    fs = [f if isinstance(f, dict) else {"severity": f} for f in findings]
    sev = [float(f["severity"]) for f in fs if f.get("severity") is not None]
    if not sev:
        return None
    kinds = {(f.get("part"), local_damage(f.get("damage")) or str(f.get("damage") or "").lower())
             for f in fs if f.get("part") or f.get("damage")}
    parts = {f["part"] for f in fs if f.get("part")}
    p = min(99, round(max(sev) * 0.6 + 4 * max(len(kinds) - 1, 0) + 4 * max(len(parts) - 1, 0)))
    likely = p >= 38
    seen = sorted(f"{part or 'Vehicle'} · {dmg.title()}" if dmg else str(part) for part, dmg in kinds)
    basis = f" Based on {len(kinds)} damage(s) on {len(parts)} part(s)." if kinds else ""
    return {"verdict": "elevated risk" if likely else "low risk", "hidden_damage_likely": likely, "probability": p / 100,
            "damages_considered": seen,
            "summary": f"{'Elevated' if likely else 'Low'} risk of hidden damage ({p}%).{basis} Simulated in demo mode."}


def mock_minor_finalize(items, extra=None):
    """Shaped like /journeys/minor/finalize. part_ids are 1-based indexes into PANELS in demo mode.
    `extra`: damages present that are not in `items` (could not be checked, or only seen in a photo); they feed the hidden-damage risk."""
    rows = []
    for it in items:
        rows.append({"damage_type": it["damage_type"], "damage": it["damage_type"].title(), "confirmed": it["confirmed"],
                     "max_conf": it["max_conf"], "severity": it["severity"], "severity_source": it["severity_source"],
                     "fix_type": "replace" if it["severity"] > 70 else "repair", "part_ids": it["part_ids"],
                     "part_names": [PANELS[i - 1] for i in it["part_ids"] if 0 < i <= len(PANELS)],
                     "status": "matched" if it["confirmed"] else "needs_review",
                     "reason": "The detector confirmed it." if it["confirmed"] else "The detector did not confirm it. A person should review it."})
    n = sum(r["status"] != "matched" for r in rows)
    hidden = mock_hidden_damage([{"part": pn, "damage": r["damage_type"], "severity": r["severity"]}
                                 for r in rows for pn in (r["part_names"] or [None])] + list(extra or []))
    likely = bool(hidden and hidden["hidden_damage_likely"])
    return {"outcome": "needs_review" if n else "matched",
            "summary": f"{n} of {len(rows)} declared damage type(s) need review." if n else "Every declared damage type was confirmed.",
            "needs_review_count": n, "hidden_damage_flag": likely, "rows": rows, "hidden_damage": hidden, "hidden_damage_note": None,
            "estimate": [{"part_id": r["part_ids"][0], "part_name": (r["part_names"] or [None])[0], "severity": r["severity"], "fix_type": r["fix_type"]}
                         for r in rows if r["part_ids"]]}


def mock_severity(data):
    """Shaped like /severity/grade. Deterministic per photo."""
    sev = round(random.Random(hashlib.md5(b"sev" + data).hexdigest()).uniform(15, 90))
    return {"ok": True, "configured": False, "composite": sev, "cutoff": 70, "verdict": "REPLACE" if sev > 70 else "REPAIR"}
