#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One public GET with curl timings. Body discarded. No cookies stored."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

WRITE_OUT = (
    '{"url":"%{url_effective}","status":%{http_code},'
    '"time_starttransfer":%{time_starttransfer},"time_total":%{time_total}}'
)


def fetch(url: str) -> dict:
    proc = subprocess.run(
        [
            "curl",
            "-sS",
            "-L",
            "--max-redirs",
            "5",
            "-o",
            "/dev/null",
            "-D",
            "-",
            "-w",
            "\n" + WRITE_OUT,
            url,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    text = proc.stdout or ""
    timing_line = text.strip().splitlines()[-1] if text.strip() else "{}"
    try:
        payload = json.loads(timing_line)
    except json.JSONDecodeError:
        payload = {"url": url, "status": 0, "stderr": (proc.stderr or "")[:300]}
    payload["method"] = "GET"
    # keep header names only
    names: list[str] = []
    for line in text.splitlines()[:-1]:
        if ":" in line and not line.lower().startswith(("http/", "\r")):
            name = line.split(":", 1)[0].strip().lower()
            if name and name not in {"set-cookie"}:
                names.append(name)
    payload["res_headers"] = names
    return payload


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    row = fetch(args.url)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps([row], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
