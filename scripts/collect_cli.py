#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dump CLI help per command. Counts can differ by surface — keep them separate."""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from pathlib import Path


DEFAULT_SURFACES = ("--help",)


def run_help(binary: str, args: list[str], timeout: float = 8.0) -> dict:
    cmd = [binary, *args]
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "cmd": cmd,
            "ok": False,
            "exit": None,
            "stdout": "",
            "stderr": str(exc),
        }
    return {
        "cmd": cmd,
        "ok": proc.returncode == 0,
        "exit": proc.returncode,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
    }


def write_dumps(out_dir: Path, results: list[dict]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    index = []
    for i, row in enumerate(results, start=1):
        slug = "-".join(a.strip("-") or "root" for a in row["cmd"][1:]) or "help"
        name = f"{i:02d}-{slug}.txt"
        body = row["stdout"] if row["stdout"] else row["stderr"]
        (out_dir / name).write_text(body, encoding="utf-8")
        index.append({"file": name, "cmd": row["cmd"], "exit": row["exit"], "ok": row["ok"]})
    (out_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out_dir / "index.json"


def render_notes(results: list[dict]) -> str:
    lines = ["# CLI 실측", ""]
    lines.append("| 표면 | 종료 | 줄 수 |")
    lines.append("|---|---:|---:|")
    for row in results:
        surface = " ".join(row["cmd"][1:]) or "(no args)"
        n = len((row["stdout"] or row["stderr"]).splitlines())
        code = row["exit"] if row["exit"] is not None else "err"
        lines.append(f"| `{surface}` | {code} | {n} |")
    lines.append("")
    lines.append("도구 목록은 명령마다 다시 찍는다. 한 목록을 전 표면에 복사하지 않는다.")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bin", required=True)
    p.add_argument(
        "--surface",
        action="append",
        default=None,
        help="repeatable. argparse-safe equals form only: --surface=--help",
    )
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--notes", type=Path)
    args = p.parse_args(argv)
    surfaces = args.surface or list(DEFAULT_SURFACES)
    results = []
    for surface in surfaces:
        raw = surface if isinstance(surface, str) else " ".join(surface)
        parts = shlex.split(raw) if raw.strip() else ["--help"]
        results.append(run_help(args.bin, parts))
    write_dumps(args.out, results)
    if args.notes:
        args.notes.parent.mkdir(parents=True, exist_ok=True)
        args.notes.write_text(render_notes(results), encoding="utf-8")
    if results and any(row["ok"] for row in results):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
