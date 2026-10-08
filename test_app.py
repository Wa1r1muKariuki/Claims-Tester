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


def inspect(at, cid="C-001"):
    """A submitted claim is inspected automatically; this just checks that it was."""
    c = next(x for x in at.session_state["claims"] if x["id"] == cid)
    assert c["analysis"] is not None and not c.get("error"), c.get("error")
    return at


# ---------------- fake backend (stdlib only) ----------------
CALLS = []   # paths the app called on the fake backend
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
        CALLS.append(self.path)
        if self.path.startswith("/api/v1/journeys/minor/finalize"):
            names = {p["part_id"]: p["label"] for p in PARTS}
            rows = [{"damage_type": i["damage_type"], "damage": i["damage_type"].title(), "confirmed": i["confirmed"], "max_conf": i["max_conf"],
                     "severity": i["severity"], "fix_type": "repair", "part_ids": i["part_ids"], "part_names": [names[x] for x in i["part_ids"]],
                     "status": "matched" if i["confirmed"] else "needs_review",
                     "reason": "confirmed" if i["confirmed"] else "declared, but not found in the photo"} for i in json.loads(body)["items"]]
            n = sum(r["status"] != "matched" for r in rows)
            self._send({"outcome": "needs_review" if n else "matched", "summary": f"{n} declared damage not found in the photo" if n else "All confirmed",
                        "needs_review_count": n, "hidden_damage_flag": False, "rows": rows,
                        "hidden_damage": {"verdict": "low_risk", "summary": "Low risk of hidden damage (18%).", "hidden_damage_likely": False},
                        "hidden_damage_note": None,
                        "estimate": [{"part_id": r["part_ids"][0], "part_name": r["part_names"][0], "severity": r["severity"], "fix_type": "repair"} for r in rows]})
        elif self.path.startswith("/api/v1/journeys/minor/check"):
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
    CALLS.clear()
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


def test_same_photo_can_be_used_for_several_damages():
    at = fresh()
    for p, d in (("Front bumper", "Scratch"), ("Front bumper", "Dent"), ("Hood", "Dent")):
        at.selectbox(key="cl_part").set_value(p); at.selectbox(key="cl_dmg").set_value(d)
        at.button(key="cl_add").click().run()
    cl = at.session_state["cl"]; same = scene(1)
    for n, it in enumerate(cl["items"]["Not towed"]):
        it["data"] = same; it["pseq"] = n + 1
    at.button(key="cl_to_photos").click().run()
    assert "looks the same" not in text(at) and not at.button(key="cl_submit").disabled
    at.button(key="cl_submit").click().run()
    assert "C-001" in text(at)


def test_reuse_button_copies_a_photo_onto_another_item():
    at = fresh()
    for d in ("Scratch", "Dent"):
        at.selectbox(key="cl_dmg").set_value(d); at.button(key="cl_add").click().run()
    first, second = at.session_state["cl"]["items"]["Not towed"]
    first["data"] = scene(5); first["pseq"] = 1
    at.button(key="cl_to_photos").click().run()
    at.segmented_control(key=f"cl_src_{second['id']}").set_value("Same photo").run()
    at.button(key=f"cl_ruse_{second['id']}").click().run()
    assert not at.exception
    assert at.session_state["cl"]["items"]["Not towed"][1]["data"] == first["data"]
    assert not at.button(key="cl_submit").disabled


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


def test_submitted_claim_is_inspected_automatically(backend):
    at = submit_claim(fresh(), "Not towed", [("Hood (bonnet)", "Dent"), ("Front door", "Scratch")])
    c = at.session_state["claims"][0]
    assert c["analysis"] is not None and c["status"] != "New"            # already inspected, before anyone opens the Insurance tab
    assert [p for p in CALLS if "minor/check" in p] and [p for p in CALLS if "minor/finalize" in p]
    assert "Success: your claim was submitted" in text(at) and "Declared damage vs model" not in text(at)   # the client sees no findings
    at.button(key="vtab_insurance").click().run()
    t = text(at)
    assert "Declared damage vs model" in t and "Ready to inspect" not in t and "Hood (bonnet)" in t and "Front door" in t
    n = len(CALLS)
    at.button(key="vtab_client").click().run(); at.button(key="vtab_insurance").click().run()
    assert len(CALLS) == n                                              # switching tabs never re-runs the model


def test_a_failed_automatic_inspection_is_not_retried_and_can_be_run_by_hand(backend, monkeypatch):
    import api
    monkeypatch.setattr(api, "minor_check", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    at = submit_claim(fresh(), "Not towed", [("Hood (bonnet)", "Dent")])
    at.button(key="vtab_insurance").click().run()
    assert not at.exception
    c = at.session_state["claims"][0]
    assert c["analysis"] is not None and c["status"] == "Needs review" and "boom" in c["analysis"]["rows"][0]["reason"]


def test_not_towed_all_matched_is_approved_automatically(backend):
    at = submit_claim(fresh(), "Not towed", [("Hood (bonnet)", "Dent")])
    at.button(key="vtab_insurance").click().run()
    inspect(at)
    c = at.session_state["claims"][0]
    assert c["status"] == "Approved" and c["decided_by"] == "Automatic"
    assert c["analysis"]["outcome"] == "matched"


def test_inspection_shows_table_hidden_damage_estimate_and_photo_findings(backend):
    at = submit_claim(fresh(), "Not towed", [("Hood (bonnet)", "Dent")])
    at.button(key="vtab_insurance").click().run()
    inspect(at)
    t = text(at)
    for want in ("Declared damage vs model", "Confidence", "Hidden damage assessment", "Low risk", "No hidden damage likely", "Repair estimate", "Photo findings", "Hidden damage likely"):
        assert want in t, want


def test_not_towed_mismatch_waits_for_adjuster_then_can_be_approved_or_rejected(backend):
    at = submit_claim(fresh(), "Not towed", [("Hood (bonnet)", "Dent"), ("Front door", "Scratch")])
    at.button(key="vtab_insurance").click().run()
    assert "Insurance review (1)" in [b.label for b in at.button]
    inspect(at)
    c = at.session_state["claims"][0]
    assert c["status"] == "Needs review" and sorted(r["status"] for r in c["analysis"]["rows"]) == ["matched", "needs_review"]
    at.button(key="ap_C-001").click().run()
    c = at.session_state["claims"][0]
    assert c["status"] == "Approved" and c["decided_by"] == "Adjuster"
    at.button(key="rr_C-001").click().run()          # re-run goes back through the model
    assert at.session_state["claims"][0]["status"] == "Needs review"
    at.button(key="rj_C-001").click().run()
    assert at.session_state["claims"][0]["status"] == "Rejected"


def test_towed_choice_matching_model_is_approved_and_mismatch_is_not(backend):
    at = submit_claim(fresh(), "Towed", [("Hood (bonnet)", "Replace")])
    assert at.session_state["claims"][0]["status"] == "Approved"       # inspected on submit
    at.button(key="cl_new").click().run()
    submit_claim(at, "Towed", [("Hood (bonnet)", "Repair")])
    at.button(key="vtab_insurance").click().run()
    inspect(at, "C-002")
    c = at.session_state["claims"][1]
    assert c["status"] == "Needs review" and "model suggests replace" in c["analysis"]["rows"][0]["reason"]


def test_demo_mode_inspects_both_claim_types_without_a_backend():
    at = submit_claim(fresh(), "Not towed", [("Hood", "Dent"), ("Roof", "Scratch")])
    at.button(key="cl_new").click().run()
    submit_claim(at, "Towed", [("Hood", "Replace"), ("Roof", "Repair")])
    at.button(key="vtab_insurance").click().run()
    inspect(at, "C-001"); inspect(at, "C-002")
    for c in at.session_state["claims"]:
        assert c["status"] in ("Approved", "Needs review") and len(c["analysis"]["rows"]) == 2


def test_hidden_damage_card_is_always_shown_and_demo_mode_simulates_it():
    at = submit_claim(fresh(), "Not towed", [("Hood", "Dent")])
    at.button(key="vtab_insurance").click().run()
    inspect(at)
    t = text(at)
    assert "Hidden damage assessment" in t and "Simulated in demo mode" in t and "Hidden damage likely" in t


def test_towed_claims_get_a_hidden_damage_assessment_in_demo_mode():
    at = submit_claim(fresh(), "Towed", [("Hood", "Replace"), ("Roof", "Repair")])
    c = at.session_state["claims"][0]
    assert c["analysis"]["hidden"] is not None and "hidden_flag" in c["analysis"]
    at.button(key="vtab_insurance").click().run()
    t = text(at)
    assert "Hidden damage assessment" in t and "Simulated in demo mode" in t and "Hidden damage likely" in t


def test_towed_hidden_damage_is_flagged_not_invented_when_the_backend_cannot_assess_it(backend):
    at = submit_claim(fresh(), "Towed", [("Hood (bonnet)", "Replace")])
    c = at.session_state["claims"][0]
    assert c["analysis"]["hidden"] is None and c["analysis"]["hidden_note"]
    at.button(key="vtab_insurance").click().run()
    assert "Not assessed" in text(at) and c["status"] == "Approved"


def hero_markdown(at):
    return [m.value for m in at.markdown if "class='hero sm'" in m.value]


def test_status_tiles_and_heroes_on_both_tabs():
    at = fresh()
    assert "Choose the damage" in text(at)
    # a <style> tag in the same element makes the app collapse it to zero height (this once hid the hero)
    assert len(hero_markdown(at)) == 1 and "<style" not in hero_markdown(at)[0]
    at.button(key="vtab_insurance").click().run()
    t = text(at)
    assert len(hero_markdown(at)) == 1 and "<style" not in hero_markdown(at)[0] and "class='kpi " in t and "Awaiting inspection" in t
    assert "awaiting inspection</span>" not in hero_markdown(at)[0]      # the hero no longer repeats the counts as chips


def test_status_tiles_filter_the_claim_list(backend):
    at = submit_claim(fresh(), "Not towed", [("Hood (bonnet)", "Dent")])                              # all matched -> Approved
    at.button(key="cl_new").click().run()
    submit_claim(at, "Not towed", [("Hood (bonnet)", "Dent"), ("Front door", "Scratch")])             # mismatch -> Needs review
    at.button(key="vtab_insurance").click().run()
    assert len(at.expander) >= 2
    labels = lambda: [x.label for x in at.expander if x.label.startswith("C-")]
    assert len(labels()) == 2
    at.button(key="kpibtn_needsreview").click().run()
    assert not at.exception and labels() == [l for l in labels() if "Needs review" in l] and len(labels()) == 1
    assert "kpi t-warn sel" in text(at)
    at.button(key="kpibtn_rejected").click().run()
    assert labels() == [] and "No claims with this status" in text(at)
    at.button(key="kpibtn_rejected").click().run()                      # clicking the active tile clears the filter
    assert len(labels()) == 2 and "sel'" not in text(at)


# ---------------- damage examples ----------------
def test_every_damage_type_has_two_example_photos():
    for d in L.DAMAGES:
        for v in (0, 1):
            assert L.find_example(d, v), (d, v)


def test_backend_damage_labels_map_to_local_types():
    assert L.local_damage("Smashed glass") == "Smashed" and L.local_damage("Broken lamp") == "Broken" and L.local_damage("Dent") == "Dent"
    assert L.local_damage("") is None and L.local_damage("Hail") is None


def test_damage_guide_is_at_the_top_and_examples_show_only_when_opened():
    at = fresh()
    at.selectbox(key="cl_dmg").set_value("Scratch").run()
    assert not at.exception and len(at.get("image")) == 0           # nothing inline until the guide is opened
    assert at.button(key="cl_guide")
    at.button(key="cl_guide").click().run()
    assert not at.exception


def test_summary_prefix_is_cleaned_and_claims_are_collapsible(backend):
    at = submit_claim(fresh(), "Not towed", [("Front door", "Scratch")])
    at.button(key="vtab_insurance").click().run()
    claim_boxes = [x for x in at.expander if x.label.startswith("C-")]
    assert len(claim_boxes) == 1 and claim_boxes[0].proto.expanded
    inspect(at)
    assert "human adjuster" not in text(at).lower()


def test_minor_item_uses_a_severity_source_the_backend_accepts():
    import api
    assert api.minor_item({"severity": {"ok": False}}, 1, "dent")["severity_source"] == "manual"
    assert api.minor_item({"severity": {"ok": True, "composite": 50}}, 1, "dent")["severity_source"] == "glm"
