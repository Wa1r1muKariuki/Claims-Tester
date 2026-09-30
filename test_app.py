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
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception, at.exception
    return at


def seed_photos(at):
    at.session_state["photos"] = {v: scene(i) for i, v in enumerate(["Front", "Rear", "Left", "Right"])}
    at.session_state["seq"] = {v: i + 1 for i, v in enumerate(["Front", "Rear", "Left", "Right"])}


def test_renders_and_gates():
    at = fresh()
    assert at.button(key="to1").disabled          # no photos yet


def test_journey1_full_flow():
    at = fresh(); seed_photos(at); at.run()
    assert not at.button(key="to1").disabled
    at.button(key="to1").click().run()             # -> form
    at.selectbox(key="declared_panel").select("Hood")
    at.selectbox(key="declared_dmg").select("Smashed")
    at.button(key="declared_add").click().run()
    assert at.session_state["declared"] == [("Hood", "Smashed")]
    at.checkbox(key="cb_confirmed").check().run()
    assert not at.button(key="to2").disabled
    at.button(key="to2").click().run()             # -> results
    at.button(key="run").click().run()
    assert not at.exception, at.exception
    html = " ".join(m.value for m in at.markdown)
    assert "Comparison report" in html and ("Needs review" in html or "Matched" in html)


def test_journey2_and_switching_keeps_photos():
    at = fresh(); seed_photos(at); at.run()
    at.session_state["towed_ui"] = "Towed"; at.run()
    assert len(at.session_state["photos"]) == 4
    at.session_state["report"] = {"name": "r.pdf", "error": None, "note": "ok"}
    at.session_state["garage"] = [("Hood", "Dent")]
    at.session_state["step"] = 1; at.run()
    html = " ".join(m.value for m in at.markdown)
    assert "Garage report summary" in html and "Hood" in html      # read-only summary, no manual entry
    assert not at.selectbox and not at.button(key="to2").disabled
    at.session_state["step"] = 2; at.run()
    at.button(key="run").click().run()
    assert not at.exception, at.exception
    assert "Comparison report" in " ".join(m.value for m in at.markdown)


def test_duplicate_photo_blocked():
    at = fresh()
    a = scene(1)
    at.session_state["photos"] = {"Front": a, "Rear": a}
    at.session_state["seq"] = {"Front": 1, "Rear": 2}
    at.run()
    assert "looks the same as your front photo" in " ".join(m.value for m in at.markdown)
    assert at.button(key="to1").disabled


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


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("PASS", n)
