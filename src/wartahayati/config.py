"""Muat dan validasi config/sources.yaml."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "sources.yaml"
LANGS = {"id", "en"}


class ConfigError(ValueError):
    """Konfigurasi sumber tidak valid."""


@dataclass(frozen=True)
class Topic:
    slug: str
    name: str


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    url: str
    tier: str
    lang: str
    topics: tuple[str, ...]
    feed: str = "auto"
    include: tuple[str, ...] = ()
    max_items: int = 6
    enabled: bool = True
    note: str = ""


@dataclass(frozen=True)
class Config:
    topics: tuple[Topic, ...]
    tiers: dict
    sources: tuple[Source, ...]


def _is_http(value: object) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def load(path: Path = DEFAULT_CONFIG) -> Config:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    topics = tuple(Topic(t["slug"], t["name"]) for t in raw.get("topics", []))
    if not topics:
        raise ConfigError("daftar 'topics' kosong")
    tiers = raw.get("tiers", {})
    slugs = {t.slug for t in topics}
    default_max = int(raw.get("defaults", {}).get("max_items", 6))

    sources: list[Source] = []
    seen: set[str] = set()
    for r in raw.get("sources", []):
        sid = r.get("id", "?")
        for key in ("id", "name", "url", "tier", "lang", "topics"):
            if not r.get(key):
                raise ConfigError(f"sumber '{sid}': kolom '{key}' wajib diisi")
        if sid in seen:
            raise ConfigError(f"id sumber ganda: '{sid}'")
        seen.add(sid)
        if r["tier"] not in tiers:
            raise ConfigError(f"sumber '{sid}': tingkat '{r['tier']}' tidak dikenal")
        if r["lang"] not in LANGS:
            raise ConfigError(f"sumber '{sid}': bahasa harus salah satu dari {sorted(LANGS)}")
        unknown = set(r["topics"]) - slugs
        if unknown:
            raise ConfigError(f"sumber '{sid}': topik tidak dikenal {sorted(unknown)}")
        feed = r.get("feed", "auto")
        if feed != "auto" and not _is_http(feed):
            raise ConfigError(f"sumber '{sid}': 'feed' harus 'auto' atau URL http(s)")
        if not _is_http(r["url"]):
            raise ConfigError(f"sumber '{sid}': 'url' harus diawali http:// atau https://")
        sources.append(
            Source(
                id=sid,
                name=r["name"],
                url=r["url"],
                tier=r["tier"],
                lang=r["lang"],
                topics=tuple(r["topics"]),
                feed=feed,
                include=tuple(r.get("include", [])),
                max_items=int(r.get("max_items", default_max)),
                enabled=bool(r.get("enabled", True)),
                note=r.get("note", ""),
            )
        )
    return Config(topics=topics, tiers=tiers, sources=tuple(sources))
