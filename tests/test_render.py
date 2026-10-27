from wartahayati.config import load
from wartahayati.render import render


def test_render_with_empty_state_writes_all_pages(tmp_path):
    cfg = load()
    render(cfg, {"items": {}, "health": {}, "updated": None}, tmp_path / "out")
    out = tmp_path / "out"
    assert (out / "index.html").exists()
    assert (out / "status" / "index.html").exists()
    assert (out / "data.json").exists()
    for topic in cfg.topics:
        assert (out / "topik" / topic.slug / "index.html").exists()


def test_render_escapes_titles(tmp_path):
    cfg = load()
    first = next(s for s in cfg.sources if s.enabled)
    state = {
        "items": {first.id: [{"title": "<script>x</script>", "link": "https://a.id/x", "published": "2026-10-27T00:00:00+00:00"}]},
        "health": {},
        "updated": "2026-10-27T00:00:00+00:00",
    }
    render(cfg, state, tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    assert "<script>x</script>" not in html
