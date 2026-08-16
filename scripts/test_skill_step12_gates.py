#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 12 live gates, PROJECT_ROOT paths, and semantic dual-tree parity."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
AGENTS = HERE.parent / "SKILL.md"


def _find_repo(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / ".claude/skills/svc-benchmark/SKILL.md").is_file() and (
            parent / ".agents/skills/svc-benchmark/SKILL.md"
        ).is_file():
            return parent
    raise SystemExit("repo root with dual-tree SKILL.md not found")


REPO = _find_repo(HERE)
CLAUDE = REPO / ".claude/skills/svc-benchmark/SKILL.md"
COMMAND = REPO / ".claude/commands/svc-benchmark.md"
BROWSER_SOP = HERE.parent / "references/browser-sop.md"
NETWORK_CAPTURE = HERE.parent / "references/network-capture.md"

COVERAGE = (
    'python3 "$SKILL/scripts/validate_coverage.py" '
    "--report report/report.md --cards notes/feature-cards.json"
)
SOURCES = (
    'python3 "$SKILL/scripts/validate_sources.py" '
    "--report report/report.md --sources notes/sources.json"
)
PRIVACY = 'python3 "$SKILL/scripts/validate_privacy.py" --root .'
AUDIT = 'python3 "$SKILL/scripts/validate_audit.py" --root .'
OFFICIAL_FRAG = "$PROJECT_ROOT/.agents/skills/doc-autoaudit/scripts/audit_gate.py"
CONVERT_FRAG = "$PROJECT_ROOT/.agents/skills/_output-rules/convert.js"
PDFVAL_FRAG = "$PROJECT_ROOT/.agents/scripts/validate-pdf-output.py"
CARDS = 'python3 "$SKILL/scripts/validate_cards.py" notes/feature-cards.json'
REPORT = 'python3 "$SKILL/scripts/validate_report.py" report/report.md'
SCAN = 'python3 "$SKILL/scripts/validate_scan.py" --root .'
TECH = 'python3 "$SKILL/scripts/validate_tech.py" --root .'
OFFICIAL = 'python3 "$SKILL/scripts/validate_official.py" --root .'
OLD_SHARED = (
    "python3 .agents/skills/doc-autoaudit/scripts/audit_gate.py",
    "node .agents/skills/_output-rules/convert.js",
    "python3 .agents/scripts/validate-pdf-output.py",
    'SKILL="$(pwd)/.agents/skills/svc-benchmark"',
    "OUT=data/research/YYYYMMDD_<slug>",
)
SHARED_PATHS = (
    ".agents/skills/doc-autoaudit/scripts/audit_gate.py",
    ".agents/skills/_output-rules/convert.js",
    ".agents/scripts/validate-pdf-output.py",
)
SKILL_LINE = re.compile(r"^`\$SKILL`은 .+$", re.M)
LINK = re.compile(r"(\[[^\]]+\]\()([^)]+)(\))")
DIRECT_RAW_NETWORK = re.compile(
    r"evidence/network/(?:raw|hook)[^\s`)\]]*\.(?:json|har|log)", re.I
)

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def step12(text: str) -> str:
    m = re.search(r"### 12\. 마무리\n(.*?)(?=\n## |\Z)", text, re.S)
    check(m is not None, "Step 12 heading missing")
    return m.group(1) if m else ""


def start_block(text: str) -> str:
    m = re.search(r"## 시작: 폴더를 먼저 만든다\n(.*?)(?=\n## |\Z)", text, re.S)
    check(m is not None, "start heading missing")
    return m.group(1) if m else ""


def runtime_network_block(text: str) -> str:
    section_match = re.search(r"### 8\. 런타임 실측\n(.*?)(?=\n### 9\.)", text, re.S)
    check(section_match is not None, "runtime section missing")
    section = section_match.group(1) if section_match else ""
    block_match = re.search(r"```bash\n(.*?)\n```", section, re.S)
    check(block_match is not None, "runtime network bash block missing")
    return block_match.group(1) if block_match else ""


def test_step12_has_live_paths() -> None:
    for label, path in (("agents", AGENTS), ("claude", CLAUDE)):
        text = path.read_text(encoding="utf-8")
        block = step12(text)
        start = start_block(text)
        for needle, name in (
            (REPORT, "validate_report"),
            (SCAN, "validate_scan"),
            (OFFICIAL, "validate_official"),
            (TECH, "validate_tech"),
            (CARDS, "validate_cards"),
            (COVERAGE, "validate_coverage"),
            (SOURCES, "validate_sources"),
            (PRIVACY, "validate_privacy"),
            (AUDIT, "validate_audit"),
            (OFFICIAL_FRAG, "audit_gate PROJECT_ROOT"),
            (CONVERT_FRAG, "convert.js PROJECT_ROOT"),
            (PDFVAL_FRAG, "validate-pdf-output PROJECT_ROOT"),
        ):
            check(needle in text, f"{label} missing {name}: {needle}")
        check("sources/audit-fact.json" in block, f"{label} missing audit-fact arg")
        check("sources/audit-visual.json" in block, f"{label} missing audit-visual arg")
        check("--manifest sources/audit-manifest.json" in block, f"{label} missing audit-manifest arg")
        check("PROJECT_ROOT=" in start, f"{label} start missing PROJECT_ROOT")
        check('SKILL="$PROJECT_ROOT/' in start, f"{label} SKILL not from PROJECT_ROOT")
        check('OUT="$PROJECT_ROOT/' in start, f"{label} OUT not absolute under PROJECT_ROOT")
        check('cd "$OUT"' in start, f"{label} missing cd OUT")
        for old in OLD_SHARED:
            check(old not in text, f"{label} stale command remains: {old}")
        if REPORT in block and COVERAGE in block:
            check(block.index(REPORT) < block.index(COVERAGE), f"{label} coverage before report")
        if REPORT in block and SCAN in block:
            check(block.index(REPORT) < block.index(SCAN), f"{label} scan before report")
        if SCAN in block and OFFICIAL in block:
            check(block.index(SCAN) < block.index(OFFICIAL), f"{label} official before scan")
        if OFFICIAL in block and TECH in block:
            check(block.index(OFFICIAL) < block.index(TECH), f"{label} tech before official")
        if TECH in block and CARDS in block:
            check(block.index(TECH) < block.index(CARDS), f"{label} cards before tech")
        if CARDS in block and COVERAGE in block:
            check(block.index(CARDS) < block.index(COVERAGE), f"{label} coverage before cards")
        if COVERAGE in block and SOURCES in block:
            check(block.index(COVERAGE) < block.index(SOURCES), f"{label} sources before coverage")
        if SOURCES in block and PRIVACY in block:
            check(block.index(SOURCES) < block.index(PRIVACY), f"{label} privacy before sources")
        if PRIVACY in block and AUDIT in block:
            check(block.index(PRIVACY) < block.index(AUDIT), f"{label} audit before privacy")
        if AUDIT in block and OFFICIAL_FRAG in block:
            check(block.index(AUDIT) < block.index(OFFICIAL_FRAG), f"{label} official gate before audit")


def test_shared_paths_resolve() -> None:
    for rel in SHARED_PATHS:
        resolved = (REPO / rel).resolve()
        check(resolved.is_file(), f"shared path missing: {rel} -> {resolved}")
        check(str(resolved).startswith(str(REPO)), f"shared path escaped repo: {resolved}")
    for script in (
        "validate_report.py",
        "validate_scan.py",
        "validate_official.py",
        "validate_tech.py",
        "validate_cards.py",
        "validate_coverage.py",
        "validate_sources.py",
        "validate_privacy.py",
        "validate_audit.py",
    ):
        check((HERE / script).is_file(), f"skill script missing: {script}")


def _write_synthetic_audit(out: Path) -> None:
    sources = out / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    (sources / "audit-fact.json").write_text(
        json.dumps(
            {
                "items": [
                    {
                        "claim_id": "c001",
                        "verdict": "match",
                        "observed": "synthetic observed text",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (sources / "audit-visual.json").write_text(
        json.dumps({"items": []}),
        encoding="utf-8",
    )
    (sources / "audit-manifest.json").write_text(
        json.dumps(
            {
                "doc": "report/report.md",
                "as_of": "x",
                "core_required": [],
                "claims": [{"id": "c001"}],
            }
        ),
        encoding="utf-8",
    )


def _copy_live_audit(live: Path, out: Path) -> bool:
    rels = (
        "sources/audit-fact.json",
        "sources/audit-visual.json",
        "sources/audit-manifest.json",
    )
    if not all((live / rel).is_file() for rel in rels):
        return False
    for rel in rels:
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((live / rel).read_bytes())
    return True


def test_e2e_from_out_cwd() -> None:
    live = REPO / "data/research/20260814_grok-bot"
    gate = REPO / ".agents/skills/doc-autoaudit/scripts/audit_gate.py"
    check(gate.is_file(), f"audit_gate missing at {gate}")
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out"
        out.mkdir()
        used_live = _copy_live_audit(live, out) if live.is_dir() else False
        if not used_live:
            _write_synthetic_audit(out)
        env = os.environ.copy()
        env["PROJECT_ROOT"] = str(REPO)
        args = [
            "sources/audit-fact.json",
            "sources/audit-visual.json",
            "--manifest",
            "sources/audit-manifest.json",
        ]
        rel = subprocess.run(
            [sys.executable, ".agents/skills/doc-autoaudit/scripts/audit_gate.py", *args],
            cwd=out,
            env=env,
            capture_output=True,
            text=True,
        )
        check(
            rel.returncode != 0,
            "old OUT-relative audit_gate unexpectedly succeeded",
        )
        abs_cmd = [sys.executable, str(gate), *args]
        good = subprocess.run(abs_cmd, cwd=out, env=env, capture_output=True, text=True)
        check(
            good.returncode == 0,
            "e2e audit_gate from OUT cwd: "
            f"{good.returncode} live={used_live} stdout={good.stdout!r} stderr={good.stderr!r}",
        )
        check("CONVERGED" in (good.stdout + good.stderr), "e2e audit_gate missing CONVERGED")


def _local_target(skill_path: Path, target: str) -> tuple[Path, str] | None:
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return None
    raw, marker, fragment = target.partition("#")
    return (skill_path.parent / raw).resolve(), (marker + fragment if marker else "")


def _semantic_text(skill_path: Path) -> str:
    text = skill_path.read_text(encoding="utf-8")
    text = SKILL_LINE.sub("`$SKILL`은 <SKILL_ROOT>다.", text)
    canonical = AGENTS.parent.resolve()

    def replace(match: re.Match[str]) -> str:
        target = match.group(2)
        resolved = _local_target(skill_path, target)
        if resolved is None:
            return match.group(0)
        path, fragment = resolved
        try:
            rel = path.relative_to(canonical).as_posix()
            normalized = f"<SKILL_ROOT>/{rel}{fragment}"
        except ValueError:
            normalized = f"<LOCAL>/{path.name}{fragment}"
        return f"{match.group(1)}{normalized}{match.group(3)}"

    return LINK.sub(replace, text)


def test_dual_tree_semantic_parity() -> None:
    a = AGENTS.read_text(encoding="utf-8")
    c = CLAUDE.read_text(encoding="utf-8")
    check(_semantic_text(AGENTS) == _semantic_text(CLAUDE), "SKILL.md semantic content differs")
    a_skill = SKILL_LINE.findall(a)
    c_skill = SKILL_LINE.findall(c)
    check(len(a_skill) == 1 and len(c_skill) == 1, "expected one $SKILL line each")
    if a_skill and c_skill:
        check(a_skill[0] != c_skill[0], "intended $SKILL lines should differ")
        check("이 파일이 있는 디렉터리" in a_skill[0], a_skill[0])
        check(".agents/skills/svc-benchmark" in c_skill[0], c_skill[0])


def test_all_local_links_exist() -> None:
    for label, skill_path in (("agents", AGENTS), ("claude", CLAUDE)):
        text = skill_path.read_text(encoding="utf-8")
        for target in (match.group(2) for match in LINK.finditer(text)):
            resolved = _local_target(skill_path, target)
            if resolved is not None:
                check(resolved[0].exists(), f"{label} broken local link: {target}")


def _direct_raw_network_paths(text: str) -> list[str]:
    return DIRECT_RAW_NETWORK.findall(text)


def test_network_document_contract() -> None:
    documents = (
        ("agents", AGENTS),
        ("claude", CLAUDE),
        ("command", COMMAND),
        ("browser-sop", BROWSER_SOP),
        ("network-capture", NETWORK_CAPTURE),
    )
    for label, path in documents:
        text = path.read_text(encoding="utf-8")
        check(
            not _direct_raw_network_paths(text),
            f"{label} stores raw network data in package: {_direct_raw_network_paths(text)}",
        )

    for label, path in (("agents", AGENTS), ("claude", CLAUDE)):
        text = path.read_text(encoding="utf-8")
        block = runtime_network_block(text)
        for needle in (
            "mktemp -d",
            'RAW_INPUT="${RAW_INPUT:-$RAW_TMP_DIR/raw.json}"',
            '"$RAW_INPUT" --out evidence/network/session.json',
            "--har evidence/network/session.json",
        ):
            check(needle in block, f"{label} runtime block missing: {needle}")
        check("HAR도 패키지 밖" in text, f"{label} missing sanitized HAR contract")
        check("원본 HAR를 직접 통과시키지 않는다" in text, f"{label} permits raw HAR passthrough")
        check("--phase=jtbd" in text, f"{label} missing --phase=jtbd")
        check("--phase=segments" in text, f"{label} missing --phase=segments")
        check("한 번에 질문 하나만" in text, f"{label} missing grill TFG")
        check("notes/failures.json" in text, f"{label} missing named failures file")
        check("notes/precheck.json" in text, f"{label} missing precheck file")
        check("process.md" in text, f"{label} missing process.md")

    command = COMMAND.read_text(encoding="utf-8")
    for needle in ("원본 HAR·hook·네트워크 로그", "패키지 밖 임시 `$RAW_INPUT`", "ingest sanitizer"):
        check(needle in command, f"command missing raw boundary: {needle}")

    browser = BROWSER_SOP.read_text(encoding="utf-8")
    for needle in ("$RAW_INPUT", "ingest_network.py", "evidence/network/session.json"):
        check(needle in browser, f"browser-sop missing hook ingest contract: {needle}")


def test_direct_raw_network_regression_fixture() -> None:
    unsafe = "로그 회수 → evidence/network/hook.json\nHAR → evidence/network/raw.har\n"
    hits = _direct_raw_network_paths(unsafe)
    check(len(hits) == 2, f"direct raw network detector missed fixture: {hits}")


def test_runtime_network_commands_from_out_cwd() -> None:
    for label, skill_path in (("agents", AGENTS), ("claude", CLAUDE)):
        block = runtime_network_block(skill_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="svc-benchmark-out-") as out_raw:
            with tempfile.TemporaryDirectory(prefix="svc-benchmark-network-") as capture_raw:
                out = Path(out_raw)
                raw_dir = Path(capture_raw)
                raw_input = raw_dir / "raw.json"
                raw_input.write_text(
                    json.dumps(
                        [
                            {
                                "method": "GET",
                                "url": "https://example.test/status?token=fixture-value",
                                "status": 200,
                                "ttfb_ms": 5,
                                "total_ms": 8,
                            }
                        ]
                    ),
                    encoding="utf-8",
                )
                env = os.environ.copy()
                env.update(
                    {
                        "PROJECT_ROOT": str(REPO),
                        "SKILL": str(HERE.parent),
                        "RAW_TMP_DIR": str(raw_dir),
                        "RAW_INPUT": str(raw_input),
                    }
                )
                run = subprocess.run(
                    ["bash", "-eu", "-c", block],
                    cwd=out,
                    env=env,
                    capture_output=True,
                    text=True,
                )
                check(
                    run.returncode == 0,
                    f"{label} runtime commands failed from OUT cwd: "
                    f"stdout={run.stdout!r} stderr={run.stderr!r}",
                )
                session = out / "evidence/network/session.json"
                summary = out / "evidence/network/summary.json"
                runtime = out / "notes/runtime.md"
                check(session.is_file(), f"{label} runtime commands did not create session.json")
                check(summary.is_file(), f"{label} runtime commands did not create summary.json")
                check(runtime.is_file(), f"{label} runtime commands did not create runtime.md")
                check(raw_input.is_file(), f"{label} runtime commands moved the external raw input")
                check(
                    not any(_direct_raw_network_paths(path.as_posix()) for path in out.rglob("*")),
                    f"{label} runtime commands created a package-local raw path",
                )
                if session.is_file():
                    session_text = session.read_text(encoding="utf-8")
                    check("fixture-value" not in session_text, f"{label} session retained a raw value")


def _safety_allow_sections(safety: str) -> str:
    read_only = safety.split("허용 (무승인 read-only):", 1)[-1].split("기본 mutation", 1)[0]
    gated = safety.split("정확한 액션이 있을 때만 실행한다.", 1)[-1]
    return read_only + gated.split("대표 시도", 1)[0]


def _safety_allow_conflicts(safety: str) -> list[str]:
    allowed = _safety_allow_sections(safety)
    patterns = (
        ("메시지·채팅", r"메시지|채팅"),
        ("결제", r"결제"),
        ("로그아웃", r"로그아웃"),
        ("Reset", r"\bReset\b"),
        ("새 worktree", r"새\s+worktree"),
        ("파괴적 작업", r"파괴적\s+작업"),
        ("가입·권한 변경", r"가입|권한\s+변경"),
        ("우회", r"(?:인증|캡차|WAF)\s+우회"),
        (
            "제품 삭제",
            r"(?m)^-\s*(?:삭제|(?:사용자|제품|계정|파일|데이터)\S*\s+(?:를\s+)?삭제)",
        ),
    )
    return [label for label, pattern in patterns if re.search(pattern, allowed)]


def _product_attempt_conflicts(modules: str) -> list[str]:
    attempts = modules.split("## 공통 실제 시도", 1)[-1]
    return [item for item in ("메시지", "채팅") if item in attempts]


def test_safety_contract() -> None:
    safety = (HERE.parent / "references" / "safety.md").read_text(encoding="utf-8")
    modules = (HERE.parent / "references" / "product-modules.md").read_text(encoding="utf-8")
    check("무조건 금지" in safety, "safety.md missing unconditional header")
    check("mutations_allowed`로도 허용하지 않는다" in safety, "safety.md missing no-override")
    for item in ("메시지 전송", "결제", "로그아웃", "삭제", "Reset", "파괴적 작업", "새 worktree"):
        check(item in safety, f"safety.md missing forbid item: {item}")
    ro = safety.split("허용 (무승인 read-only):", 1)[-1].split("기본 mutation", 1)[0]
    check("공식 설치" not in ro, "official install still listed as no-approval read-only")
    gated = safety.split("정확한 액션이 있을 때만 실행한다.", 1)[-1]
    check("공식 설치" in gated.split("대표 시도", 1)[0], "official install missing from gated list")
    check(
        not _safety_allow_conflicts(safety),
        f"safety hard-ban appears in an allow section: {_safety_allow_conflicts(safety)}",
    )
    check(
        not _product_attempt_conflicts(modules),
        f"product module permits hard-ban attempt: {_product_attempt_conflicts(modules)}",
    )
    for label, path in (("agents", AGENTS), ("claude", CLAUDE)):
        text = path.read_text(encoding="utf-8")
        check(
            "승인이나 `mutations_allowed`로도 허용하지 않는다" in text,
            f"{label} missing unconditional forbid",
        )
        check("공식 설치로 올린다" not in text, f"{label} still instructs install-before-gates")
        check(
            "둘 다 있기 전에는 지시하지 않는다" in text,
            f"{label} step 7 missing both-gates install wording",
        )


def test_hard_ban_reappearance_fixture() -> None:
    safety = (HERE.parent / "references" / "safety.md").read_text(encoding="utf-8")
    modules = (HERE.parent / "references" / "product-modules.md").read_text(encoding="utf-8")
    unsafe_safety = safety.replace("- 공개 GET", "- 공개 GET\n- 메시지 전송", 1)
    unsafe_modules = modules.replace(
        "- 검색/읽기 전용 데모/상태 조회 중 공개된 것",
        "- 검색/읽기 전용 데모/상태 조회 중 공개된 것\n- 채팅",
        1,
    )
    check(
        "메시지·채팅" in _safety_allow_conflicts(unsafe_safety),
        "synthetic safety hard-ban conflict was not detected",
    )
    check(
        "채팅" in _product_attempt_conflicts(unsafe_modules),
        "synthetic product attempt conflict was not detected",
    )


def main() -> int:
    test_step12_has_live_paths()
    test_shared_paths_resolve()
    test_e2e_from_out_cwd()
    test_dual_tree_semantic_parity()
    test_all_local_links_exist()
    test_network_document_contract()
    test_direct_raw_network_regression_fixture()
    test_runtime_network_commands_from_out_cwd()
    test_safety_contract()
    test_hard_ban_reappearance_fixture()
    if FAILURES:
        print("FAIL")
        for item in FAILURES:
            print("-", item)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
