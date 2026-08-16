#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed core and per-occurrence figure audit for a benchmark package."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
URL_RE = re.compile(r"^https?://", re.I)
DFORM_URL = re.compile(r"\[(https?://[^\]\s]+)\]\(\1\)")


def is_bridge(item: dict) -> bool:
    return item.get("role") == "bridge"


def figure_bridge_ids(manifest: dict) -> list[str]:
    """Figure bridge requirements come only from manifest claim types."""
    out: list[str] = []
    claims = manifest.get("claims")
    if not isinstance(claims, list):
        return out
    for claim in claims:
        if isinstance(claim, dict) and claim.get("type") == "figure":
            cid = str(claim.get("id") or "").strip()
            if cid:
                out.append(cid)
    return out


def report_images(md: str) -> list[dict[str, str]]:
    return [{"caption": match.group(1), "path": match.group(2)} for match in IMG_RE.finditer(md)]


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _ledger_urls(doc: object) -> list[str]:
    if not isinstance(doc, dict):
        return []
    if "cited" in doc:
        cited = doc.get("cited")
        return [str(item).strip() for item in cited] if isinstance(cited, list) else []
    out: list[str] = []
    for key in ("primary", "secondary"):
        rows = doc.get(key)
        if isinstance(rows, list):
            out.extend(str(item).strip() for item in rows)
    return out


def ledger_http_urls(root: Path) -> set[str]:
    sources = root / "notes" / "sources.json"
    if not sources.is_file():
        return set()
    try:
        doc = json.loads(sources.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return {item for item in _ledger_urls(doc) if URL_RE.match(item)}


def dform_http_urls(root: Path, md: str | None = None) -> set[str]:
    if md is None:
        report = root / "report" / "report.md"
        if not report.is_file():
            return set()
        try:
            md = report.read_text(encoding="utf-8")
        except OSError:
            return set()
    return set(DFORM_URL.findall(md))


def classify_http_evidence(ref: str, ledger_urls: set[str], dform_urls: set[str]) -> str:
    in_ledger = ref in ledger_urls
    in_dform = ref in dform_urls
    if in_ledger and in_dform:
        return "both"
    if in_dform and not in_ledger:
        return "dform-only"
    if in_ledger and not in_dform:
        return "ledger-only"
    return "unregistered"


def evidence_exists(
    root: Path,
    ref: str,
    ledger_urls: set[str] | None = None,
    dform_urls: set[str] | None = None,
) -> bool:
    if URL_RE.match(ref):
        led = ledger_http_urls(root) if ledger_urls is None else ledger_urls
        dfo = dform_http_urls(root) if dform_urls is None else dform_urls
        return classify_http_evidence(ref, led, dfo) == "both"
    clean = ref.split("#", 1)[0].strip()
    if not clean:
        return False
    base = root.resolve()
    candidates = (base / clean, base / "report" / clean)
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
            resolved.relative_to(base)
            if resolved.is_file():
                return True
        except (OSError, ValueError):
            continue
    return False


def _items(doc: object, label: str, errors: list[str]) -> list[dict]:
    raw = doc.get("items") if isinstance(doc, dict) else doc
    if not isinstance(raw, list):
        errors.append(f"{label} items missing")
        return []
    out: list[dict] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            errors.append(f"{label} item[{index}] is not an object")
        else:
            out.append(item)
    return out


def _id_map(items: list[dict], key: str, label: str, errors: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    seen: Counter[str] = Counter()
    for index, item in enumerate(items):
        value = str(item.get(key) or "").strip()
        if not value:
            errors.append(f"{label} item[{index}] missing {key}")
            continue
        seen[value] += 1
        out[value] = item
    duplicates = sorted(value for value, count in seen.items() if count > 1)
    if duplicates:
        errors.append(f"duplicate {label} ids: {duplicates}")
    return out


def _manifest_contract(manifest: object, errors: list[str]) -> tuple[list[str], list[str]]:
    if not isinstance(manifest, dict):
        errors.append("audit-manifest root must be an object")
        return [], []

    raw_core = manifest.get("core_required")
    if not isinstance(raw_core, list) or not raw_core:
        errors.append("manifest core_required must be a non-empty list")
        core: list[str] = []
    else:
        core = [str(item).strip() for item in raw_core if str(item).strip()]
        if len(core) != len(raw_core):
            errors.append("manifest core_required has an empty id")
        if len(core) != len(set(core)):
            errors.append("manifest core_required has duplicate ids")

    claims = manifest.get("claims")
    if not isinstance(claims, list) or not claims:
        errors.append("manifest claims must be a non-empty list")
        return core, []
    claim_ids: list[str] = []
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            errors.append(f"manifest claim[{index}] is not an object")
            continue
        cid = str(claim.get("id") or "").strip()
        if not cid:
            errors.append(f"manifest claim[{index}] missing id")
        else:
            claim_ids.append(cid)
    if len(claim_ids) != len(set(claim_ids)):
        errors.append("manifest claims have duplicate ids")
    return core, figure_bridge_ids(manifest)


def audit_errors(root: Path) -> tuple[list[str], dict]:
    errors: list[str] = []
    manifest_path = root / "sources" / "audit-manifest.json"
    fact_path = root / "sources" / "audit-fact.json"
    visual_path = root / "sources" / "audit-visual.json"
    report_path = root / "report" / "report.md"
    for path in (manifest_path, fact_path, visual_path, report_path):
        if not path.is_file():
            errors.append(f"missing {path.relative_to(root)}")
    if errors:
        return errors, _stats(0, 0, 0, 0, 0)

    manifest = load_json(manifest_path)
    fact_doc = load_json(fact_path)
    visual_doc = load_json(visual_path)
    md = report_path.read_text(encoding="utf-8")
    required, needed_bridges = _manifest_contract(manifest, errors)
    fact_items = _items(fact_doc, "audit-fact", errors)
    visual_items = _items(visual_doc, "audit-visual", errors)
    ledger_urls = ledger_http_urls(root)
    dform_urls = dform_http_urls(root, md)

    facts = _id_map(fact_items, "claim_id", "fact claim", errors)
    mismatch = 0
    core_ok = 0
    for cid in required:
        item = facts.get(cid)
        if item is None:
            errors.append(f"core missing from audit-fact: {cid}")
            continue
        if item.get("verdict") != "match":
            mismatch += 1
            errors.append(f"core mismatch: {cid} verdict={item.get('verdict')}")
            continue
        evidence = item.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"core {cid} has no evidence")
            continue
        missing_files = [
            str(ref)
            for ref in evidence
            if not URL_RE.match(str(ref))
            and not evidence_exists(root, str(ref), ledger_urls, dform_urls)
        ]
        classes = [
            classify_http_evidence(str(ref), ledger_urls, dform_urls)
            for ref in evidence
            if URL_RE.match(str(ref))
        ]
        if "dform-only" in classes:
            errors.append(f"core {cid} dform-only url evidence")
            continue
        if "ledger-only" in classes:
            errors.append(f"core {cid} ledger-only url evidence")
            continue
        if "unregistered" in classes:
            errors.append(f"core {cid} unregistered url evidence")
            continue
        if missing_files:
            errors.append(f"core {cid} missing evidence files")
            continue
        core_ok += 1

    images = report_images(md)
    if not images:
        errors.append("report has no figures")
    occurrence_items = [item for item in visual_items if not is_bridge(item)]
    bridge_items = [item for item in visual_items if is_bridge(item)]
    occurrence_ids = _id_map(occurrence_items, "id", "visual occurrence", errors)

    visual_pairs: list[tuple[str, str]] = []
    for item in occurrence_items:
        path = item.get("path")
        caption = item.get("caption")
        if (
            not isinstance(path, str)
            or not path.strip()
            or not isinstance(caption, str)
            or not caption.strip()
        ):
            errors.append(f"visual entry missing path/caption: {item.get('id')}")
            continue
        visual_pairs.append((caption, path))
        if item.get("verdict") != "match":
            mismatch += 1
            errors.append(f"figure mismatch: {item.get('id')} verdict={item.get('verdict')}")
        if not str(item.get("observed") or item.get("screen") or "").strip():
            errors.append(f"figure {item.get('id')} missing screen reading")
        if not evidence_exists(root, path, ledger_urls, dform_urls):
            errors.append("figure file missing")

    report_pairs = [(item["caption"], item["path"]) for item in images]
    report_count = Counter(report_pairs)
    visual_count = Counter(visual_pairs)
    audited_figures = sum((report_count & visual_count).values())
    for pair, count in (report_count - visual_count).items():
        errors.append(f"report image not in visual audit ({count}): {pair}")
    extras = list((visual_count - report_count).elements())
    if extras:
        errors.append(f"visual extras vs report refs: {extras}")
    if len(occurrence_items) != len(images):
        errors.append(f"occurrence count visual={len(occurrence_items)} report={len(images)}")

    bridges = _id_map(bridge_items, "claim_id", "bridge claim", errors)
    extra_bridges = sorted(set(bridges) - set(needed_bridges))
    if extra_bridges:
        errors.append(f"bridge extras vs manifest figure claims: {extra_bridges}")
    bridge_ok = 0
    for cid in needed_bridges:
        item = bridges.get(cid)
        if item is None:
            errors.append(f"bridge missing: {cid}")
            continue
        if item.get("verdict") != "match":
            mismatch += 1
            errors.append(f"bridge mismatch: {cid} verdict={item.get('verdict')}")
            continue
        if not str(item.get("observed") or "").strip():
            errors.append(f"bridge {cid} missing observed")
            continue
        supporting = item.get("supporting")
        if not isinstance(supporting, list) or not supporting:
            errors.append(f"bridge {cid} missing supporting occurrence ids")
            continue
        missing = [str(sid) for sid in supporting if str(sid) not in occurrence_ids]
        if missing:
            errors.append(f"bridge {cid} missing supporting: {missing}")
            continue
        bridge_ok += 1

    stats = _stats(core_ok, len(required), audited_figures, len(images), mismatch, bridge_ok, len(needed_bridges))
    if core_ok != len(required) or not required:
        errors.append(f"core audited/required {stats['core']} != 100%")
    if audited_figures != len(images) or not images:
        errors.append(f"occurrence audited/report refs {stats['occurrence']} != 100%")
    if bridge_ok != len(needed_bridges):
        errors.append(f"bridge audited/required {stats['bridge']} != 100%")
    if mismatch != 0:
        errors.append(f"mismatch {mismatch} != 0")
    return errors, stats


def _stats(
    core_ok: int,
    core_n: int,
    fig_ok: int,
    fig_n: int,
    mismatch: int,
    bridge_ok: int = 0,
    bridge_n: int = 0,
) -> dict:
    return {
        "core": f"{core_ok}/{core_n}",
        "figures": f"{fig_ok}/{fig_n}",
        "occurrence": f"{fig_ok}/{fig_n}",
        "bridge": f"{bridge_ok}/{bridge_n}",
        "mismatch": mismatch,
        "core_ok": core_ok,
        "core_n": core_n,
        "fig_ok": fig_ok,
        "fig_n": fig_n,
        "bridge_ok": bridge_ok,
        "bridge_n": bridge_n,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        errors, stats = audit_errors(root)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    summary = (
        f"core {stats['core']} occurrence {stats['occurrence']} "
        f"bridge {stats['bridge']} mismatch {stats['mismatch']}"
    )
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        print(summary)
        return 1
    print(f"OK {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
