#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_privacy: exact exceptions, redactions, and email allowlist."""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_privacy import main as privacy_main, privacy_errors  # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def _config(**changes: object) -> dict:
    config: dict = {
        "html": [{"path": "evidence/docs/nested/source.html", "reason": "제3자 원문"}],
        "allowed_emails": [],
        "forbidden_paths": ["evidence/screenshots/private.png"],
        "redactions": [
            {
                "path": "evidence/docs/redacted.txt",
                "markers": ["[MASKED_NAME]", "[MASKED_EMAIL]"],
            }
        ],
    }
    config.update(changes)
    return config


def _write_config(root: Path, **changes: object) -> None:
    config = _config(**changes)
    (root / "notes/privacy-exceptions.json").write_text(json.dumps(config), encoding="utf-8")


def _pkg(root: Path) -> Path:
    for name in ("notes", "report", "review", "sources", "evidence/docs/nested", "evidence/screenshots"):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / "evidence/docs/nested/source.html").write_text(
        "<html>thirdparty@private.test</html>", encoding="utf-8"
    )
    (root / "evidence/docs/redacted.txt").write_text(
        "[MASKED_NAME]\n[MASKED_EMAIL]\n", encoding="utf-8"
    )
    _write_config(root)
    return root


def run_case(mutator=None) -> list[str]:
    with tempfile.TemporaryDirectory() as raw:
        root = _pkg(Path(raw))
        if mutator:
            mutator(root)
        return privacy_errors(root)


def test_explicit_example_addresses_pass() -> None:
    def mutate(root: Path) -> None:
        _write_config(
            root,
            allowed_emails=["first@example.com", "second@example.org"],
        )
        (root / "notes/examples.txt").write_text(
            "first@example.com second@example.org\n", encoding="utf-8"
        )

    errors = run_case(mutate)
    check(not errors, f"listed examples should pass: {errors}")


def test_unlisted_example_address_fails_without_echo() -> None:
    def mutate(root: Path) -> None:
        (root / "notes/leak.txt").write_text("arbitrary@example.com\n", encoding="utf-8")

    errors = run_case(mutate)
    check(any("personal email pattern" in error for error in errors), f"example-domain FN: {errors}")
    check(not any("arbitrary@" in error for error in errors), f"error leaked address: {errors}")


def test_product_domains_are_not_blanket_allowed() -> None:
    for domain in ("x.ai", "cursor.com", "apple.com"):
        def mutate(root: Path, suffix: str = domain) -> None:
            (root / "notes/leak.txt").write_text(f"person@{suffix}\n", encoding="utf-8")

        errors = run_case(mutate)
        check(any("personal email pattern" in error for error in errors), f"domain allow FN {domain}: {errors}")


def test_exact_allowed_email_passes() -> None:
    def mutate(root: Path) -> None:
        _write_config(root, allowed_emails=["allowed@vendor.test"])
        (root / "notes/contact.txt").write_text("allowed@vendor.test\n", encoding="utf-8")

    errors = run_case(mutate)
    check(not errors, f"exact allowed email should pass: {errors}")


def test_allowlist_entry_must_already_be_lowercase() -> None:
    def mutate(root: Path) -> None:
        _write_config(root, allowed_emails=["Allowed@vendor.test"])
        (root / "notes/contact.txt").write_text("allowed@vendor.test\n", encoding="utf-8")

    errors = run_case(mutate)
    check(any("exact lowercased address" in error for error in errors), f"lowercase contract FN: {errors}")
    check(any("personal email pattern" in error for error in errors), f"uppercase allow bypass: {errors}")


def test_unlisted_email_fails_without_echoing_value() -> None:
    def mutate(root: Path) -> None:
        (root / "notes/leak.txt").write_text("person@private.test\n", encoding="utf-8")

    errors = run_case(mutate)
    check(any("personal email pattern" in error for error in errors), f"email FN: {errors}")
    check(not any("person@" in error for error in errors), f"error leaked address: {errors}")


def test_published_html_email_fails_without_echoing_value() -> None:
    def mutate(root: Path) -> None:
        (root / "report/report.html").write_text(
            "<html>private.person@internal.test</html>\n", encoding="utf-8"
        )

    errors = run_case(mutate)
    check(any("personal email pattern in report/report.html" in error for error in errors), f"HTML email FN: {errors}")
    check(not any("private.person@" in error for error in errors), f"HTML error leaked address: {errors}")


def test_uppercase_html_actual_ledger_and_body_checks() -> None:
    def unlisted(root: Path) -> None:
        (root / "evidence/docs/EXTRA.HTML").write_text("<html>source</html>", encoding="utf-8")

    errors = run_case(unlisted)
    check(any("unlisted third-party html" in error for error in errors), f"uppercase actual-set FN: {errors}")

    def listed(root: Path) -> None:
        (root / "evidence/docs/SOURCE.HTML").write_text("<html>source</html>", encoding="utf-8")
        _write_config(
            root,
            html=[
                {"path": "evidence/docs/nested/source.html", "reason": "원문"},
                {"path": "evidence/docs/SOURCE.HTML", "reason": "원문"},
            ],
        )

    errors = run_case(listed)
    check(not errors, f"listed uppercase HTML should pass: {errors}")

    secret = "uppercase.html@internal.test"

    def published_body(root: Path) -> None:
        (root / "report/REPORT.HTML").write_text(f"<html>{secret}</html>", encoding="utf-8")

    errors = run_case(published_body)
    check(
        any("personal email pattern in report/REPORT.HTML" in error for error in errors),
        f"uppercase HTML body FN: {errors}",
    )
    check(not any(secret in error for error in errors), f"uppercase HTML error leaked a value: {errors}")


def test_recursive_html_exact_set() -> None:
    def unlisted(root: Path) -> None:
        (root / "evidence/docs/deeper").mkdir()
        (root / "evidence/docs/deeper/extra.html").write_text("x", encoding="utf-8")

    errors = run_case(unlisted)
    check(any("unlisted third-party html" in error for error in errors), f"recursive html FN: {errors}")

    def missing(root: Path) -> None:
        _write_config(
            root,
            html=[
                {"path": "evidence/docs/nested/source.html", "reason": "원문"},
                {"path": "evidence/docs/nested/missing.html", "reason": "원문"},
            ],
        )

    errors = run_case(missing)
    check(any("html exception file missing" in error for error in errors), f"listed missing FN: {errors}")


def test_html_path_and_reason_fail_closed() -> None:
    def outside(root: Path) -> None:
        _write_config(root, html=[{"path": "report/not-evidence.html", "reason": "원문"}])

    errors = run_case(outside)
    check(any("inside evidence/docs" in error for error in errors), f"outside html FN: {errors}")

    def blank_reason(root: Path) -> None:
        _write_config(root, html=[{"path": "evidence/docs/nested/source.html", "reason": ""}])

    errors = run_case(blank_reason)
    check(any("missing reason" in error for error in errors), f"reason FN: {errors}")


def test_forbidden_presence_and_embed_fail() -> None:
    def present(root: Path) -> None:
        (root / "evidence/screenshots/private.png").write_bytes(b"x")

    errors = run_case(present)
    check(any("forbidden path present" in error for error in errors), f"presence FN: {errors}")

    def embed(root: Path) -> None:
        (root / "report/report.md").write_text(
            "![비공개](../evidence/screenshots/private.png)\n", encoding="utf-8"
        )

    errors = run_case(embed)
    check(any("report embeds forbidden" in error for error in errors), f"embed FN: {errors}")


def test_redaction_file_and_markers_required() -> None:
    def missing_marker(root: Path) -> None:
        (root / "evidence/docs/redacted.txt").write_text("[MASKED_NAME]\n", encoding="utf-8")

    errors = run_case(missing_marker)
    check(any("markers absent" in error for error in errors), f"marker FN: {errors}")

    def missing_file(root: Path) -> None:
        _write_config(
            root,
            redactions=[{"path": "evidence/docs/not-there.txt", "markers": ["[MASKED]"]}],
        )

    errors = run_case(missing_file)
    check(any("redaction file missing" in error for error in errors), f"redaction file FN: {errors}")


def test_missing_ledger_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        (root / "notes").mkdir()
        errors = privacy_errors(root)
    check(any("ledger missing" in error for error in errors), f"missing ledger FN: {errors}")


def test_each_required_ledger_key_fails_closed() -> None:
    for missing_key in ("html", "allowed_emails", "forbidden_paths", "redactions"):
        def mutate(root: Path, key: str = missing_key) -> None:
            config = _config()
            config.pop(key)
            (root / "notes/privacy-exceptions.json").write_text(
                json.dumps(config), encoding="utf-8"
            )

        errors = run_case(mutate)
        check(
            any("missing required keys" in error and missing_key in error for error in errors),
            f"missing required key accepted: {missing_key}",
        )


def test_network_secret_classes_fail_without_echo() -> None:
    cases = (
        (
            "query",
            [{"url": "https://api.example.test/status?token=query-secret-123"}],
            "query-secret-123",
        ),
        (
            "header",
            [{"requestHeaders": "Authorization: Bearer header-secret-123"}],
            "header-secret-123",
        ),
        (
            "body",
            [{"body": "token: body-secret-123"}],
            "body-secret-123",
        ),
    )
    for label, document, secret in cases:
        def mutate(root: Path, doc: object = document) -> None:
            network = root / "evidence/network"
            network.mkdir(parents=True, exist_ok=True)
            (network / "leak.json").write_text(json.dumps(doc), encoding="utf-8")

        errors = run_case(mutate)
        check(
            any("unsanitized secret material" in error for error in errors),
            f"network {label} secret accepted: {errors}",
        )
        check(not any(secret in error for error in errors), f"network {label} error leaked a value")


def test_network_userinfo_fails_without_echo() -> None:
    secrets = ("name-SECRET-001", "ui-SECRET-000")

    def mutate(root: Path) -> None:
        network = root / "evidence/network"
        network.mkdir(parents=True, exist_ok=True)
        document = [{"url": f"https://{secrets[0]}:{secrets[1]}@[2001:db8::1]:8443/a"}]
        (network / "leak.json").write_text(json.dumps(document), encoding="utf-8")

    with tempfile.TemporaryDirectory() as raw:
        root = _pkg(Path(raw))
        mutate(root)
        errors = privacy_errors(root)
        output = StringIO()
        with redirect_stdout(output):
            result = privacy_main(["--root", str(root)])
    check(result != 0, "privacy CLI accepted URL userinfo")
    check(
        any("unsanitized secret material" in error for error in errors),
        f"URL userinfo was not reported: {errors}",
    )
    check(
        all(secret not in "\n".join(errors) for secret in secrets),
        "privacy errors exposed URL userinfo",
    )
    check(
        all(secret not in output.getvalue() for secret in secrets),
        "privacy CLI exposed URL userinfo",
    )


def test_sanitized_network_artifact_passes() -> None:
    def mutate(root: Path) -> None:
        network = root / "evidence/network"
        network.mkdir(parents=True, exist_ok=True)
        document = [
            {
                "url": "https://api.example.test/status",
                "request": {
                    "headers": [
                        {"name": "Authorization", "value": "[REDACTED]"},
                        {"name": "Accept", "value": "application/json"},
                    ],
                    "postData": {"text": "{\"token\":\"[REDACTED]\"}"},
                },
            }
        ]
        (network / "session.json").write_text(json.dumps(document), encoding="utf-8")
        (network / "summary.json").write_text(
            json.dumps({"count": 1, "entries": []}), encoding="utf-8"
        )

    errors = run_case(mutate)
    check(not errors, f"documented sanitized network artifacts rejected: {errors}")


def test_network_jsonl_is_checked_line_by_line_without_echo() -> None:
    secret = "jsonl-secret-value"

    def mutate(root: Path) -> None:
        network = root / "evidence/network"
        network.mkdir(parents=True, exist_ok=True)
        rows = [
            {"url": "https://api.example.test/status"},
            {"requestHeaders": f"Authorization: Bearer {secret}"},
        ]
        (network / "trace.JSONL").write_text(
            "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
        )

    errors = run_case(mutate)
    check(any("unsanitized secret material" in error for error in errors), f"JSONL secret accepted: {errors}")
    check(not any(secret in error for error in errors), f"JSONL error leaked a value: {errors}")

    def invalid(root: Path) -> None:
        network = root / "evidence/network"
        network.mkdir(parents=True, exist_ok=True)
        (network / "trace.jsonl").write_text('{"ok": true}\n{"broken":\n', encoding="utf-8")

    errors = run_case(invalid)
    check(any("not valid JSONL at line 2" in error for error in errors), f"invalid JSONL accepted: {errors}")
    check(not any("broken" in error for error in errors), f"JSONL parse error exposed content: {errors}")


def test_raw_and_hook_network_artifacts_fail_regardless_of_content() -> None:
    def mutate(root: Path) -> None:
        network = root / "evidence/network"
        network.mkdir(parents=True, exist_ok=True)
        (network / "raw.json").write_text("[]\n", encoding="utf-8")
        (network / "HOOK.JSON").write_text("[]\n", encoding="utf-8")

    errors = run_case(mutate)
    check(
        any("forbidden raw network artifact: evidence/network/raw.json" in error for error in errors),
        f"raw.json accepted: {errors}",
    )
    check(
        any("forbidden raw network artifact: evidence/network/HOOK.JSON" in error for error in errors),
        f"hook.json accepted case-insensitively: {errors}",
    )


def test_mixed_case_raw_har_fails_without_echo() -> None:
    secret = "mixed-case-header-value"
    document = {
        "log": {
            "entries": [
                {
                    "request": {
                        "url": "https://api.example.test/status",
                        "headers": [{"NaMe": "Authorization", "VaLuE": secret}],
                    },
                    "response": {"status": 200, "headers": []},
                }
            ]
        }
    }
    with tempfile.TemporaryDirectory() as raw:
        root = _pkg(Path(raw))
        network = root / "evidence/network"
        network.mkdir(parents=True, exist_ok=True)
        (network / "mixed.har").write_text(json.dumps(document), encoding="utf-8")
        errors = privacy_errors(root)
        output = StringIO()
        with redirect_stdout(output):
            result = privacy_main(["--root", str(root)])
    check(result != 0, "privacy CLI accepted a mixed-case raw HAR")
    check(
        any("unsanitized secret material" in error for error in errors),
        "privacy errors omitted mixed-case HAR finding",
    )
    check(secret not in "\n".join(errors), "privacy error exposed a mixed-case header value")
    check(secret not in output.getvalue(), "privacy CLI exposed a mixed-case header value")


def test_live_package() -> None:
    root = HERE.parents[4] / "data/research/20260814_grok-bot"
    if not root.exists():
        return
    errors = privacy_errors(root)
    check(not errors, f"live privacy FAIL: {errors}")


def main() -> int:
    test_explicit_example_addresses_pass()
    test_unlisted_example_address_fails_without_echo()
    test_product_domains_are_not_blanket_allowed()
    test_exact_allowed_email_passes()
    test_allowlist_entry_must_already_be_lowercase()
    test_unlisted_email_fails_without_echoing_value()
    test_published_html_email_fails_without_echoing_value()
    test_uppercase_html_actual_ledger_and_body_checks()
    test_recursive_html_exact_set()
    test_html_path_and_reason_fail_closed()
    test_forbidden_presence_and_embed_fail()
    test_redaction_file_and_markers_required()
    test_missing_ledger_fails_closed()
    test_each_required_ledger_key_fails_closed()
    test_network_secret_classes_fail_without_echo()
    test_network_userinfo_fails_without_echo()
    test_sanitized_network_artifact_passes()
    test_network_jsonl_is_checked_line_by_line_without_echo()
    test_raw_and_hook_network_artifacts_fail_regardless_of_content()
    test_mixed_case_raw_har_fails_without_echo()
    test_live_package()
    if FAILURES:
        print("FAIL")
        for item in FAILURES:
            print("-", item)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
