#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed official-source inventory."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REQUIRED_KINDS = ("changelog", "blog", "docs", "press", "support")
LAYERS = {"primary", "secondary", "hint"}
ITEM_KINDS = REQUIRED_KINDS + ("rss", "status", "other")
MAX_ITEMS = 12
MAX_COMMUNITY = 8


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
    return any(
        isinstance(item, dict) and _text(item.get("depth")) == "deep"
        for item in raw["segments"]
    )


def validate_official_doc(data: object, *, allow_shallow: bool) -> list[str]:
    if not isinstance(data, dict):
        return ["official-sources.json must be an object"]
    reason = _text(data.get("missing_reason"))
    if allow_shallow and "landscape-shallow" in reason:
        return []
    errors: list[str] = []
    feeds = data.get("feeds")
    if not isinstance(feeds, list):
        return ["official-sources.feeds must be a list"]
    by_kind: dict[str, dict] = {}
    for index, item in enumerate(feeds):
        if not isinstance(item, dict):
            errors.append(f"feeds[{index}] is not an object")
            continue
        kind = _text(item.get("kind"))
        if kind in REQUIRED_KINDS and kind not in by_kind:
            by_kind[kind] = item
    for kind in REQUIRED_KINDS:
        feed = by_kind.get(kind)
        if feed is None:
            errors.append(f"feeds missing required kind: {kind}")
            continue
        found = feed.get("found")
        url = _text(feed.get("url"))
        miss = _text(feed.get("missing_reason"))
        if found is True:
            if not url:
                errors.append(f"feeds.{kind} found but url missing")
        else:
            if not miss:
                errors.append(f"feeds.{kind} missing_reason required when not found")
    items = data.get("items")
    if items is None:
        items = []
    if not isinstance(items, list):
        errors.append("official-sources.items must be a list")
        items = []
    if len(items) > MAX_ITEMS:
        errors.append(f"official-sources.items cap is {MAX_ITEMS}")
    seen: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"items[{index}] is not an object")
            continue
        iid = _text(item.get("id"))
        if not iid:
            errors.append(f"items[{index}].id missing")
        elif iid in seen:
            errors.append(f"duplicate item id: {iid}")
        else:
            seen.add(iid)
        kind = _text(item.get("kind"))
        if kind not in ITEM_KINDS:
            errors.append(f"items[{index}].kind unknown: {kind}")
        if not _text(item.get("url")):
            errors.append(f"items[{index}].url missing")
        layer = _text(item.get("layer")) or "primary"
        if layer not in LAYERS:
            errors.append(f"items[{index}].layer unknown: {layer}")
    community = data.get("community")
    if community is None:
        community = []
    if not isinstance(community, list):
        errors.append("official-sources.community must be a list")
        community = []
    if len(community) > MAX_COMMUNITY:
        errors.append(f"official-sources.community cap is {MAX_COMMUNITY}")
    for index, item in enumerate(community):
        if not isinstance(item, dict):
            errors.append(f"community[{index}] is not an object")
            continue
        if not _text(item.get("url")):
            errors.append(f"community[{index}].url missing")
        layer = _text(item.get("layer"))
        if layer == "primary":
            errors.append("last30days-as-official")
    return errors


def validate_official(root: Path) -> list[str]:
    allow_shallow = _scan_of(root) == "landscape" and not _has_deep_segment(root)
    path = root / "notes" / "official-sources.json"
    if not path.is_file():
        return ["notes/official-sources.json missing"]
    try:
        data = _load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"notes/official-sources.json: {exc}"]
    return validate_official_doc(data, allow_shallow=allow_shallow)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    args = p.parse_args(argv)
    if not args.root.is_dir():
        print(f"FAIL: not a directory: {args.root}")
        return 1
    errors = validate_official(args.root)
    if errors:
        print("FAIL")
        for item in errors:
            print(f"- {item}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
