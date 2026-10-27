"""Fungsi murni untuk membersihkan, menyaring, dan menggabungkan butir feed."""
from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_TRACK_PREFIXES = ("utm_",)
_TRACK_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid", "igshid", "ref_src"}


def clean_text(value: str | None, limit: int = 220) -> str:
    text = html.unescape(_TAG.sub(" ", value or ""))
    text = _WS.sub(" ", text).strip()
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def canonical_url(url: str | None) -> str | None:
    """Kembalikan URL http(s) tanpa parameter pelacak, atau None bila skema tidak aman."""
    parts = urlsplit((url or "").strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith(_TRACK_PREFIXES) and k.lower() not in _TRACK_KEYS
    ]
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path or "/", urlencode(query), ""))


def dedupe_key(url: str) -> str:
    p = urlsplit(url)
    host = p.netloc.lower().removeprefix("www.")
    return f"{host}{p.path.rstrip('/')}?{p.query}"


def title_key(title: str) -> str:
    return re.sub(r"\W+", "", title.casefold())


def compile_filter(include: tuple[str, ...] | list[str]) -> re.Pattern | None:
    if not include:
        return None
    return re.compile("|".join(re.escape(k) for k in include), re.IGNORECASE)


def to_item(entry, now: datetime) -> dict | None:
    """Ubah entri feedparser menjadi butir {title, link, published, _text}."""
    title = clean_text(entry.get("title"))
    link = canonical_url(entry.get("link"))
    if not title or not link:
        return None
    stamp = entry.get("published_parsed") or entry.get("updated_parsed")
    published = datetime(*stamp[:6], tzinfo=timezone.utc) if stamp else now
    published = min(published, now)
    summary = clean_text(entry.get("summary"), 2000)
    return {
        "title": title,
        "link": link,
        "published": published.isoformat(timespec="seconds"),
        "_text": f"{title} {summary}",
    }


def merge(old: list[dict], new: list[dict], limit: int) -> list[dict]:
    """Gabungkan riwayat dan butir baru. Tanggal terbit lama dipertahankan."""
    by_key: dict[str, dict] = {}
    for item in old:
        by_key[dedupe_key(item["link"])] = item
    for item in new:
        key = dedupe_key(item["link"])
        if key in by_key:
            item = {**item, "published": by_key[key]["published"]}
        by_key[key] = item
    out: list[dict] = []
    seen_titles: set[str] = set()
    for item in sorted(by_key.values(), key=lambda i: i["published"], reverse=True):
        tk = title_key(item["title"])
        if tk and tk in seen_titles:
            continue
        seen_titles.add(tk)
        out.append(item)
    return out[:limit]
