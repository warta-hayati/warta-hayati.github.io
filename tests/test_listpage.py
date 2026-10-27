from pathlib import Path

import pytest

from wartahayati.config import load
from wartahayati.listpage import butir, cari_tanggal, parse, select

DATA = Path(__file__).parent / "data"

HTML = """
<div class="daftar" class="kelas-kedua">
  <a href="/berita/satu"><time>21-09-2026</time><h4>Ratas di Istana</h4></a>
  <a href="/berita/dua"><time>2 Oktober 2026</time><h4>Panen raya</h4></a>
  <a href="/lainnya"><span>Tanpa judul</span></a>
</div>
"""


def test_cari_tanggal_handles_indonesian_and_numeric_formats():
    assert cari_tanggal("21-09-2026")[0].date().isoformat() == "2026-09-21"
    assert cari_tanggal("23/10/2026")[0].date().isoformat() == "2026-10-23"
    assert cari_tanggal("Minggu, 25 Oktober 2026")[0].date().isoformat() == "2026-10-25"
    assert cari_tanggal("Selasa, 27 Okt 2026")[0].date().isoformat() == "2026-10-27"
    assert cari_tanggal("17 August 2026")[0].date().isoformat() == "2026-08-17"
    assert cari_tanggal("terbit 2026-10-27 09:00")[0].date().isoformat() == "2026-10-27"
    assert cari_tanggal("31 Februari 2026") == (None, 0, 0)
    assert cari_tanggal("tanpa tanggal") == (None, 0, 0)


def test_parse_merges_duplicate_attributes():
    pohon = parse(HTML)
    assert len(select(pohon, "div.daftar")) == 1
    assert len(select(pohon, "div.kelas-kedua")) == 1


def test_select_supports_has_and_comma():
    pohon = parse(HTML)
    assert len(select(pohon, "a:has(h4)")) == 2
    assert len(select(pohon, "div.daftar a time, div.daftar a h4")) == 4
    assert select(pohon, "div.tidak-ada") == []


def test_parse_ignores_script_contents():
    assert select(parse("<div><script>var a = \"<a href='/x'>Palsu</a>\";</script><a href='/y'>Asli</a></div>"), "a") != []
    assert len(select(parse("<script>var a = \"<a href='/x'>Palsu</a>\";</script>"), "a")) == 0


def test_butir_reads_title_link_and_date():
    hasil = butir(parse(HTML), {"item": "a:has(h4)", "title": "h4", "date": "time"}, "https://contoh.id/")
    assert [b["title"] for b in hasil] == ["Ratas di Istana", "Panen raya"]
    assert hasil[0]["link"] == "https://contoh.id/berita/satu"
    assert hasil[1]["published_parsed"][:3] == (2026, 10, 2)


def test_butir_can_take_date_from_title():
    hasil = butir(parse(HTML), {"title": "a:has(time)", "date_in_title": True}, "https://contoh.id/")
    assert [b["title"] for b in hasil] == ["Ratas di Istana", "Panen raya"]
    assert hasil[0]["published_parsed"][:3] == (2026, 9, 21)


def test_butir_returns_empty_when_rules_do_not_match():
    assert butir(parse("<p>tidak ada berita</p>"), {"item": "div.berita", "title": "h3"}, "https://x.id/") == []


def test_butir_needs_title_and_link():
    assert butir(parse("<div class='berita'><h3>Judul</h3></div>"), {"item": "div.berita", "title": "h3"}, "https://x.id/") == []


def test_select_rejects_unknown_selector():
    with pytest.raises(ValueError):
        select(parse("<p>x</p>"), ":bukan-pemilih")


def _sumber_dari_fixture(sid: str):
    """Ambil aturan asli dari config lalu uji terhadap halaman tersimpan."""
    sumber = next(s for s in load().sources if s.id == sid)
    html = (DATA / f"{sid}.html").read_text(encoding="utf-8", errors="replace")
    return sumber, butir(parse(html), dict(sumber.list_rules), sumber.url)


def test_fao_asia_pasifik_fixture_yields_news():
    sumber, hasil = _sumber_dari_fixture("fao-asia-pasifik")
    assert sumber.list_rules, "aturan 'list' hilang dari config"
    assert len(hasil) >= 15
    asia = [b for b in hasil if b["link"].startswith("https://www.fao.org/asiapacific/news/news-detail/")]
    assert len(asia) >= 15
    assert all(b["link"].startswith("https://www.fao.org/") for b in hasil)
    assert all(b["published_parsed"] for b in hasil)
    assert all(len(b["title"]) > 20 for b in hasil)


def test_kemenhut_fixture_yields_news():
    sumber, hasil = _sumber_dari_fixture("kemenhut")
    assert sumber.enabled, "Kementerian Kehutanan seharusnya sudah aktif"
    assert len(hasil) >= 8
    assert all(b["link"].startswith("https://www.kehutanan.go.id/news/") for b in hasil)
    assert all(b["published_parsed"] for b in hasil)
