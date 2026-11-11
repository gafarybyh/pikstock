import kwgen.pipeline as pipeline
import kwgen.text as text
from kwgen.constants import EXTRACT_PROMPT, SEO_SPECS, SYSTEM_PROMPT


def test_description_validator():
    assert pipeline._desc_issues(" ".join(["floral"] * 60)) == []
    assert pipeline._desc_issues(" ".join(["floral"] * 40)) == ["40 kata (target 55-85)"]
    assert "ada preamble" in pipeline._desc_issues("Here is " + " ".join(["floral"] * 60))
    assert "menyebut format/medium teknis" in pipeline._desc_issues(
        " ".join(["floral"] * 55 + ["vector"])
    )
    assert "bukan teks English" in pipeline._desc_issues("é " * 60)


def test_vision_does_not_replace_with_empty_retry(monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "encode_image_meta",
        lambda path: ("image/jpeg", "abc", {"ext": "jpg", "format": "JPEG"}),
    )
    responses = iter(["short", "  "])
    monkeypatch.setattr(pipeline, "_post", lambda payload: next(responses))
    desc, meta = pipeline._vision("probe.jpg")
    assert desc == "short"
    assert meta["ext"] == "jpg"


def test_clean_desc_and_brand():
    cleaned = text._clean_desc("Vecteezy watermark on a watercolour floral clip art")
    assert "Vecteezy" not in cleaned
    assert "watercolor" in cleaned
    assert "watermark" in cleaned

    tags = text._clean_tags(
        ["vecteezy floral", "watercolour floral", "creative market", "floral clip art"],
        cap=5,
    )
    assert tags == ["watercolor floral", "floral clip art"]
    assert text._clean_title("Watercolour Floral Canva Template") == "Watercolor Floral Template"


def test_canva_format_guard():
    assert pipeline._format_label({"ext": "jpg", "format": "JPEG"}) == "JPG"
    assert pipeline._ensure_format("Dog Family", {"ext": "jpg", "format": "JPEG"}) == "Dog Family - JPG"
    assert pipeline._ensure_format("Dog Family JPG", {"ext": "jpg", "format": "JPEG"}) == "Dog Family JPG"
    assert pipeline._ensure_format("Dog Family JPEG", {"ext": "jpg", "format": "JPEG"}) == "Dog Family JPEG"


def test_facts_per_market():
    meta = {"format": "PNG", "width": 1024, "height": 768,
            "orientation": "landscape", "alpha": True, "ext": "png"}
    canva = pipeline._facts_for("canva", meta)
    assert "format PNG" in canva
    assert "1024x768 pixels" in canva
    assert "landscape orientation" in canva
    assert "contains transparent pixels" in canva

    etsy = pipeline._facts_for("etsy", meta)
    assert "format" not in etsy
    assert "contains transparent pixels" in etsy
    assert pipeline._facts_for("core", meta) == ""


def test_seo_step_injects_facts(monkeypatch):
    captured = []

    def fake_post(payload):
        captured.append(payload["messages"][0]["content"])
        return '{"tags":["floral clip art"]}'

    monkeypatch.setattr(pipeline, "_post", fake_post)
    result = pipeline.seo_step(
        "A floral clip art set.",
        "canva",
        SEO_SPECS(10)["canva"],
        facts="Known file facts: format PNG.",
    )
    assert result == {"tags": ["floral clip art"]}
    assert "Known file facts: format PNG." in captured[0]


def test_specs_and_prompt_do_not_seed_file_formats():
    specs = SEO_SPECS(10)
    assert "vector" not in specs["core"][0].lower()
    assert "flat vector" not in specs["style"][0].lower()
    assert "include the file format only" in specs["canva"][2].lower()
    assert "55-85 words" in SYSTEM_PROMPT
    assert "US spelling" in SYSTEM_PROMPT
    assert "45-70" not in SYSTEM_PROMPT


def test_extract_prompt_free_attributes():
    assert "55-85 words" in EXTRACT_PROMPT
    for key in ('"asset_type"', '"style"', '"mood"', '"tone"', '"colors"',
                '"lighting"', '"composition"', '"product_type"'):
        assert key in EXTRACT_PROMPT
    assert "Leave a field empty" in EXTRACT_PROMPT
    assert "exactly one value from" not in EXTRACT_PROMPT
    assert "from: " not in EXTRACT_PROMPT


def test_extract_attrs_normalized(monkeypatch):
    reply = (
        '{"description": "' + " ".join(["floral"] * 60) + '", '
        '"asset_type": "Clip Art", "style": "  Flat   Illustration ", '
        '"mood": ["Calm", "calm", "playful", "dreamy"], '
        '"tone": "PASTEL", "colors": "pink", "lighting": "", '
        '"composition": "Flat Lay", "product_type": "Clip Art"}'
    )
    monkeypatch.setattr(
        pipeline, "encode_image_meta",
        lambda path: ("image/png", "abc", {"ext": "png", "format": "PNG"}),
    )
    monkeypatch.setattr(pipeline, "_post", lambda payload: reply)
    desc, attrs = pipeline.extract_describe("probe.png")
    assert desc.startswith("floral")
    assert attrs == {
        "asset_type": "clip art",
        "style": "flat illustration",
        "mood": ["calm", "playful"],
        "tone": "pastel",
        "colors": ["pink"],
        "lighting": "",
        "composition": "flat lay",
        "product_type": "clip art",
    }
