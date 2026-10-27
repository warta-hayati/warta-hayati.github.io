"""Antarmuka baris perintah: build, fetch, render, check."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .config import DEFAULT_CONFIG, ROOT, ConfigError, load
from .fetcher import fetch_all, load_state, save_state
from .render import render


def _print_health(cfg, state) -> int:
    failed = 0
    for s in cfg.sources:
        if not s.enabled:
            continue
        h = state["health"].get(s.id, {})
        ok = h.get("ok", False)
        failed += not ok
        detail = f"{h.get('kept', 0)} judul" if ok else h.get("error", "belum diperiksa")
        print(f"{'OK    ' if ok else 'GAGAL '} {s.id:<26} {detail}")
    print(f"\n{failed} sumber gagal dari {sum(s.enabled for s in cfg.sources)} sumber aktif")
    return failed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="wartahayati", description="Agregator pertanian, perikanan, kehutanan, dan ilmu hayati Asia")
    ap.add_argument("command", choices=["build", "fetch", "render", "check"], help="build: fetch lalu render; check: fetch lalu laporan kesehatan")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--data", type=Path, default=ROOT / "data" / "state.json")
    ap.add_argument("--out", type=Path, default=ROOT / "dist")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s")

    try:
        cfg = load(args.config)
    except ConfigError as exc:
        print(f"Konfigurasi tidak valid: {exc}")
        return 2
    state = load_state(args.data)

    if args.command in {"build", "fetch", "check"}:
        fetch_all(cfg, state)
        save_state(args.data, state)
    if args.command in {"build", "render"}:
        render(cfg, state, args.out)
        print(f"Situs dibangun di {args.out}")
    if args.command == "check":
        return 1 if _print_health(cfg, state) else 0
    return 0
