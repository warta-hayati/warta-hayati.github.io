"""Ambil daftar berita dari halaman HTML biasa yang tidak menyediakan RSS.

Aturan per sumber ditulis di config/sources.yaml pada kunci ``list`` dengan
pemilih CSS sederhana: tag, ``.kelas``, ``#id``, dan ``:has(...)``, dipisah
spasi untuk hubungan keturunan. Hanya memakai html.parser dari pustaka standar,
tanpa dependensi tambahan.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Iterator
from urllib.parse import urljoin

import requests

TIMEOUT = (10, 25)
VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}
SKIP = {"script", "style", "noscript", "template", "svg", "iframe"}

# Nama bulan Indonesia dan Inggris, singkat maupun penuh.
BULAN = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12,
    "january": 1, "february": 2, "march": 3, "may": 5, "june": 6, "july": 7,
    "august": 8, "october": 10, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "agu": 8,
    "ags": 8, "agt": 8, "sep": 9, "okt": 10, "nov": 11, "des": 12, "aug": 8,
    "oct": 10, "dec": 12,
}

_NAMA_BULAN = "|".join(sorted(BULAN, key=len, reverse=True))
_HARI = (
    r"senin|selasa|rabu|kamis|jumat|jum'at|sabtu|minggu|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday"
)
TANGGAL = re.compile(
    r"(?:(?:" + _HARI + r")[a-z]*\.?,?\s*)?(?:"
    r"(?P<y1>\d{4})-(?P<m1>\d{1,2})-(?P<d1>\d{1,2})"
    r"|(?P<d2>\d{1,2})[/-](?P<m2>\d{1,2})[/-](?P<y2>\d{4})"
    r"|(?P<d3>\d{1,2})\s+(?P<m3>" + _NAMA_BULAN + r")\.?\s+(?P<y3>\d{4})"
    r")",
    re.IGNORECASE,
)


def cari_tanggal(teks: str) -> tuple[datetime | None, int, int]:
    """Cari tanggal pertama dalam teks; kembalikan (waktu, awal, akhir)."""
    m = TANGGAL.search(teks or "")
    if not m:
        return None, 0, 0
    if m["y1"]:
        tahun, bulan, hari = int(m["y1"]), int(m["m1"]), int(m["d1"])
    elif m["d2"]:
        tahun, bulan, hari = int(m["y2"]), int(m["m2"]), int(m["d2"])
    else:
        tahun, bulan, hari = int(m["y3"]), BULAN[m["m3"].lower()], int(m["d3"])
    try:
        waktu = datetime(tahun, bulan, hari, tzinfo=timezone.utc)
    except ValueError:
        return None, 0, 0
    return waktu, m.start(), m.end()


class Node:
    """Simpul ringkas: tag, atribut, dan anak (teks atau simpul)."""

    __slots__ = ("tag", "attrs", "children")

    def __init__(self, tag: str | None, attrs: dict[str, str] | None = None) -> None:
        self.tag = tag
        self.attrs = attrs or {}
        self.children: list[Node | str] = []

    def text(self) -> str:
        bagian = [a if isinstance(a, str) else a.text() for a in self.children]
        return re.sub(r"\s+", " ", " ".join(b for b in bagian if b.strip())).strip()


class _Pohon(HTMLParser):
    """Bangun pohon sederhana; skrip, gaya, dan gambar tidak ikut tersimpan."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.akar = Node("#document")
        self._tumpuk = [self.akar]
        self._bisu: list[str] = []

    @staticmethod
    def _atribut(attrs) -> dict[str, str]:
        """Gabungkan atribut kembar (sebagian situs menulis class dua kali)."""
        peta: dict[str, str] = {}
        for kunci, nilai in attrs:
            nilai = (nilai or "").strip()
            peta[kunci] = f"{peta[kunci]} {nilai}".strip() if kunci in peta else nilai
        return peta

    def handle_starttag(self, tag, attrs):
        if self._bisu or tag in SKIP:
            if tag not in VOID:
                self._bisu.append(tag)
            return
        simpul = Node(tag, self._atribut(attrs))
        self._tumpuk[-1].children.append(simpul)
        if tag not in VOID:
            self._tumpuk.append(simpul)

    def handle_startendtag(self, tag, attrs):
        if self._bisu:
            return
        self._tumpuk[-1].children.append(Node(tag, self._atribut(attrs)))

    def handle_endtag(self, tag):
        if self._bisu:
            if self._bisu[-1] == tag:
                self._bisu.pop()
            return
        if tag in VOID:
            return
        for i in range(len(self._tumpuk) - 1, 0, -1):
            if self._tumpuk[i].tag == tag:
                del self._tumpuk[i:]
                break

    def handle_data(self, data):
        if self._bisu or not data.strip():
            return
        self._tumpuk[-1].children.append(data)


def parse(html: str) -> Node:
    """Ubah HTML menjadi pohon simpul."""
    pohon = _Pohon()
    pohon.feed(html)
    pohon.close()
    return pohon.akar


_BAGIAN = re.compile(
    r"^(?P<tag>[a-zA-Z][\w-]*)?(?P<kelas>(?:\.[\w-]+)*)(?P<id>#[\w-]+)?(?P<has>:has\([^)]*\))?$"
)


def _urai(bagian: str) -> tuple[str, set[str], str, str]:
    m = _BAGIAN.match(bagian.strip())
    if not m or not bagian.strip():
        raise ValueError(f"pemilih tidak dikenal: '{bagian}'")
    dalam = m["has"]
    return (
        (m["tag"] or "").lower(),
        {k for k in m["kelas"].split(".") if k},
        (m["id"] or "")[1:],
        dalam[5:-1].strip() if dalam else "",
    )


def _cocok(simpul: Node, bagian: tuple[str, set[str], str, str]) -> bool:
    tag, kelas, id_, dalam = bagian
    if not simpul.tag:
        return False
    if tag and simpul.tag != tag:
        return False
    if id_ and simpul.attrs.get("id") != id_:
        return False
    if kelas and not kelas <= set(simpul.attrs.get("class", "").split()):
        return False
    return not (dalam and not select(simpul, dalam))


def _keturunan(simpul: Node) -> Iterator[Node]:
    for anak in simpul.children:
        if isinstance(anak, Node):
            yield anak
            yield from _keturunan(anak)


def _rantai(akar: Node, pemilih: str, urutan: list[Node], terlihat: set[int]) -> None:
    """Telusuri satu rantai keturunan; hanya langkah terakhir yang jadi hasil."""
    hasil = [akar]
    for b in (_urai(x) for x in pemilih.split()):
        berikut: list[Node] = []
        lokal: set[int] = set()
        for dasar in hasil:
            for simpul in _keturunan(dasar):
                if id(simpul) not in lokal and _cocok(simpul, b):
                    lokal.add(id(simpul))
                    berikut.append(simpul)
        hasil = berikut
        if not hasil:
            break
    for simpul in hasil:
        if id(simpul) not in terlihat:
            terlihat.add(id(simpul))
            urutan.append(simpul)


def select(akar: Node, pemilih: str) -> list[Node]:
    """Pemilih CSS sederhana: 'div.kelas h3 a', '#id', 'a:has(h4)', gabungan koma."""
    urutan: list[Node] = []
    terlihat: set[int] = set()
    for bagian in pemilih.split(","):
        if bagian.strip():
            _rantai(akar, bagian.strip(), urutan, terlihat)
    return urutan


def _pertama(wadah: Node, pemilih: str) -> Node | None:
    hasil = select(wadah, pemilih)
    return hasil[0] if hasil else None


def _tautan(wadah: Node, pemilih: str) -> str | None:
    if pemilih:
        simpul = _pertama(wadah, pemilih)
        return simpul.attrs.get("href") if simpul else None
    if wadah.tag == "a" and wadah.attrs.get("href"):
        return wadah.attrs["href"]
    simpul = _pertama(wadah, "a")
    return simpul.attrs.get("href") if simpul else None


def butir(pohon: Node, aturan: dict, halaman: str) -> list[dict]:
    """Ubah halaman menjadi entri bergaya feedparser sesuai aturan sumber.

    Aturan yang dikenal: ``item`` (wadah tiap berita), ``title`` (elemen judul),
    ``link`` (elemen tautan), ``date`` (elemen tanggal), ``summary`` (ringkasan),
    dan ``date_in_title`` (tanggal dibaca dari judul lalu dibuang dari judul).
    """
    if aturan.get("item"):
        pasangan = [(w, _pertama(w, aturan.get("title", "a"))) for w in select(pohon, aturan["item"])]
    else:
        pasangan = [(w, w) for w in select(pohon, aturan.get("title", "a"))]

    hasil: list[dict] = []
    for wadah, judul_el in pasangan:
        if judul_el is None:
            continue
        judul = judul_el.text()
        tanggal = None
        if aturan.get("date"):
            simpul = _pertama(wadah, aturan["date"])
            if simpul is not None:
                tanggal, _, _ = cari_tanggal(simpul.text())
        if aturan.get("date_in_title"):
            dari_judul, awal, akhir = cari_tanggal(judul)
            if dari_judul is not None:
                judul = (judul[:awal] + judul[akhir:]).strip(" -–—,|·")
                tanggal = tanggal or dari_judul
        tautan = _tautan(wadah, aturan.get("link", ""))
        if not judul.strip() or not tautan:
            continue
        ringkasan = ""
        if aturan.get("summary"):
            simpul = _pertama(wadah, aturan["summary"])
            if simpul is not None:
                ringkasan = simpul.text()
        entri = {"title": judul, "link": urljoin(halaman, tautan), "summary": ringkasan}
        if tanggal is not None:
            entri["published_parsed"] = tanggal.timetuple()
        hasil.append(entri)
    return hasil


def load_list(session: requests.Session, sumber) -> tuple[str, list]:
    """Ambil halaman daftar berita sumber dan kembalikan entri bergaya feedparser."""
    resp = session.get(sumber.url, timeout=TIMEOUT)
    resp.raise_for_status()
    entri = butir(parse(resp.text), dict(sumber.list_rules), sumber.url)
    if not entri:
        raise ValueError("halaman tanpa butir berita")
    return sumber.url, entri
