"""Logic for the car damage demo. No Streamlit imports, so it can be unit tested.

Real model API contract (set MODEL_API_URL): POST multipart field "image",
respond with JSON list of {"Panel", "Damage", "conf", "bbox": [x1, y1, x2, y2]}
(bbox as fractions 0-1 of image width/height).
"""
import hashlib
import io
import os
import random

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageOps

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC = True
except Exception:
    HEIC = False

VIEWS = ["Front", "Rear", "Left", "Right"]
VIEW_HINT = {
    "Front": "Stand 3-4 m away, whole front of the car in frame.",
    "Rear": "Stand 3-4 m away, whole rear of the car in frame.",
    "Left": "Full driver-side profile, wheels to roof.",
    "Right": "Full passenger-side profile, wheels to roof.",
}
PANELS = ["Front bumper", "Rear bumper", "Hood", "Trunk", "Roof", "Windshield",
          "Left front door", "Left rear door", "Right front door", "Right rear door",
          "Left fender", "Right fender", "Headlight", "Taillight", "Wheel/Tire"]
DAMAGES = ["Scratch", "Dent", "Smashed", "Broken", "Torn", "Dislodged"]
DAMAGE_INFO = {
    "Scratch": "Surface marks or lines in the paint. The panel keeps its shape.",
    "Dent": "Panel pushed inward with no break. Shape is distorted, paint mostly intact.",
    "Smashed": "Heavily crushed or shattered, with cracks radiating from the impact.",
    "Broken": "A part has snapped or split into pieces, or a piece is missing.",
    "Torn": "Metal or plastic ripped open, leaving a jagged edge.",
    "Dislodged": "Part is still attached but knocked out of position, with an uneven gap.",
}
ALIASES = {"smached": "Smashed", "smash": "Smashed", "scratches": "Scratch", "dented": "Dent",
           "rip": "Torn", "ripped": "Torn", "displaced": "Dislodged"}


def normalize(label, options):
    s = str(label).strip().lower()
    for o in options:
        if o.lower() == s:
            return o
    a = ALIASES.get(s)
    return a if a in options else None


# ---------------- image validity ----------------
MAX_BYTES = 12 * 1024 * 1024
DUP_BITS = 5


def ahash(im):
    g = np.asarray(im.convert("L").resize((8, 8), Image.LANCZOS), dtype=np.float32)
    return int("".join("1" if b else "0" for b in (g > g.mean()).flatten()), 2)


def hamming(a, b):
    return bin(a ^ b).count("1")


def check_single(data: bytes, min_short=480, min_long=640):
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
            soft.append("blurry, hold steady and retake")
        if mean < 50:
            soft.append("too dark")
        elif mean > 215:
            soft.append("overexposed")
    return {"blocking": blocking, "soft": soft, "hash": ahash(im), "size": (w, h)}


def validate_report(name: str, data: bytes):
    """Validate an uploaded garage report. Returns {error, items, note}."""
    name = name.lower()
    if len(data) > 15 * 1024 * 1024:
        return {"error": "file is larger than 15 MB", "items": [], "note": ""}
    if name.endswith(".pdf"):
        ok = data[:5] == b"%PDF-"
        return {"error": None if ok else "not a valid PDF file", "items": [],
                "note": "PDF attached. Enter its damage items below."}
    if name.endswith(".csv"):
        try:
            df = pd.read_csv(io.BytesIO(data))
            df.columns = [c.strip().title() for c in df.columns]
            df = df[["Panel", "Damage"]].dropna()
        except Exception:
            return {"error": "CSV must have Panel and Damage columns", "items": [], "note": ""}
        items, bad = [], []
        for _, r in df.iterrows():
            p, d = normalize(r["Panel"], PANELS), normalize(r["Damage"], DAMAGES)
            if p and d:
                if (p, d) not in items:
                    items.append((p, d))
            else:
                bad.append(f'{r["Panel"]} / {r["Damage"]}')
        if bad:
            return {"error": "unknown panel or damage type: " + "; ".join(bad[:5]), "items": [], "note": ""}
        return {"error": None, "items": items, "note": f"{len(items)} item(s) loaded from CSV."}
    try:
        Image.open(io.BytesIO(data)).verify()
        return {"error": None, "items": [], "note": "Image attached. Enter its damage items below."}
    except Exception:
        return {"error": "not a readable image", "items": [], "note": ""}


# ---------------- detection ----------------
def detect_damage(view: str, data: bytes):
    """MOCK unless MODEL_API_URL is set. Deterministic per image so reruns are stable."""
    url = os.environ.get("MODEL_API_URL")
    if url:
        import requests
        r = requests.post(url, files={"image": data}, timeout=90)
        r.raise_for_status()
        out = []
        for d in r.json():
            p, dm = normalize(d["Panel"], PANELS), normalize(d["Damage"], DAMAGES)
            if p and dm:
                out.append({"view": view, "Panel": p, "Damage": dm, "conf": float(d["conf"]), "bbox": d["bbox"]})
        return out
    view_panels = {"Front": ["Front bumper", "Hood", "Headlight", "Windshield"],
                   "Rear": ["Rear bumper", "Trunk", "Taillight"],
                   "Left": ["Left front door", "Left rear door", "Left fender", "Wheel/Tire"],
                   "Right": ["Right front door", "Right rear door", "Right fender", "Wheel/Tire"]}
    rng = random.Random(hashlib.md5(data).hexdigest())
    out = []
    for panel in rng.sample(view_panels[view], k=rng.randint(0, 2)):
        x, y = rng.uniform(0.1, 0.5), rng.uniform(0.1, 0.5)
        out.append({"view": view, "Panel": panel, "Damage": rng.choice(DAMAGES),
                    "conf": round(rng.uniform(0.55, 0.97), 2),
                    "bbox": [x, y, x + rng.uniform(0.15, 0.35), y + rng.uniform(0.15, 0.35)]})
    return out


def annotate(data: bytes, dets):
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    d = ImageDraw.Draw(img)
    W, H = img.size
    lw = max(3, W // 250)
    for det in dets:
        x1, y1, x2, y2 = det["bbox"]
        box = [x1 * W, y1 * H, x2 * W, y2 * H]
        d.rectangle(box, outline=(239, 68, 68), width=lw)
        label = f'{det["Panel"]} / {det["Damage"]} {det["conf"]:.0%}'
        d.rectangle([box[0], box[1], box[0] + 8 * len(label) + 8, box[1] + 16], fill=(239, 68, 68))
        d.text((box[0] + 4, box[1] + 2), label, fill="white")
    return img


def compare(ref_items, dets, minor: bool):
    """Journey 1: user-declared vs model. Journey 2: garage report vs model."""
    ref = set(ref_items)
    best = {}
    for d in dets:
        k = (d["Panel"], d["Damage"])
        best[k] = max(best.get(k, 0), d["conf"])
    src = "User-declared" if minor else "Garage report"
    rows = [{"Panel": p, "Damage": dm, "Source": src, "Confidence": best.get((p, dm)),
             "Status": "Matched" if (p, dm) in best else "Needs review"} for p, dm in sorted(ref)]
    rows += [{"Panel": p, "Damage": dm, "Source": "Model only", "Confidence": best[(p, dm)],
              "Status": "Listed only" if minor else "Info"} for p, dm in sorted(set(best) - ref)]
    return pd.DataFrame(rows, columns=["Panel", "Damage", "Source", "Confidence", "Status"])


def outcome(df):
    return "Needs review" if (df["Status"] == "Needs review").any() else "Matched"


# ---------------- illustrated examples ----------------
def example_image(damage, size=(640, 420)):
    """Simple illustration. Drop real photos in examples/<damage>.jpg to override (see app)."""
    W, H = size
    img = Image.new("RGB", size, (232, 236, 242))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((24, 24, W - 24, H - 24), radius=34, fill=(52, 101, 164), outline=(28, 58, 100), width=5)
    d.rounded_rectangle((44, 40, W - 44, H // 3), radius=24, fill=(78, 130, 192))
    rnd = random.Random(damage)
    cx, cy = W // 2, H // 2 + 20
    if damage == "Scratch":
        for i in range(6):
            x = 130 + i * 18
            d.line([(x, 110 + rnd.randint(-5, 5)), (x + 230, H - 110 + rnd.randint(-8, 8))], fill=(238, 241, 245), width=2)
    elif damage == "Dent":
        for i, r in enumerate(range(110, 10, -10)):
            c = (int(52 - i * 2.2), int(101 - i * 4), int(164 - i * 6))
            d.ellipse((cx - r * 1.5, cy - r, cx + r * 1.5, cy + r), fill=c)
        d.ellipse((cx - 80, cy - 60, cx - 20, cy - 25), fill=(130, 175, 220))
    elif damage == "Smashed":
        d.polygon([(cx - 30, cy - 20), (cx + 25, cy - 35), (cx + 45, cy + 15), (cx, cy + 40), (cx - 40, cy + 20)], fill=(18, 22, 30))
        for a in range(14):
            ang = a * 0.4488
            r = rnd.randint(90, 170)
            d.line([(cx, cy), (cx + r * np.cos(ang), cy + r * np.sin(ang) * 0.7)], fill=(235, 238, 243), width=2)
        for r in (60, 100):
            d.ellipse((cx - r, cy - r * 0.7, cx + r, cy + r * 0.7), outline=(220, 225, 232), width=2)
    elif damage == "Broken":
        pts = [(cx - 20, 24)]
        for i in range(1, 9):
            pts.append((cx + (25 if i % 2 else -25) + rnd.randint(-8, 8), 24 + i * (H - 48) // 8))
        d.polygon(pts + [(cx + 60, H - 24), (cx + 60, 24)], fill=(18, 22, 30))
        d.line(pts, fill=(235, 238, 243), width=3)
    elif damage == "Torn":
        pts = [(W - 24, cy - 60)]
        for i in range(1, 12):
            pts.append((W - 24 - (150 if i % 2 else 70) - rnd.randint(0, 25), cy - 60 + i * 11))
        pts.append((W - 24, cy + 70))
        d.polygon(pts, fill=(150, 156, 165))
        d.polygon([(x + 12, y) for x, y in pts[:-1]] + [(W - 24, cy + 70)], outline=(20, 20, 24), width=3)
    elif damage == "Dislodged":
        d.rectangle((90, 90, W - 90, H // 2 + 10), fill=(15, 18, 24))
        d.rectangle((104, 116, W - 76, H // 2 + 40), fill=(96, 148, 210), outline=(28, 58, 100), width=4)
    d.text((34, H - 22), f"Illustration: {damage}", fill=(255, 255, 255))
    return img
