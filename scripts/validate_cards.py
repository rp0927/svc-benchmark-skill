#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed feature-card schema and evidence check."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REQUIRED = (
    "id",
    "name",
    "status",
    "one_liner",
    "job_to_be_done",
    "insight",
    "deleted",
    "evidence",
)
FORBIDDEN = ("if_we_build",)
STATUS = {"live", "beta", "deprecated", "deleted"}
DIFFICULTY = {None, "S", "M", "L", "XL"}
OBSERVED = {"browser", "cli", "docs", "docs+cli", "docs-only", "official-image", "network"}
PATH_REQUIRED = {"cli", "docs+cli", "network"}


def load_cards(raw: object) -> list[dict]:
    if isinstance(raw, dict) and "cards" in raw:
        raw = raw["cards"]
    if not isinstance(raw, list):
        raise ValueError("root must be a list or {cards: [...]}")
    cards: list[dict] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"card[{index}] is not an object")
        cards.append(item)
    return cards


def infer_package_root(card_path: Path) -> Path:
    resolved = card_path.resolve()
    for parent in resolved.parents:
        if parent.name == "notes":
            return parent.parent
    return resolved.parent


def _file(root: Path | None, value: object) -> Path | None:
    if root is None or not isinstance(value, str) or not value.strip():
        return None
    rel = Path(value)
    if rel.is_absolute():
        return None
    try:
        path = (root / rel).resolve()
        path.relative_to(root.resolve())
        return path if path.is_file() else None
    except (OSError, ValueError):
        return None


def _browser_tree_paths(root: Path) -> set[Path]:
    """Return redacted accessibility-tree artifacts eligible for browser evidence."""
    config_path = root / "notes" / "privacy-exceptions.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    redactions = config.get("redactions") if isinstance(config, dict) else None
    if not isinstance(redactions, list):
        return set()
    docs = (root / "evidence" / "docs").resolve()
    valid: set[Path] = set()
    for item in redactions:
        if not isinstance(item, dict) or item.get("kind") != "accessibility-tree":
            continue
        path = _file(root, item.get("path"))
        markers = item.get("markers")
        if path is None or path.suffix.lower() not in {".txt", ".json"}:
            continue
        try:
            path.relative_to(docs)
        except ValueError:
            continue
        if not isinstance(markers, list) or not markers or any(not str(marker).strip() for marker in markers):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if all(str(marker) in text for marker in markers):
            valid.add(path)
    return valid


def validate_cards(cards: list[dict], root: Path | None = None) -> list[str]:
    errors: list[str] = []
    ids: list[str] = []
    if not cards:
        return ["no cards"]
    browser_trees = _browser_tree_paths(root) if root is not None else set()
    for index, card in enumerate(cards):
        prefix = f"card[{index}]"
        for key in REQUIRED:
            if key not in card:
                errors.append(f"{prefix} missing {key}")
        for key in FORBIDDEN:
            if key in card:
                errors.append(f"{prefix} forbidden field {key}")
        cid = card.get("id")
        if not isinstance(cid, str) or not cid.strip():
            errors.append(f"{prefix} id must be a non-empty string")
        else:
            if cid != cid.strip() or " " in cid:
                errors.append(f"{prefix} id must be a stable slug without spaces: {cid!r}")
            ids.append(cid)
        status = card.get("status")
        if status not in STATUS:
            errors.append(f"{prefix} bad status {status!r}")
        if card.get("deleted") is True and status not in {"deleted", "deprecated"}:
            errors.append(f"{prefix} deleted=true but status={status!r}")
        if card.get("deleted") is False and status == "deleted":
            errors.append(f"{prefix} status=deleted but deleted=false")
        if card.get("difficulty") not in DIFFICULTY:
            errors.append(f"{prefix} bad difficulty {card.get('difficulty')!r}")

        screenshot = card.get("screenshot")
        screenshot_ok = False
        if screenshot is not None:
            if not isinstance(screenshot, str) or not screenshot.strip():
                errors.append(f"{prefix} screenshot must be null or a non-empty path")
            elif root is not None:
                screenshot_ok = _file(root, screenshot) is not None
                if not screenshot_ok:
                    errors.append(f"{prefix} screenshot file missing or outside package")

        evidence = card.get("evidence", [])
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{prefix} evidence must be a non-empty list")
        else:
            for row_index, row in enumerate(evidence):
                row_prefix = f"{prefix}.evidence[{row_index}]"
                if not isinstance(row, dict):
                    errors.append(f"{row_prefix} not object")
                    continue
                observed = row.get("observed")
                if observed not in OBSERVED:
                    errors.append(f"{row_prefix} bad observed {observed!r}")
                for key in ("url", "note"):
                    if not isinstance(row.get(key), str) or not row[key].strip():
                        errors.append(f"{row_prefix} {key} must be non-empty")
                path_file = _file(root, row.get("path"))
                path_ok = path_file is not None
                if root is not None and observed in PATH_REQUIRED and not path_ok:
                    errors.append(f"{row_prefix} {observed} requires an existing evidence.path")
                if root is not None and observed == "browser" and not (
                    screenshot_ok or path_file in browser_trees
                ):
                    errors.append(
                        f"{row_prefix} browser without screenshot requires a redacted evidence/docs accessibility tree; otherwise use docs-only"
                    )
                if root is not None and observed == "official-image" and not (screenshot_ok or path_ok):
                    errors.append(f"{row_prefix} official-image requires card screenshot or existing evidence.path")
                if row.get("path") is not None and root is not None and not path_ok:
                    errors.append(f"{row_prefix} evidence.path file missing or outside package")

        empty_core = not card.get("one_liner") and not card.get("job_to_be_done")
        if empty_core and not card.get("missing_reason"):
            errors.append(f"{prefix} empty core fields need missing_reason")
    if len(ids) != len(set(ids)):
        errors.append("duplicate id")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    try:
        cards = load_cards(json.loads(args.path.read_text(encoding="utf-8")))
        errors = validate_cards(cards, infer_package_root(args.path))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"OK {len(cards)} cards")
    return 0


if __name__ == "__main__":
    sys.exit(main())
