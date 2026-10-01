"""Client for the Car Damage Detection API (/api/v1). All network calls live here.

Configure with env vars / Streamlit secrets:  API_BASE_URL (required), API_KEY (optional bearer token).
"""
import base64
import json
import os

import requests


class ApiError(Exception):
    pass


def base_url():
    u = (os.environ.get("API_BASE_URL") or "").strip().rstrip("/")
    return u[:-7] if u.endswith("/api/v1") else u


def enabled():
    return bool(base_url())


def _req(method, path, timeout=120, **kw):
    headers = {"Authorization": f"Bearer {os.environ['API_KEY']}"} if os.environ.get("API_KEY") else {}
    try:
        r = requests.request(method, f"{base_url()}/api/v1{path}", headers=headers, timeout=timeout, **kw)
    except requests.RequestException as e:
        raise ApiError(f"Cannot reach the backend ({type(e).__name__}).") from e
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail")
        except Exception:
            detail = r.text[:200]
        raise ApiError(f"Backend returned {r.status_code}: {detail}")
    try:
        return r.json()
    except ValueError as e:
        raise ApiError("Backend did not return JSON.") from e


def _file(data, name="photo.jpg"):
    return (name, data, "image/jpeg")


def _b(x):
    return "true" if x else "false"


def b64_bytes(s):
    return base64.b64decode(s) if s else None


# ---- system / taxonomy ----
def health():
    h = _req("GET", "/health", timeout=8)
    return h if isinstance(h, dict) else {"raw": h}


def detectors():
    return _req("GET", "/detectors", timeout=20)


def parts():
    return _req("GET", "/hidden-damage/parts", timeout=20)


# ---- per-photo ----
def quality(data):
    return _req("POST", "/quality/check", timeout=30, files={"file": _file(data)})


def detect(data, models=None, threshold=None, include_image=True):
    """All detectors (or the comma-separated `models`) on one image. threshold=None -> production thresholds."""
    params = {"include_image": _b(include_image)}
    if models:
        params["models"] = models
    if threshold is not None:
        params["threshold"] = threshold
    return _req("POST", "/detectors/detect", params=params, files={"file": _file(data)})


# ---- journey 1 (not towed): one declared damage + its photo, then finalize ----
def minor_check(damage_type, data, threshold=None, include_image=True):
    """damage_type is a detector key (e.g. 'dent'). threshold=None -> each detector's production threshold."""
    form = {"damage_type": damage_type, "include_image": _b(include_image)}
    if threshold is not None:
        form["threshold"] = str(threshold)
    return _req("POST", "/journeys/minor/check", data=form, files={"file": _file(data)})


def minor_item(chk, part_id, damage_type):
    """Build a MinorItem for /minor/finalize from a /minor/check result."""
    sev = chk.get("severity") or {}
    score = sev.get("composite")
    score = min(100.0, max(0.0, float(score))) if score is not None else 0.0
    return {"damage_type": damage_type, "confirmed": bool(chk.get("confirmed")), "max_conf": chk.get("max_conf"),
            "severity": score, "severity_source": "glm" if sev.get("ok") else "default", "part_ids": [part_id]}


def minor_finalize(items):
    return _req("POST", "/journeys/minor/finalize", json={"items": items})


# ---- journey 2 (towed) ----
def major(photos, garage_text, estimate=None, run_glm=True, include_images=True, threshold=None):
    """photos: {'Front': bytes, ...}; estimate: [{'part_id': 12, 'severity': 70}, ...]"""
    files = {v.lower(): _file(d, f"{v.lower()}.jpg") for v, d in photos.items()}
    form = {"garage_text": garage_text or "", "estimate": json.dumps(estimate or []), "run_glm": _b(run_glm),
            "include_images": _b(include_images)}
    if threshold is not None:
        form["threshold"] = str(threshold)
    return _req("POST", "/journeys/major", data=form, files=files, timeout=300)
