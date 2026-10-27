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


def test_render_publishes_icons_and_og_image(tmp_path):
    cfg = load()
    render(cfg, {"items": {}, "health": {}, "updated": None}, tmp_path / "out")
    out = tmp_path / "out"
    for name in ("favicon.ico", "favicon.png", "apple-touch-icon.png", "og-image.jpg"):
        assert (out / "static" / name).exists(), f"berkas ikon hilang: {name}"
    assert (out / "favicon.ico").exists(), "favicon.ico tidak ada di akar situs"
    index = (out / "index.html").read_text(encoding="utf-8")
    assert 'rel="icon"' in index
    assert 'rel="apple-touch-icon"' in index
    assert 'property="og:image"' in index
    assert 'href="static/favicon.ico"' in index
    topik = (out / "topik" / cfg.topics[0].slug / "index.html").read_text(encoding="utf-8")
    assert 'href="../../static/favicon.ico"' in topik


def test_homepage_lists_every_topic_and_drops_empty_boxes(tmp_path):
    cfg = load()
    render(cfg, {"items": {}, "health": {}, "updated": None}, tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    for topic in cfg.topics:
        assert f'href="topik/{topic.slug}/"' in html, f"topik hilang dari beranda: {topic.slug}"
    assert html.count('class="topik"') == len(cfg.topics)
    assert "Belum ada judul yang termuat dari sumber ini" not in html
    assert html.count("Belum ada judul dari sumber topik ini") == len(cfg.topics)


def test_box_without_items_is_hidden(tmp_path):
    cfg = load()
    first = next(s for s in cfg.sources if s.enabled)
    state = {
        "items": {first.id: [{"title": "Judul uji", "link": "https://a.id/x", "published": "2026-10-27T00:00:00+00:00"}]},
        "health": {},
        "updated": None,
    }
    render(cfg, state, tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    assert "Judul uji" in html
    assert html.count('class="box"') == 1


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


def test_every_topic_section_and_tab_carries_its_colour_key(tmp_path):
    cfg = load()
    render(cfg, {"items": {}, "health": {}, "updated": None}, tmp_path / "out")
    out = tmp_path / "out"
    html = (out / "index.html").read_text(encoding="utf-8")
    for topic in cfg.topics:
        assert f'<section class="topik" data-topik="{topic.slug}">' in html, f"seksi tanpa kunci warna: {topic.slug}"
        assert f'<a href="topik/{topic.slug}/" data-topik="{topic.slug}"' in html, f"tab tanpa kunci warna: {topic.slug}"
    # Delapan seksi beranda ditambah delapan tab topik.
    assert html.count("data-topik=") == len(cfg.topics) * 2

    slug = cfg.topics[0].slug
    topik = (out / "topik" / slug / "index.html").read_text(encoding="utf-8")
    assert f'<section class="topik" data-topik="{slug}">' in topik
    # Pita di tepi atas memakai warna topik halaman ini.
    assert f'<div class="pita" data-topik="{slug}"' in topik


def test_stylesheet_defines_palette_for_every_topic(tmp_path):
    cfg = load()
    render(cfg, {"items": {}, "health": {}, "updated": None}, tmp_path / "out")
    css = (tmp_path / "out" / "static" / "style.css").read_text(encoding="utf-8")
    for topic in cfg.topics:
        assert f"[data-topik={topic.slug}]" in css, f"warna topik hilang: {topic.slug}"
    assert "var(--t-bg)" in css
    assert "var(--t-ink)" in css
