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
DUP_BITS = 5


def ahash(im):
    g = np.asarray(im.convert("L").resize((8, 8), Image.LANCZOS), dtype=np.float32)
    return int("".join("1" if b else "0" for b in (g > g.mean()).flatten()), 2)


def hamming(a, b):
    return bin(a ^ b).count("1")


def check_single(data: bytes, min_short=100, min_long=100):
    """Validity + quality checks on one photo. 'blocking' must be fixed by a retake;
    'soft' can be overridden by the user."""
    blocking, soft = [], []
    if len(data) > MAX_BYTES:
        return {"blocking": ["file is larger than 12 MB"], "soft": [], "hash": None, "size": None}
    try:
        Image.open(io.BytesIO(data)).verify()
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    except Exception:
        return {"blocking": ["not a readable image (corrupt or unsupported file)"], "soft": [],
                "hash": None, "size": None}
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
    return {"blocking": blocking, "soft": soft, "hash": ahash(im), "size": (w, h)}


# ---------------- demo-mode stand-ins (used only when no backend is connected) ----------------
def mock_minor_check(damage_type, data, threshold=None):
    """Shaped like the backend's /journeys/minor/check response. Deterministic per photo."""
    rng = random.Random(hashlib.md5(damage_type.encode() + data).hexdigest())
    thr = 0.5 if threshold is None else float(threshold)
    conf = round(rng.uniform(0.25, 0.96), 2)
    others = [d for d in DAMAGES if d != damage_type and rng.random() < 0.12][:1]
    sev = round(rng.uniform(15, 90))
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    W, H = img.size
    x, y = rng.uniform(0.15, 0.5), rng.uniform(0.15, 0.5)
    box = [x * W, y * H, (x + 0.3) * W, (y + 0.3) * H]
    d = ImageDraw.Draw(img)
    d.rectangle(box, outline=(239, 68, 68), width=max(3, W // 250))
    d.text((box[0] + 4, box[1] + 4), f"{damage_type} {conf:.0%}", fill=(239, 68, 68))
    img.thumbnail((900, 900))
    b = io.BytesIO()
    img.save(b, "JPEG", quality=80)
    return {"damage_type": damage_type, "label": damage_type, "confirmed": conf >= thr, "available": True, "error": None,
            "max_conf": conf, "thr": thr, "other_damage": others, "quality": {},
            "severity": {"ok": True, "configured": False, "composite": sev}, "fix_type": "replace" if sev > 70 else "repair",
            "image_jpeg_b64": base64.b64encode(b.getvalue()).decode()}


def mock_minor_finalize(items):
    """Shaped like /journeys/minor/finalize. part_ids are 1-based indexes into PANELS in demo mode."""
    rows = []
    for it in items:
        rows.append({"damage_type": it["damage_type"], "damage": it["damage_type"].title(), "confirmed": it["confirmed"],
                     "max_conf": it["max_conf"], "severity": it["severity"], "severity_source": it["severity_source"],
                     "fix_type": "replace" if it["severity"] > 70 else "repair", "part_ids": it["part_ids"],
                     "part_names": [PANELS[i - 1] for i in it["part_ids"] if 0 < i <= len(PANELS)],
                     "status": "matched" if it["confirmed"] else "needs_review",
                     "reason": "The detector confirmed it." if it["confirmed"] else "The detector did not confirm it. A person should review it."})
    n = sum(r["status"] != "matched" for r in rows)
    return {"outcome": "needs_review" if n else "matched",
            "summary": f"{n} of {len(rows)} declared damage type(s) need review." if n else "Every declared damage type was confirmed.",
            "needs_review_count": n, "hidden_damage_flag": False, "rows": rows, "hidden_damage": None, "hidden_damage_note": None,
            "estimate": [{"part_id": r["part_ids"][0], "part_name": (r["part_names"] or [None])[0], "severity": r["severity"], "fix_type": r["fix_type"]}
                         for r in rows if r["part_ids"]]}


def mock_severity(data):
    """Shaped like /severity/grade. Deterministic per photo."""
    sev = round(random.Random(hashlib.md5(b"sev" + data).hexdigest()).uniform(15, 90))
    return {"ok": True, "configured": False, "composite": sev, "cutoff": 70, "verdict": "REPLACE" if sev > 70 else "REPAIR"}
