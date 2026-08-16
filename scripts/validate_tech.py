#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed tech-depth notes: packets, code, impl, perf, persona."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACKET_METHODS = {"har-sanitized", "curl-timing", "none"}
CODE_OBS = {"docs-only", "browser", "cli", "none"}
PERSONA_MODES = {"walkthrough-public", "approved-readonly", "none"}
OUTCOMES = {"열림", "일부", "막힘", "문서만"}
TECH_FILES = (
    "packets.json",
    "code-surface.json",
    "impl-methods.json",
    "perf.json",
    "persona-trials.json",
)
IMPL_KEYS = ("hosting", "auth", "data_path", "model_routing", "billing_unit")
PERF_NUMS = (
    "home_ttfb_ms",
    "home_total_ms",
    "api_median_ms",
    "stream_first_byte_ms",
    "stream_end_ms",
)


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _scan_of(root: Path) -> str:
    run_path = root / "run.json"
    if run_path.is_file():
        try:
            data = _load_json(run_path)
        except (OSError, json.JSONDecodeError):
            data = None
        if isinstance(data, dict):
            scan = _text(data.get("scan"))
            if scan in {"product", "landscape"}:
                return scan
    return "product"


def _has_deep_segment(root: Path) -> bool:
    path = root / "notes" / "segments.json"
    if not path.is_file():
        return False
    try:
        raw = _load_json(path)
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(raw, dict) or not isinstance(raw.get("segments"), list):
        return False
    for item in raw["segments"]:
        if isinstance(item, dict) and _text(item.get("depth")) == "deep":
            return True
    return False


def _shallow_ok(reason: str) -> bool:
    return "landscape-shallow" in reason


def validate_packets(data: object, *, allow_shallow: bool) -> list[str]:
    if not isinstance(data, dict):
        return ["packets.json must be an object"]
    errors: list[str] = []
    method = _text(data.get("method"))
    reason = _text(data.get("missing_reason"))
    if method not in PACKET_METHODS:
        errors.append("packets.method unknown or missing")
        return errors
    if method == "none":
        if not reason:
            errors.append("packets.missing_reason required when method is none")
        elif allow_shallow and not _shallow_ok(reason) and reason == "":
            errors.append("packets.missing_reason empty")
        return errors
    flows = data.get("flows")
    if not isinstance(flows, list) or not flows:
        return ["packets.flows required when method is not none"]
    for index, item in enumerate(flows):
        if not isinstance(item, dict):
            errors.append(f"packets.flows[{index}] is not an object")
            continue
        if not _text(item.get("method")):
            errors.append(f"packets.flows[{index}].method missing")
        if not (_text(item.get("host")) or _text(item.get("path"))):
            errors.append(f"packets.flows[{index}] needs host or path")
    return errors


def validate_code(data: object, *, allow_shallow: bool) -> list[str]:
    if not isinstance(data, dict):
        return ["code-surface.json must be an object"]
    observed = _text(data.get("observed"))
    reason = _text(data.get("missing_reason"))
    if observed not in CODE_OBS:
        return ["code-surface.observed unknown or missing"]
    if observed == "none":
        if not reason:
            return ["code-surface.missing_reason required when observed is none"]
        if allow_shallow:
            return []
        return []
    filled = any(
        [
            _text(data.get("public_repo")),
            _text(data.get("notes")),
            isinstance(data.get("entrypoints"), list) and bool(data.get("entrypoints")),
            isinstance(data.get("client_bundles"), list) and bool(data.get("client_bundles")),
            isinstance(data.get("cli_bins"), list) and bool(data.get("cli_bins")),
        ]
    )
    if not filled and not reason:
        return ["code-surface needs a public signal or missing_reason"]
    return []


def validate_impl(data: object, *, allow_shallow: bool) -> list[str]:
    if not isinstance(data, dict):
        return ["impl-methods.json must be an object"]
    reason = _text(data.get("missing_reason"))
    filled = any(_text(data.get(key)) for key in IMPL_KEYS)
    if not filled and not reason:
        return ["impl-methods needs a filled cell or missing_reason"]
    if allow_shallow and not filled and not _shallow_ok(reason) and not reason:
        return ["impl-methods.missing_reason required"]
    return []


def validate_perf(data: object, *, allow_shallow: bool) -> list[str]:
    if not isinstance(data, dict):
        return ["perf.json must be an object"]
    reason = _text(data.get("missing_reason"))
    nums = [data.get(key) for key in PERF_NUMS]
    has_num = any(isinstance(item, (int, float)) for item in nums)
    chars = data.get("characteristics")
    has_char = isinstance(chars, list) and any(_text(item) for item in chars)
    if not has_num and not has_char and not reason:
        return ["perf needs a timing, a characteristic, or missing_reason"]
    if allow_shallow:
        return []
    return []


def validate_persona(data: object, *, allow_shallow: bool) -> list[str]:
    if not isinstance(data, dict):
        return ["persona-trials.json must be an object"]
    errors: list[str] = []
    mode = _text(data.get("mode"))
    reason = _text(data.get("missing_reason"))
    if mode not in PERSONA_MODES:
        return ["persona-trials.mode unknown or missing"]
    if mode == "none":
        if not reason:
            return ["persona-trials.missing_reason required when mode is none"]
        return []
    trials = data.get("trials")
    if not isinstance(trials, list) or len(trials) < 2:
        return ["persona-trials needs at least two trials"]
    for index, item in enumerate(trials):
        if not isinstance(item, dict):
            errors.append(f"persona-trials.trials[{index}] is not an object")
            continue
        if not _text(item.get("persona")):
            errors.append(f"persona-trials.trials[{index}].persona missing")
        path = item.get("path")
        if not isinstance(path, list) or not path:
            errors.append(f"persona-trials.trials[{index}].path missing")
        outcome = _text(item.get("outcome"))
        if outcome not in OUTCOMES:
            errors.append(f"persona-trials.trials[{index}].outcome unknown")
        if item.get("mutation") is True:
            errors.append("persona-trial-as-mutation")
    if allow_shallow:
        return errors
    return errors


VALIDATORS = {
    "packets.json": validate_packets,
    "code-surface.json": validate_code,
    "impl-methods.json": validate_impl,
    "perf.json": validate_perf,
    "persona-trials.json": validate_persona,
}


def validate_tech(root: Path) -> list[str]:
    scan = _scan_of(root)
    allow_shallow = scan == "landscape" and not _has_deep_segment(root)
    errors: list[str] = []
    for name in TECH_FILES:
        path = root / "notes" / name
        if not path.is_file():
            errors.append(f"notes/{name} missing")
            continue
        try:
            data = _load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"notes/{name}: {exc}")
            continue
        errors.extend(VALIDATORS[name](data, allow_shallow=allow_shallow))
    return errors


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    args = p.parse_args(argv)
    root = args.root
    if not root.is_dir():
        print(f"FAIL: not a directory: {root}")
        return 1
    errors = validate_tech(root)
    if errors:
        print("FAIL")
        for item in errors:
            print(f"- {item}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
