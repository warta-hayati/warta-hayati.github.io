"""Bangun situs statis dari konfigurasi dan state."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import ROOT, Config

MARKER = ".wartahayati"


def _prepare(out: Path) -> None:
    if out.exists():
        if any(out.iterdir()) and not (out / MARKER).exists():
            raise SystemExit(f"{out} sudah berisi berkas lain. Pilih folder keluaran yang kosong.")
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / MARKER).write_text("dibuat oleh wartahayati\n", encoding="utf-8")


def render(cfg: Config, state: dict, out: Path = ROOT / "dist") -> None:
    items = state.get("items", {})
    health = state.get("health", {})
    enabled = [s for s in cfg.sources if s.enabled]
    boxes = {
        s.id: {"source": s, "items": items.get(s.id, [])[: s.max_items], "health": health.get(s.id, {})}
        for s in enabled
    }
    by_topic = {t.slug: [boxes[s.id] for s in enabled if t.slug in s.topics] for t in cfg.topics}
    primary = {t.slug: [boxes[s.id] for s in enabled if s.topics[0] == t.slug] for t in cfg.topics}

    def filled(boxes_: list[dict]) -> list[dict]:
        """Sisakan kotak yang punya judul. Sumber yang gagal tampil di halaman status."""
        return [b for b in boxes_ if b["items"]]

    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    common = {"topics": cfg.topics, "tiers": cfg.tiers, "updated": state.get("updated")}
    _prepare(out)

    def write(rel: str, template: str, path: str = "", **ctx) -> None:
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(env.get_template(template).render(**common, path=path, **ctx), encoding="utf-8")

    write(
        "index.html",
        "index.html",
        "",
        root="",
        current=None,
        sections=[(t, filled(primary[t.slug])) for t in cfg.topics],
    )
    for t in cfg.topics:
        write(f"topik/{t.slug}/index.html", "topik.html", f"topik/{t.slug}/", root="../../", current=t.slug, topic=t, boxes=filled(by_topic[t.slug]))

    rows = sorted(
        ({"source": s, "health": health.get(s.id, {})} for s in enabled),
        key=lambda r: (r["health"].get("ok", False), r["source"].name.lower()),
    )
    write(
        "status/index.html",
        "status.html",
        "status/",
        root="../",
        current="status",
        rows=rows,
        candidates=[s for s in cfg.sources if not s.enabled],
    )

    shutil.copytree(ROOT / "static", out / "static")
    # Sebagian peramban, pembaca feed, dan layanan lain meminta /favicon.ico
    # langsung di akar situs, tanpa membaca tag <link rel="icon">.
    shutil.copyfile(ROOT / "static" / "favicon.ico", out / "favicon.ico")
    export = {
        "updated": state.get("updated"),
        "sources": [
            {
                "id": s.id,
                "name": s.name,
                "url": s.url,
                "tier": s.tier,
                "lang": s.lang,
                "topics": list(s.topics),
                "items": boxes[s.id]["items"],
            }
            for s in enabled
        ],
    }
    (out / "data.json").write_text(json.dumps(export, ensure_ascii=False, indent=1), encoding="utf-8")
