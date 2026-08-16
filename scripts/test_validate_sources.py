#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_sources: generic ledger and D-form URL contract."""
from __future__ import annotations

import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_sources import (  # noqa: E402
    CURRENCY_RE,
    catalog_matches_paragraph,
    currency_errors,
    main as sources_main,
    named_source_catalog,
    report_cited_urls,
    source_errors,
    token_in_text,
    url_has_userinfo,
    url_host,
)

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def dform(urls: list[str], label: str = "x") -> str:
    return dform_items([(label, url) for url in urls])


def dform_items(items: list[tuple[str, str]]) -> str:
    lines = ["## 23. 참고 자료", ""]
    for label, url in items:
        lines.append(f"- **{label}** — [{url}]({url})<br><i>함의: t.</i>")
    return "\n".join(lines) + "\n"


def test_arbitrary_service_positive() -> None:
    urls = ["https://example.test/docs", "https://example.test/pricing"]
    check(report_cited_urls(dform(urls)) == urls, "D-form parse changed")
    errs = source_errors(dform(urls), {"cited": urls})
    check(not errs, f"generic cited ledger should pass: {errs}")


def test_fallback_primary_secondary_positive() -> None:
    urls = ["https://example.test/docs", "https://news.example.test/item"]
    doc = {"primary": [urls[0]], "secondary": [urls[1]]}
    errs = source_errors(dform(urls), doc)
    check(not errs, f"primary+secondary fallback should pass: {errs}")


def test_declared_empty_cited_fails_closed() -> None:
    errs = source_errors(dform(["https://example.test/docs"]), {"cited": []})
    check(any("empty source ledger" in error for error in errs), f"empty cited FN: {errs}")


def test_missing_and_extra_fail() -> None:
    report = ["https://example.test/report"]
    ledger = ["https://example.test/ledger"]
    errs = source_errors(dform(report), {"cited": ledger})
    check(any("missing report" in error for error in errs), f"missing FN: {errs}")
    check(any("extra vs report" in error for error in errs), f"extra FN: {errs}")


def test_duplicates_fail_both_sides() -> None:
    url = "https://example.test/docs"
    report_errs = source_errors(dform([url, url]), {"cited": [url, "https://example.test/other"]})
    check(any("duplicate report" in error for error in report_errs), f"report duplicate FN: {report_errs}")
    ledger_errs = source_errors(dform([url, "https://example.test/other"]), {"cited": [url, url]})
    check(any("duplicate source" in error for error in ledger_errs), f"ledger duplicate FN: {ledger_errs}")


def test_invalid_ledger_url_fails() -> None:
    errs = source_errors("", {"cited": ["not-a-url"]})
    check(any("invalid URL" in error for error in errs), f"invalid URL FN: {errs}")


def test_named_source_currency_without_url_fails() -> None:
    url = "https://example.test/docs"
    md = "VentureBeat 제목은 Cursor Ultra 월 200달러를 적는다.\n\n" + dform([url])
    errs = source_errors(md, {"cited": [url]})
    check(any("named-source" in error for error in errs), f"currency FN: {errs}")
    only = currency_errors("VentureBeat says Ultra is $200 a month.\n", {"cited": [url]})
    check(len(only) == 1, f"currency_errors expected 1: {only}")


def test_arbitrary_named_source_currency_positive() -> None:
    url = "https://examplenews.test/price"
    md = (
        f"ExampleNews lists the seat at $120 a month. {url}\n\n"
        + dform([url], label="ExampleNews")
    )
    doc = {
        "cited": [url],
        "named": [{"label": "ExampleNews", "hosts": ["examplenews.test"]}],
    }
    errs = source_errors(md, doc)
    check(not errs, f"arbitrary named source with matching host should pass: {errs}")


def test_wired_currency_without_source_fails() -> None:
    url = "https://example.test/docs"
    md = "Wired put the seat at $999 a month.\n\n" + dform([url])
    errs = source_errors(md, {"cited": [url]})
    check(any("named-source" in error for error in errs), f"Wired FN: {errs}")


def test_wired_hangul_particle_and_amount_forms() -> None:
    url = "https://example.test/docs"
    doc = {"cited": [url]}
    check(CURRENCY_RE.search("월 987달러라고 적는다.") is not None, "987달러라고 miss")
    check(CURRENCY_RE.search("좌석이 $987이라고 적는다.") is not None, "$987이라고 miss")
    for body in (
        "Wired는 좌석을 987달러라고 적는다.",
        "Wired는 좌석이 $987이라고 적는다.",
    ):
        errs = currency_errors(body + "\n\n" + dform([url]), doc)
        check(errs, f"Wired는 FN: {body} {errs}")
    check(CURRENCY_RE.search("Wired는 온디맨드 $0만 적는다.") is None, "$0 still excluded")
    check(CURRENCY_RE.search("Wired는 온디맨드 $0.00만 적는다.") is None, "$0.00 still excluded")
    check(CURRENCY_RE.search("인수 보도 약 600억 달러.") is None, "eok-dollar still excluded")
    check(CURRENCY_RE.search("Wired는 좌석을 $0.99라고 적는다.") is not None, "$0.99 miss")
    check(CURRENCY_RE.search("Wired는 좌석을 $10.50라고 적는다.") is not None, "$10.50 miss")
    check(CURRENCY_RE.search("Wired는 좌석을 $1,234.50라고 적는다.") is not None, "$1,234.50 miss")
    check(CURRENCY_RE.search("Wired는 좌석을 5달러라고 적는다.") is not None, "5달러 miss")
    check(CURRENCY_RE.search("Wired는 좌석을 0.01달러라고 적는다.") is not None, "0.01달러 miss")
    check(CURRENCY_RE.search("Wired는 좌석을 0.99달러라고 적는다.") is not None, "0.99달러 miss")
    check(CURRENCY_RE.search("Wired는 좌석을 1,234달러라고 적는다.") is not None, "1,234달러 miss")
    check(CURRENCY_RE.search("Wired는 온디맨드 0달러만 적는다.") is None, "0달러 still excluded")
    check(CURRENCY_RE.search("Wired는 온디맨드 0.00달러만 적는다.") is None, "0.00달러 still excluded")
    check(CURRENCY_RE.search("1,23달러") is None, "invalid 1,23 comma")
    check(CURRENCY_RE.search("12,34달러") is None, "invalid 12,34 comma")


def _amount_match(text: str) -> str | None:
    match = CURRENCY_RE.search(text)
    return match.group(0) if match else None


def test_trailing_punct_zero_excluded_and_decimals_whole() -> None:
    check(_amount_match("$0,") is None, "$0, matched")
    check(_amount_match("$0.00,") is None, "$0.00, matched")
    check(_amount_match("0달러,") is None, "0달러, matched")
    check(_amount_match("0.00달러,") is None, "0.00달러, matched")
    check(_amount_match("$0.99,") == "$0.99", f"$0.99, got {_amount_match('$0.99,')!r}")
    check(_amount_match("$10.50,") == "$10.50", f"$10.50, got {_amount_match('$10.50,')!r}")
    check(_amount_match("$1,234.50,") == "$1,234.50", f"$1,234.50, got {_amount_match('$1,234.50,')!r}")
    check(_amount_match("0.01달러,") == "0.01달러", f"0.01달러, got {_amount_match('0.01달러,')!r}")
    check(_amount_match("1,234.50달러,") == "1,234.50달러", f"1,234.50달러, got {_amount_match('1,234.50달러,')!r}")
    check(_amount_match("$1,23,") is None, "malformed $1,23, matched")
    url = "https://example.test/docs"
    md = "The meter is $0.00, with no seat price.\n\n" + dform([url])
    errs = source_errors(md, {"cited": [url]})
    check(not errs, f"zero with comma should not trip currency: {errs}")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "report").mkdir()
        (root / "notes").mkdir()
        report = root / "report" / "report.md"
        sources = root / "notes" / "sources.json"
        report.write_text(md, encoding="utf-8")
        sources.write_text(json.dumps({"cited": [url]}), encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = sources_main(["--report", str(report), "--sources", str(sources)])
    check(code == 0, f"CLI $0.00, should pass: exit={code}")


def test_no_implicit_first_word_alias() -> None:
    url = "https://examplenews.test/price"
    md = f"ExampleNews lists the seat at $120. {url}\n\n" + dform([url], label="Docs")
    doc = {"cited": [url], "named": [{"label": "ExampleNews Daily", "hosts": ["examplenews.test"]}]}
    labels = named_source_catalog(md, doc)[0]["labels"] if named_source_catalog(md, doc) else set()
    check("ExampleNews" not in labels, f"implicit first-word alias: {labels}")
    errs = currency_errors(md, doc)
    check(errs, f"first-word alias must not match: {errs}")


def test_explicit_alias_positive() -> None:
    url = "https://examplenews.test/price"
    md = f"ENWire lists the seat at $120. {url}\n\n" + dform([url], label="Docs")
    doc = {
        "cited": [url],
        "named": [{"label": "ExampleNews", "aliases": ["ENWire"], "hosts": ["examplenews.test"]}],
    }
    errs = source_errors(md, doc)
    check(not errs, f"explicit alias should pass: {errs}")


def test_partial_label_news_does_not_match_badnews() -> None:
    url = "https://news.test/price"
    md = f"BadNews lists the seat at $120. {url}\n\n" + dform([url], label="Docs")
    doc = {"cited": [url], "named": [{"label": "News", "hosts": ["news.test"]}]}
    check(not token_in_text("News", "BadNews lists the seat"), "News matched inside BadNews")
    errs = currency_errors(md, doc)
    check(any("named-source" in error for error in errs), f"BadNews should stay unregistered: {errs}")


def test_cross_host_alpha_beta_fails() -> None:
    alpha = "https://alphanews.test/a"
    beta = "https://betanews.test/b"
    md = (
        f"AlphaNews and BetaNews both list $120. {beta}\n\n"
        + dform_items([("AlphaNews", alpha), ("BetaNews", beta)])
    )
    doc = {
        "cited": [alpha, beta],
        "named": [
            {"label": "AlphaNews", "hosts": ["alphanews.test"]},
            {"label": "BetaNews", "hosts": ["betanews.test"]},
        ],
    }
    errs = source_errors(md, doc)
    check(any("missing own host/url" in error for error in errs), f"cross-host FN: {errs}")


def test_cross_host_both_urls_positive() -> None:
    alpha = "https://alphanews.test/a"
    beta = "https://betanews.test/b"
    md = (
        f"AlphaNews and BetaNews both list $120. {alpha} {beta}\n\n"
        + dform_items([("AlphaNews", alpha), ("BetaNews", beta)])
    )
    doc = {
        "cited": [alpha, beta],
        "named": [
            {"label": "AlphaNews", "hosts": ["alphanews.test"]},
            {"label": "BetaNews", "hosts": ["betanews.test"]},
        ],
    }
    errs = source_errors(md, doc)
    check(not errs, f"both hosts should pass: {errs}")


def test_venturebeat_unrelated_host_fails() -> None:
    cited = "https://venturebeat.com/article"
    md = (
        "VentureBeat says Ultra is $200 a month. https://example.test/unrelated\n\n"
        + dform([cited], label="VentureBeat")
    )
    doc = {
        "cited": [cited],
        "named": [{"label": "VentureBeat", "hosts": ["venturebeat.com"]}],
    }
    errs = source_errors(md, doc)
    check(any("missing own host/url" in error for error in errs), f"unrelated host FN: {errs}")


def test_host_default_port_and_rejects() -> None:
    good = "https://examplenews.test/price"
    entry = {"labels": {"ExampleNews"}, "hosts": {"examplenews.test"}, "urls": {good}}
    check(url_host(good) == "examplenews.test", url_host(good))
    check(url_host("https://examplenews.test:443/price") == "examplenews.test", "https default port")
    check(url_host("http://examplenews.test:80/price") == "examplenews.test", "http default port")
    check(catalog_matches_paragraph(entry, ["https://examplenews.test:443/price"]), "port 443 should match")
    check(url_host("https://examplenews.test@evil.com/price") == "", "userinfo spoof")
    check(url_host("https://evil@examplenews.test/price") == "", "userinfo on good host")
    check(not catalog_matches_paragraph(entry, ["https://examplenews.test@evil.com/price"]), "userinfo must not match")
    check(url_host("https://news.examplenews.test/price") == "news.examplenews.test", "subdomain host")
    check(not catalog_matches_paragraph(entry, ["https://news.examplenews.test/price"]), "subdomain must not match")
    check(not catalog_matches_paragraph(entry, ["https://example.test/docs"]), "other host must not match")
    check(url_host("https://www.trusted.test/x") == "www.trusted.test", "www stays on hostname")
    bare_hosts = {"labels": {"N"}, "hosts": {"trusted.test"}, "urls": set()}
    www_hosts = {"labels": {"N"}, "hosts": {"www.trusted.test"}, "urls": set()}
    check(not catalog_matches_paragraph(bare_hosts, ["https://www.trusted.test/x"]), "www URL vs bare host")
    check(catalog_matches_paragraph(www_hosts, ["https://www.trusted.test/x"]), "www URL vs www host")
    check(not catalog_matches_paragraph(www_hosts, ["https://trusted.test/x"]), "bare URL vs www host")


def test_userinfo_direct_match_rejected_both_sides() -> None:
    spoof = "https://trusted.test@evil.test/x"
    check(url_has_userinfo(spoof), "spoof should have userinfo")
    entry = {"labels": {"TrustedNews"}, "hosts": {"trusted.test"}, "urls": {spoof}}
    check(not catalog_matches_paragraph(entry, [spoof]), "direct same spoof must not match")
    md = dform([spoof], label="TrustedNews")
    doc = {"cited": [spoof], "named": [{"label": "TrustedNews", "hosts": ["trusted.test"]}]}
    errs = source_errors(md, doc)
    check(any("userinfo" in error for error in errs), f"ledger+D-form spoof FN: {errs}")
    check(not any("trusted.test@" in error or "evil.test" in error for error in errs), f"userinfo leaked: {errs}")
    body = f"TrustedNews lists the seat at $120. {spoof}\n\n" + md
    body_errs = source_errors(body, doc)
    check(any("userinfo" in error for error in body_errs), f"body+ledger spoof FN: {body_errs}")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "report").mkdir()
        (root / "notes").mkdir()
        report = root / "report" / "report.md"
        sources = root / "notes" / "sources.json"
        report.write_text(md, encoding="utf-8")
        sources.write_text(json.dumps(doc), encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = sources_main(["--report", str(report), "--sources", str(sources)])
    check(code != 0, f"CLI same spoof should fail: exit={code}")


def test_cli_korean_five_dollar_wrong_host_fails() -> None:
    url = "https://example.test/docs"
    md = "Wired는 좌석을 5달러라고 적는다.\n\n" + dform([url])
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "report").mkdir()
        (root / "notes").mkdir()
        report = root / "report" / "report.md"
        sources = root / "notes" / "sources.json"
        report.write_text(md, encoding="utf-8")
        sources.write_text(json.dumps({"cited": [url]}), encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = sources_main(["--report", str(report), "--sources", str(sources)])
    check(code != 0, f"CLI 5달러 other-host should fail: exit={code}")


def test_cli_decimal_wrong_host_fails() -> None:
    url = "https://example.test/docs"
    md = "Wired lists the seat at $0.99 a month.\n\n" + dform([url])
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "report").mkdir()
        (root / "notes").mkdir()
        report = root / "report" / "report.md"
        sources = root / "notes" / "sources.json"
        report.write_text(md, encoding="utf-8")
        sources.write_text(json.dumps({"cited": [url]}), encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = sources_main(["--report", str(report), "--sources", str(sources)])
    check(code != 0, f"CLI $0.99 other-host should fail: exit={code}")
    errs = source_errors(md, {"cited": [url]})
    check(any("named-source" in error for error in errs), f"decimal FN: {errs}")


def test_live_package() -> None:
    root = HERE.parents[4] / "data/research/20260814_grok-bot"
    report = root / "report/report.md"
    sources = root / "notes/sources.json"
    if not report.exists() or not sources.exists():
        return
    md = report.read_text(encoding="utf-8")
    doc = json.loads(sources.read_text(encoding="utf-8"))
    errs = source_errors(md, doc)
    check(not errs, f"live sources FAIL: {errs}")
    check(len(report_cited_urls(md)) == 14, "live source count is not 14")


def main() -> int:
    test_arbitrary_service_positive()
    test_fallback_primary_secondary_positive()
    test_declared_empty_cited_fails_closed()
    test_missing_and_extra_fail()
    test_duplicates_fail_both_sides()
    test_invalid_ledger_url_fails()
    test_named_source_currency_without_url_fails()
    test_arbitrary_named_source_currency_positive()
    test_wired_currency_without_source_fails()
    test_wired_hangul_particle_and_amount_forms()
    test_trailing_punct_zero_excluded_and_decimals_whole()
    test_no_implicit_first_word_alias()
    test_explicit_alias_positive()
    test_partial_label_news_does_not_match_badnews()
    test_cross_host_alpha_beta_fails()
    test_cross_host_both_urls_positive()
    test_venturebeat_unrelated_host_fails()
    test_host_default_port_and_rejects()
    test_userinfo_direct_match_rejected_both_sides()
    test_cli_korean_five_dollar_wrong_host_fails()
    test_cli_decimal_wrong_host_fails()
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
