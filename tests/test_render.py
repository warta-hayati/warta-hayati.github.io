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
    for name in ("favicon.ico", "favicon.png", "apple-touch-icon.png", "og-image.jpg", "logo-warta-hayati-96.png"):
        assert (out / "static" / name).exists(), f"berkas ikon hilang: {name}"
    assert (out / "favicon.ico").exists(), "favicon.ico tidak ada di akar situs"
    index = (out / "index.html").read_text(encoding="utf-8")
    assert 'rel="icon"' in index
    assert 'rel="apple-touch-icon"' in index
    assert 'property="og:image"' in index
    assert 'href="static/favicon.ico"' in index
    assert '<img class="logo" src="static/logo-warta-hayati-96.png"' in index, "logo tidak dipakai di beranda"
    topik = (out / "topik" / cfg.topics[0].slug / "index.html").read_text(encoding="utf-8")
    assert 'href="../../static/favicon.ico"' in topik
    assert '<img class="logo" src="../../static/logo-warta-hayati-96.png"' in topik, "logo tidak dipakai di halaman topik"


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


def test_status_cells_carry_labels_for_mobile_cards(tmp_path):
    cfg = load()
    render(cfg, {"items": {}, "health": {}, "updated": None}, tmp_path / "out")
    html = (tmp_path / "out" / "status" / "index.html").read_text(encoding="utf-8")
    assert html.count("data-label=") == html.count("<td"), "ada sel tabel tanpa label untuk tampilan kartu"


def test_stylesheet_has_mobile_rules(tmp_path):
    cfg = load()
    render(cfg, {"items": {}, "health": {}, "updated": None}, tmp_path / "out")
    css = (tmp_path / "out" / "static" / "style.css").read_text(encoding="utf-8")
    assert "@media (max-width:640px)" in css
    assert "@media (pointer:coarse)" in css
    assert "min-height:44px" in css
    assert "attr(data-label)" in css
    # Tab topik tidak boleh mengandalkan geser mendatar di layar sempit.
    assert "@media (max-width:900px)" in css
    assert ".topik-nav{position:static;flex-wrap:wrap;overflow:visible" in css
    assert "scroll-snap-type:x proximity" in css, "tab mendatar untuk layar lebar hilang"


def test_about_page_and_contact_reachable(tmp_path):
    cfg = load()
    render(cfg, {"items": {}, "health": {}, "updated": None}, tmp_path / "out")
    out = tmp_path / "out"
    tentang = (out / "tentang" / "index.html").read_text(encoding="utf-8")
    assert "mailto:ekajogja@gmail.com" in tentang
    assert "https://ekajogja.com" in tentang
    assert 'src="../static/logo-warta-hayati.png"' in tentang
    assert 'href="../data.json"' in tentang
    assert 'src="../static/logo-warta-hayati-96.png"' in tentang, "logo kepala halaman hilang"

    halaman = {
        "index.html": "tentang/",
        "status/index.html": "../tentang/",
        f"topik/{cfg.topics[0].slug}/index.html": "../../tentang/",
        "tentang/index.html": "../tentang/",
    }
    for rel, tautan in halaman.items():
        html = (out / rel).read_text(encoding="utf-8")
        assert "mailto:ekajogja@gmail.com" in html, f"surel kontak hilang di {rel}"
        assert "ekajogja.com" in html, f"alamat situs pribadi hilang di {rel}"
        assert f'href="{tautan}"' in html, f"tautan Tentang hilang di {rel}"
