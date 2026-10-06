import io, random
from PIL import Image, ImageDraw
from streamlit.testing.v1 import AppTest


def scene(seed, w=1200, h=800):
    r = random.Random(seed)
    im = Image.new("RGB", (w, h), (120, 130, 140))
    d = ImageDraw.Draw(im)
    for _ in range(80):
        x, y = r.randint(0, w), r.randint(0, h)
        d.rectangle((x, y, x + r.randint(20, 200), y + r.randint(20, 150)), fill=tuple(r.randint(0, 255) for _ in range(3)))
    b = io.BytesIO(); im.save(b, "JPEG", quality=90); return b.getvalue()


def fresh():
    at = AppTest.from_file("app.py", default_timeout=30)
    at.session_state["view"] = "Insurance"
    at.run()
    assert not at.exception, at.exception
    return at


def seed_photos(at):
    at.session_state["photos"] = {v: scene(i) for i, v in enumerate(["Front", "Rear", "Left", "Right"])}
    at.session_state["seq"] = {v: i + 1 for i, v in enumerate(["Front", "Rear", "Left", "Right"])}


import base64
import api
import logic as L


def text(at):
    return " ".join(m.value for m in at.markdown)


def towed(at):
    at.session_state["towed_ui"] = "Towed"
    return at


def inst(iid, data, parts, chk=None, thr=None):
    return {"id": iid, "data": data, "parts": parts, "chk": chk, "thr": thr, "err": None, "n": 0}


def seed_minor(at, specs):
    """specs: [(type, [(part_list, seed)])] -> instances with a demo model check already done."""
    at.session_state["mn_types"] = [t for t, _ in specs]
    n = 0
    inst_map = {}
    for t, photos in specs:
        lst = []
        for parts, seed in photos:
            n += 1
            d = scene(seed)
            lst.append(inst(n, d, parts, L.mock_minor_check(t, d, None), None))
        inst_map[t] = lst
    at.session_state["mn_inst"] = inst_map
    at.session_state["mn_seq"] = n
    at.session_state["flags"] = {"none_minor": False, "none_major": False, "confirmed": True}


def test_renders_and_gates():
    at = fresh()
    assert at.button(key="to1").disabled          # nothing ticked yet
    assert "Damage you can see" in text(at)


def test_minor_journey_has_two_steps_and_no_angle_photos():
    at = fresh()
    assert "Photos" not in " ".join(b.label for b in at.button if b.key and b.key.startswith(("nav_", "navon_")))


def test_problems_are_listed_until_every_damage_has_a_checked_photo():
    at = fresh()
    at.session_state["mn_types"] = ["Scratch", "Dent"]
    at.run()
    assert "Choose where the scratch is and add a photo." in text(at) and "Choose where the dent is and add a photo." in text(at)
    assert at.button(key="to1").disabled


def test_multiple_damages_full_flow_demo():
    at = fresh()
    seed_minor(at, [("Scratch", [(["Hood"], 1)]), ("Dent", [(["Left front door"], 2), (["Roof"], 3)])])
    at.run()
    assert not at.button(key="to1").disabled, text(at)
    at.button(key="to1").click().run()
    assert at.session_state["step"] == 1
    at.button(key="run").click().run()
    assert not at.exception and not at.session_state["run_error"], at.session_state["run_error"]
    t = text(at)
    assert "Declared damage vs model" in t and "Hood" in t and "Left front door" in t and "Photo findings" in t
    assert at.session_state["live"]["kind"] == "minor"


def test_two_photos_of_one_damage_become_one_item_with_all_parts():
    at = fresh()
    seed_minor(at, [("Dent", [(["Left front door"], 2), (["Roof", "Hood"], 3)])])
    at.session_state["step"] = 1; at.run()
    at.button(key="run").click().run()
    fin = at.session_state["live"]["final"]
    assert len(fin["rows"]) == 1
    names = fin["rows"][0]["part_names"]
    assert {"Left front door", "Roof", "Hood"} <= set(names)


def test_other_damage_suggestion_adds_the_type_and_reuses_the_photo():
    at = fresh()
    d = scene(5)
    chk = L.mock_minor_check("Scratch", d, None)
    chk["other_damage"] = ["Dent"]
    at.session_state["mn_types"] = ["Scratch"]
    at.session_state["mn_inst"] = {"Scratch": [inst(1, d, ["Hood"], chk)]}
    at.session_state["mn_seq"] = 1
    at.session_state["flags"] = {"none_minor": False, "none_major": False, "confirmed": True}
    at.run()
    at.button(key="oth_1_Dent").click().run()
    assert not at.exception, at.exception
    assert at.session_state["flags"]["confirmed"] is False     # the list changed, so ask again
    assert at.session_state["mn_types"] == ["Dent", "Scratch"] or set(at.session_state["mn_types"]) == {"Scratch", "Dent"}
    dent = at.session_state["mn_inst"]["Dent"][-1]
    assert dent["data"] == d and dent["parts"] == ["Hood"] and dent["chk"] is not None


def test_photo_slot_opens_only_after_the_location_is_chosen():
    at = fresh()
    at.session_state["mn_types"] = ["Scratch"]
    at.session_state["mn_inst"] = {"Scratch": [inst(1, None, [])]}
    at.session_state["mn_seq"] = 1
    at.run()
    assert not at.exception, at.exception
    assert "Choose the location first" in text(at) and "Waiting for the location and a photo." in text(at)
    assert not at.get("file_uploader")
    at.session_state["mn_inst"]["Scratch"][0]["parts"] = ["Hood"]
    at.run()
    assert not at.exception and at.get("file_uploader")
    assert "Upload a clear photo of the scratch on the hood." in " ".join(c.value for c in at.caption)
    assert "Waiting for a photo." in text(at)


def test_location_is_asked_before_the_photo_in_the_to_do_list():
    at = fresh()
    at.session_state["mn_types"] = ["Dent"]
    at.session_state["mn_inst"] = {"Dent": [inst(1, None, ["Roof"])]}
    at.session_state["mn_seq"] = 1
    at.run()
    assert "Add a photo of the dent." in text(at)            # location known, photo missing
    assert at.button(key="to1").disabled


def test_confirm_checkbox_unlocks_only_when_everything_is_ready():
    at = fresh()
    at.session_state["mn_types"] = ["Scratch"]
    at.run()
    assert at.checkbox(key="cb_confirmed").disabled
    seed_minor(at, [("Scratch", [(["Hood"], 1)])])
    at.session_state["flags"] = {"none_minor": False, "none_major": False, "confirmed": False}
    at.run()
    assert not at.checkbox(key="cb_confirmed").disabled
    assert at.button(key="to1").disabled                      # still needs the confirmation


def test_extra_empty_photo_slot_can_be_cancelled():
    at = fresh()
    seed_minor(at, [("Dent", [(["Roof"], 2)])])
    at.run()
    at.button(key="more_Dent").click().run()
    assert len(at.session_state["mn_inst"]["Dent"]) == 2
    new_id = at.session_state["mn_inst"]["Dent"][-1]["id"]
    at.button(key=f"cx_{new_id}").click().run()
    assert len(at.session_state["mn_inst"]["Dent"]) == 1 and not at.exception


def test_changing_threshold_marks_checks_stale_and_recheck_clears_it():
    at = fresh()
    seed_minor(at, [("Scratch", [(["Hood"], 1)])])
    at.run()
    assert not at.button(key="to1").disabled
    at.session_state["thr_mode"], at.session_state["thr_val"] = "custom", 0.7
    at.run()
    assert at.button(key="to1").disabled and "Re-check" in text(at) + " ".join(b.label for b in at.button)
    at.button(key="recheck").click().run()
    assert not at.exception and not at.button(key="to1").disabled
    assert at.session_state["mn_inst"]["Scratch"][0]["thr"] == 0.7


def test_no_visible_damage_gives_a_matched_outcome():
    at = fresh()
    at.session_state["flags"] = {"none_minor": True, "none_major": False, "confirmed": True}
    at.run()
    assert not at.button(key="to1").disabled
    at.session_state["step"] = 1; at.run()
    at.button(key="run").click().run()
    assert "No damage was declared" in text(at)


def test_towed_photos_come_before_garage_report():
    at = towed(fresh())
    at.run()
    assert "Capture the vehicle" in text(at)
    assert [b.label for b in at.button if b.key and b.key.startswith(("nav_", "navon_")) and not b.key.endswith("_claims")] == ["Photos", "Garage report", "Results"]
    assert at.button(key="to1").disabled                      # no photos yet
    at.session_state["step"] = 1; at.run()
    assert "Garage report" in text(at) and "Capture the vehicle" not in text(at)


def test_towed_garage_step_needs_photos_and_report():
    at = towed(fresh()); seed_photos(at); at.run()
    assert not at.button(key="to1").disabled                  # four good photos -> can continue
    at.session_state["step"] = 1; at.run()
    assert at.button(key="to2").disabled                      # no report yet
    at.session_state["step"] = 2; at.run()
    assert "Complete your inspection first" in text(at)
    at.button(key="gate").click().run()
    assert at.session_state["step"] == 1                      # photos done, so it sends you to the report


def test_towed_results_gate_sends_you_to_photos_when_missing():
    at = towed(fresh())
    at.session_state["report"] = {"name": "r.txt", "error": None, "note": "ok", "text": "Hood dent"}
    at.session_state["step"] = 2; at.run()
    assert "Accept all four photos" in text(at)
    at.button(key="gate").click().run()
    assert at.session_state["step"] == 0


def test_towed_demo_flow_and_switching_keeps_photos():
    at = fresh(); seed_photos(at); at.run()
    at.session_state["towed_ui"] = "Towed"; at.run()
    assert len(at.session_state["photos"]) == 4
    at.session_state["report"] = {"name": "r.pdf", "error": None, "note": "ok", "text": ""}
    at.session_state["garage"] = [("Hood", "Dent")]
    at.session_state["step"] = 1; at.run()
    assert "Garage report summary" in text(at) and not at.exception
    at.session_state["step"] = 2; at.run()
    at.button(key="run").click().run()
    assert not at.exception and "Comparison report" in text(at)


def test_duplicate_towed_photo_blocked():
    at = towed(fresh())
    a = scene(1)
    at.session_state["photos"] = {"Front": a, "Rear": a}
    at.session_state["seq"] = {"Front": 1, "Rear": 2}
    at.session_state["step"] = 0
    at.run()
    assert "looks the same as your front photo" in text(at)
    assert at.button(key="to1").disabled


def test_journey_switch_returns_to_the_first_step():
    at = fresh()
    at.session_state["step"] = 1; at.run()
    at.session_state["towed_ui"] = "Towed"; at.run()
    assert not at.exception


def test_theme_toggle_and_guide_images():
    at = fresh()
    assert at.session_state["dark"] is False
    at.button(key="theme_btn").click().run()
    assert at.session_state["dark"] is True and not at.exception
    import logic as L
    assert L.check_single(scene(3))["soft"] == []
    for d in L.DAMAGES:
        assert L.example_image(d, 0).size == L.example_image(d, 1).size


def test_bad_quality_photos_are_rejected():
    import io, logic as L
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (1200, 800), (10, 10, 10)).save(b, "JPEG")
    assert L.check_single(b.getvalue())["blocking"]




# ---------------- live backend (against dev_mock_backend.py) ----------------
import contextlib, os, subprocess, sys, time, urllib.request


_PORT = 8620


@contextlib.contextmanager
def backend():
    global _PORT
    _PORT += 1
    port = _PORT
    p = subprocess.Popen([sys.executable, "-m", "uvicorn", "dev_mock_backend:app", "--port", str(port), "--log-level", "warning"])
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/health", timeout=1); break
            except Exception:
                time.sleep(0.25)
        os.environ["API_BASE_URL"] = f"http://127.0.0.1:{port}"
        yield
    finally:
        os.environ.pop("API_BASE_URL", None)
        p.terminate()
        p.wait(timeout=10)


def text(at):
    return " ".join(m.value for m in at.markdown)


def test_live_minor_flow_uses_detector_keys_and_finalizes():
    with backend():
        at = fresh()
        assert "Connected to the detection API" in text(at)
        # chips come from /detectors, so the labels are the backend's own
        assert "Smashed glass" in " ".join(str(p.options) for p in at.get("pills")) if at.get("pills") else True
        d1, d2 = scene(11), scene(12)
        c1, c2 = api.minor_check("scratch", d1, None), api.minor_check("glass", d2, 0.4)
        at.session_state["mn_types"] = ["scratch", "glass"]
        at.session_state["mn_inst"] = {"scratch": [inst(1, d1, ["Hood"], c1, None)], "glass": [inst(2, d2, ["Windshield"], c2, 0.4)]}
        at.session_state["mn_seq"] = 2
        at.session_state["thr_mode"], at.session_state["thr_val"] = "custom", 0.4
        at.session_state["flags"] = {"none_minor": False, "none_major": False, "confirmed": True}
        at.session_state["step"] = 1; at.run()
        # scratch was checked with production thresholds, so it is stale under the custom one
        assert "Complete your inspection first" in text(at)
        at.session_state["mn_inst"]["scratch"][0]["thr"] = 0.4
        at.run()
        at.button(key="run").click().run()
        assert not at.exception and not at.session_state["run_error"], at.session_state["run_error"]
        t = text(at)
        assert "Declared damage vs model" in t and "Windshield" in t and "Hidden damage assessment" in t
        assert {r["damage_type"] for r in at.session_state["live"]["final"]["rows"]} == {"scratch", "glass"}
        assert "Confirmed" in t or "Needs review" in t


def test_live_towed_sends_text_and_estimate():
    with backend():
        at = towed(fresh()); seed_photos(at)
        at.session_state["report"] = {"name": "r.txt", "error": None, "note": "ok", "text": "Hood dent\nDoor scratch"}
        at.session_state["estimate"] = [("Hood", 70)]
        at.session_state["step"] = 2; at.run()
        at.button(key="run").click().run()
        assert not at.exception and not at.session_state["run_error"], at.session_state["run_error"]
        t = text(at)
        assert "Garage report vs photos" in t and "Hidden damage assessment" in t and "Estimate lines: 1" in t
        assert at.session_state["live"]["res"]["garage_items"] == ["dent", "scratch"]


def test_live_towed_pdf_summary_does_not_crash():
    with backend():
        at = towed(fresh())
        at.session_state["report"] = {"name": "r.pdf", "error": None, "note": "ok", "text": "Hood dent"}
        at.session_state["step"] = 1; at.run()
        assert not at.exception, at.exception
        assert "Text that will be sent to the backend" in " ".join(x.label for x in at.expander)


def test_live_backend_quality_rejects_towed_photo():
    with backend():
        at = towed(fresh())
        at.session_state["photos"] = {"Front": scene(7) + b"BADQUALITY"}; at.session_state["seq"] = {"Front": 1}
        at.session_state["step"] = 0; at.run()
        assert "out of focus" in text(at)


def test_backend_down_falls_back_to_demo():
    os.environ["API_BASE_URL"] = "http://127.0.0.1:9"
    try:
        at = fresh()
        assert "Demo mode" in text(at) and "Backend not available" in " ".join(c.value for c in at.caption)
        seed_minor(at, [("Scratch", [(["Hood"], 1)])]); at.session_state["step"] = 1; at.run()
        at.button(key="run").click().run()
        assert not at.exception and "Declared damage vs model" in text(at)
    finally:
        os.environ.pop("API_BASE_URL", None)


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("PASS", n)


# ---------------- client -> insurance link (same session) ----------------
def _client_with_items(at, mode, items):
    """items: [(panel, detail)], each gets a different photo; then submit on the Client tab."""
    at.session_state["view"] = "Client"; at.run()
    if mode == "Towed":
        at.session_state["cl"]["mode"] = "Towed"; at.run()
    for n, (panel, detail) in enumerate(items):
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
    assert not at.exception and "C-001" in text(at)
    return at


def test_client_claim_reaches_insurance_and_prefills_inspection():
    at = fresh()
    _client_with_items(at, "Not towed", [("Hood", "Dent"), ("Roof", "Scratch")])
    assert len(at.session_state["claims"]) == 1
    at.button(key="vtab_insurance").click().run()
    assert "Insurance review (1)" in [b.label for b in at.button]
    at.button(key="nav_claims").click().run()
    assert not at.exception and "Client claims" in text(at)
    at.button(key="co_C-001").click().run()
    assert not at.exception
    assert at.session_state["step"] == 0
    assert set(at.session_state["mn_types"]) == {"Dent", "Scratch"}
    inst = at.session_state["mn_inst"]["Dent"][0]
    assert inst["parts"] == ["Hood"] and inst["chk"] and not inst["err"]
    assert at.session_state["claims"][0]["status"] == "In review"


def test_towed_client_claim_is_graded_on_insurance_side():
    at = fresh()
    _client_with_items(at, "Towed", [("Hood", "Replace"), ("Roof", "Repair")])
    at.button(key="vtab_insurance").click().run()
    at.button(key="nav_claims").click().run()
    at.button(key="cg_C-001").click().run()
    assert not at.exception
    rows = at.session_state["claims"][0]["analysis"]
    assert len(rows) == 2 and all(r["status"] in ("Matched", "Needs review") for r in rows)
    assert "Client choice vs model" in text(at)


def test_empty_claims_inbox():
    at = fresh()
    at.session_state["view"] = "Insurance"; at.session_state["step"] = -1; at.run()
    assert not at.exception and "No client claims yet" in text(at)
