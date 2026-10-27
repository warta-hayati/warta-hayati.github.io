"""Ambil feed RSS/Atom, temukan feed otomatis, dan simpan riwayat per sumber."""
from __future__ import annotations

import concurrent.futures as cf
import json
import logging
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import feedparser
import requests

from .config import Config, Source
from .listpage import load_list
from .normalize import compile_filter, merge, to_item

log = logging.getLogger("wartahayati")

USER_AGENT = "WartaHayatiBot/0.1 (+https://github.com/warta-hayati/warta-hayati.github.io)"
TIMEOUT = (10, 25)
STORE_LIMIT = 40
COMMON_PATHS = ("feed/", "feed", "rss", "rss.xml", "feed.xml", "index.xml", "atom.xml")
FEED_TYPES = {"application/rss+xml", "application/atom+xml"}


class _LinkFinder(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.found: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "link":
            return
        a = {k: (v or "") for k, v in attrs}
        if "alternate" in a.get("rel", "").lower() and a.get("type", "").lower() in FEED_TYPES and a.get("href"):
            self.found.append(a["href"])


def _download(session: requests.Session, url: str) -> bytes:
    resp = session.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.content


def parse_feed(session: requests.Session, url: str) -> list:
    entries = feedparser.parse(_download(session, url)).entries
    if not entries:
        raise ValueError("feed tanpa entri")
    return entries


def discover(session: requests.Session, page_url: str) -> tuple[str, list]:
    """Cari feed dari tag <link rel=alternate>, lalu dari jalur umum."""
    candidates: list[str] = []
    try:
        finder = _LinkFinder()
        finder.feed(_download(session, page_url).decode("utf-8", "replace"))
        candidates += [urljoin(page_url, h) for h in finder.found]
    except requests.RequestException as exc:
        log.debug("halaman %s tidak terbaca: %s", page_url, exc)
    parts = urlsplit(page_url)
    origin = f"{parts.scheme}://{parts.netloc}/"
    candidates += [urljoin(origin, p) for p in COMMON_PATHS]
    tried: set[str] = set()
    for cand in candidates:
        if cand in tried:
            continue
        tried.add(cand)
        try:
            return cand, parse_feed(session, cand)
        except (requests.RequestException, ValueError):
            continue
    raise LookupError("feed tidak ditemukan")


def load_entries(source: Source, known_feeds: dict[str, str]) -> tuple[str, list]:
    with requests.Session() as session:
        session.headers["User-Agent"] = USER_AGENT
        if source.list_rules:
            return load_list(session, source)
        if source.feed != "auto":
            return source.feed, parse_feed(session, source.feed)
        cached = known_feeds.get(source.url)
        if cached:
            try:
                return cached, parse_feed(session, cached)
            except (requests.RequestException, ValueError):
                log.info("feed tersimpan untuk %s gagal, mencari ulang", source.id)
        return discover(session, source.url)


def load_state(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    for key in ("feeds", "items", "health"):
        data.setdefault(key, {})
    return data


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def fetch_all(cfg: Config, state: dict, workers: int = 8) -> dict:
    now = datetime.now(timezone.utc)
    stamp = now.isoformat(timespec="seconds")
    sources = [s for s in cfg.sources if s.enabled]

    def key_of(s: Source) -> str:
        return s.url if s.feed == "auto" else s.feed

    unique: dict[str, Source] = {}
    for s in sources:
        unique.setdefault(key_of(s), s)

    results: dict[str, tuple[str, list] | Exception] = {}
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(load_entries, s, state["feeds"]): k for k, s in unique.items()}
        for fut in cf.as_completed(futures):
            try:
                results[futures[fut]] = fut.result()
            except Exception as exc:  # batas kerja per sumber: satu kegagalan tidak boleh menghentikan yang lain
                results[futures[fut]] = exc

    for s in sources:
        res = results[key_of(s)]
        health = state["health"].setdefault(s.id, {})
        health["checked"] = stamp
        if isinstance(res, Exception):
            health.update(ok=False, error=f"{type(res).__name__}: {res}"[:200])
            log.warning("gagal  %-24s %s", s.id, health["error"])
            continue
        feed_url, entries = res
        if s.feed == "auto":
            state["feeds"][s.url] = feed_url
        flt = compile_filter(s.include)
        items = [it for e in entries if (it := to_item(e, now)) and (flt is None or flt.search(it["_text"]))]
        fresh = [{k: v for k, v in it.items() if k != "_text"} for it in items]
        state["items"][s.id] = merge(state["items"].get(s.id, []), fresh, STORE_LIMIT)
        health.update(ok=True, error=None, feed=feed_url, seen=len(entries), kept=len(items), last_ok=stamp)
        log.info("sukses %-24s %d dari %d entri", s.id, len(items), len(entries))

    active = {s.id for s in cfg.sources}
    for section in ("items", "health"):
        state[section] = {k: v for k, v in state[section].items() if k in active}
    state["updated"] = stamp
    return state
