import io, json, os, re, random, threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from PIL import Image, ImageDraw
from streamlit.testing.v1 import AppTest

import logic as L


def scene(seed, w=1200, h=800):
    r = random.Random(seed)
    im = Image.new("RGB", (w, h), (120, 130, 140))
    d = ImageDraw.Draw(im)
    for _ in range(80):
        x, y = r.randint(0, w), r.randint(0, h)
        d.rectangle((x, y, x + r.randint(20, 200), y + r.randint(20, 150)), fill=tuple(r.randint(0, 255) for _ in range(3)))
    b = io.BytesIO(); im.save(b, "JPEG", quality=90); return b.getvalue()


def text(at):
    return " ".join(m.value for m in at.markdown)


@pytest.fixture(autouse=True)
def demo_env():
    """Default: no backend (an empty value also wins over .streamlit/secrets.toml)."""
    os.environ["API_BASE_URL"] = ""
    yield
    os.environ.pop("API_BASE_URL", None)


def fresh(view="Client"):
    at = AppTest.from_file("app.py", default_timeout=30)
    at.session_state["view"] = view
    at.run()
    assert not at.exception, at.exception
    return at


def submit_claim(at, mode, items):
    """Drive the Client tab: add (part, detail) items, give each a distinct photo, submit."""
    if mode == "Towed":
        at.session_state["cl"]["mode"] = "Towed"; at.run()
    for panel, detail in items:
        at.selectbox(key="cl_part").set_value(panel)
        if mode == "Towed":
            at.segmented_control(key="cl_act").set_value(detail)
        else:
            at.selectbox(key="cl_dmg").set_value(detail)
        at.button(key="cl_add").click().run()
    cl = at.session_state["cl"]
    for n, it in enumerate(cl["items"][mode]):
        it["data"] = scene(100 + n); cl["pseq"] += 1; it["pseq"] = cl["pseq"]
    at.button(key="cl_to_photos").click().run()
    assert not at.button(key="cl_submit").disabled
    at.button(key="cl_submit").click().run()
    assert not at.exception
    return at


# ---------------- fake backend (stdlib only) ----------------
PARTS = [{"part_id": 7, "part_name": "hood", "label": "Hood (bonnet)"}, {"part_id": 9, "part_name": "door", "label": "Front door"}]
DETECTORS = [{"key": "dent", "label": "Dent"}, {"key": "scratch", "label": "Scratch"}]


class _H(BaseHTTPRequestHandler):
    def _send(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        self._send({"/api/v1/health": {"status": "ok"}, "/api/v1/hidden-damage/parts": PARTS, "/api/v1/detectors": DETECTORS}.get(self.path, {}))

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path.startswith("/api/v1/journeys/minor/check"):
            t = (re.search(rb'name="damage_type"\r\n\r\n(\w+)', body) or [None, b""])[1].decode()
            ok = t == "dent"   # the fake model "sees" dents only
            self._send({"damage_type": t, "label": t, "confirmed": ok, "available": True, "error": None, "max_conf": 0.9 if ok else 0.2,
                        "thr": 0.5, "other_damage": [], "quality": {}, "severity": {"ok": True, "composite": 40}, "fix_type": "repair", "image_jpeg_b64": None})
        elif self.path.startswith("/api/v1/severity/grade"):
            self._send({"ok": True, "configured": True, "composite": 85, "cutoff": 70, "verdict": "REPLACE"})   # the fake model always says Replace
        else:
            self._send({})

    def log_message(self, *a):
        pass


_PORT = [8740]


@pytest.fixture
def backend():
    _PORT[0] += 1
    srv = HTTPServer(("127.0.0.1", _PORT[0]), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    os.environ["API_BASE_URL"] = f"http://127.0.0.1:{_PORT[0]}"
    yield
    srv.shutdown()


# ---------------- tabs ----------------
def test_opens_on_client_tab_with_hero_and_switches():
    at = fresh()
    assert "Report your" in text(at) and "hero sm" in text(at)
    assert at.button(key="vtabon_client") and at.button(key="vtab_insurance")
    at.button(key="vtab_insurance").click().run()
    assert not at.exception and "No claims yet" in text(at)
    at.button(key="vtab_client").click().run()
    assert "Report your" in text(at)


def test_client_lists_survive_tab_switch_and_mode_switch():
    at = fresh()
    at.selectbox(key="cl_part").set_value("Hood"); at.button(key="cl_add").click().run()
    at.session_state["cl"]["mode"] = "Towed"; at.run()
    at.selectbox(key="cl_part").set_value("Roof"); at.button(key="cl_add").click().run()
    at.button(key="vtab_insurance").click().run(); at.button(key="vtab_client").click().run()
    cl = at.session_state["cl"]
    assert [i["panel"] for i in cl["items"]["Not towed"]] == ["Hood"] and [i["panel"] for i in cl["items"]["Towed"]] == ["Roof"]


# ---------------- client side ----------------
def test_client_cannot_continue_or_submit_without_items_and_photos():
    at = fresh()
    assert at.button(key="cl_to_photos").disabled
    at.button(key="cl_add").click().run()
    at.button(key="cl_to_photos").click().run()
    assert at.button(key="cl_submit").disabled


def test_client_duplicate_photo_is_blocked():
    at = fresh()
    for p in ("Hood", "Roof"):
        at.selectbox(key="cl_part").set_value(p); at.button(key="cl_add").click().run()
    cl = at.session_state["cl"]; same = scene(1)
    for n, it in enumerate(cl["items"]["Not towed"]):
        it["data"] = same; it["pseq"] = n + 1
    at.button(key="cl_to_photos").click().run()
    assert "looks the same" in text(at) and at.button(key="cl_submit").disabled


def test_submit_shows_success_with_reference_and_no_model_output():
    at = submit_claim(fresh(), "Not towed", [("Hood", "Dent")])
    t = text(at)
    assert "Success" in t and "C-001" in t
    assert "Confidence" not in t and "Model" not in t
    at.button(key="cl_new").click().run()
    assert not at.exception and at.session_state["cl"]["items"]["Not towed"] == []


def test_client_lists_use_backend_parts_and_detectors(backend):
    at = fresh()
    assert at.selectbox(key="cl_part").options == ["Hood (bonnet)", "Front door"]
    assert at.selectbox(key="cl_dmg").options == ["Dent", "Scratch"]


# ---------------- insurance side ----------------
def test_empty_inbox():
    assert "No claims yet" in text(fresh("Insurance"))


def test_not_towed_all_matched_is_approved_automatically(backend):
    at = submit_claim(fresh(), "Not towed", [("Hood (bonnet)", "Dent")])
    at.button(key="vtab_insurance").click().run()
    assert not at.exception
    c = at.session_state["claims"][0]
    assert c["status"] == "Approved" and c["decided_by"] == "Automatic"
    assert c["analysis"][0]["status"] == "Matched"


def test_not_towed_mismatch_waits_for_adjuster_then_can_be_approved_or_rejected(backend):
    at = submit_claim(fresh(), "Not towed", [("Hood (bonnet)", "Dent"), ("Front door", "Scratch")])
    at.button(key="vtab_insurance").click().run()
    c = at.session_state["claims"][0]
    assert c["status"] == "Needs review" and [r["status"] for r in c["analysis"]] == ["Matched", "Needs review"]
    assert "Insurance review (1)" in [b.label for b in at.button]
    at.button(key="ap_C-001").click().run()
    c = at.session_state["claims"][0]
    assert c["status"] == "Approved" and c["decided_by"] == "Adjuster"
    at.button(key="rr_C-001").click().run()          # re-run puts it back through the model
    assert at.session_state["claims"][0]["status"] == "Needs review"
    at.button(key="rj_C-001").click().run()
    assert at.session_state["claims"][0]["status"] == "Rejected"


def test_towed_choice_matching_model_is_approved_and_mismatch_is_not(backend):
    at = submit_claim(fresh(), "Towed", [("Hood (bonnet)", "Replace")])
    at.button(key="vtab_insurance").click().run()
    assert at.session_state["claims"][0]["status"] == "Approved"
    at.button(key="vtab_client").click().run(); at.button(key="cl_new").click().run()
    submit_claim(at, "Towed", [("Hood (bonnet)", "Repair")])
    at.button(key="vtab_insurance").click().run()
    c = at.session_state["claims"][1]
    assert c["status"] == "Needs review" and "model suggests replace" in c["analysis"][0]["reason"]


def test_demo_mode_analyses_both_claim_types_without_a_backend():
    at = submit_claim(fresh(), "Not towed", [("Hood", "Dent"), ("Roof", "Scratch")])
    at.button(key="cl_new").click().run()
    submit_claim(at, "Towed", [("Hood", "Replace"), ("Roof", "Repair")])
    at.button(key="vtab_insurance").click().run()
    assert not at.exception
    for c in at.session_state["claims"]:
        assert c["status"] in ("Approved", "Needs review") and len(c["analysis"]) == 2


def test_backend_down_falls_back_to_demo():
    os.environ["API_BASE_URL"] = "http://127.0.0.1:9"
    at = fresh()
    assert not at.exception
    assert at.selectbox(key="cl_part").options == L.PANELS


# ---------------- logic ----------------
def test_theme_toggle():
    at = fresh()
    assert at.session_state["dark"] is False
    at.button(key="theme_btn").click().run()
    assert at.session_state["dark"] is True and not at.exception


def test_photo_quality_checks():
    assert L.check_single(scene(3))["blocking"] == []
    b = io.BytesIO(); Image.new("RGB", (1200, 800), (10, 10, 10)).save(b, "JPEG")
    assert L.check_single(b.getvalue())["blocking"]
