#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared recursive sanitizer for HAR and simple network JSON."""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REDACTED = "[REDACTED]"
URL_KEYS = {"url", "href", "uri", "url_effective", "redirecturl"}
HEADER_KEYS = {"headers", "requestheaders", "responseheaders", "req_headers", "res_headers"}
QUERY_KEYS = {"querystring", "queryparams", "query_params"}
COOKIE_KEYS = {"cookies"}
BODY_KEYS = {"body", "requestbody", "responsebody", "postdata", "payload", "content"}
BODY_TEXT_KEYS = {"text"}

JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
BEARER_RE = re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/-]{4,}")
PREFIX_TOKEN_RE = re.compile(r"\b(?:sk|ghp|gho|xox[aboprs])-?[A-Za-z0-9_-]{8,}\b", re.I)
BODY_PAIR_RE = re.compile(
    r"(?i)([\"']?(?:access[_-]?token|refresh[_-]?token|id[_-]?token|token|api[_-]?key|"
    r"client[_-]?secret|secret|password|passwd|authorization|cookie|session(?:[_-]?id)?)[\"']?"
    r"\s*[:=]\s*[\"']?)([^\"',&\s}\]]+)"
)


def _normalized(name: object) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(name).strip().lower()).strip("-")


def _dict_ci_get(item: dict, key: str, default: object = None) -> object:
    target = key.casefold()
    for candidate, value in item.items():
        if str(candidate).casefold() == target:
            return value
    return default


def header_name(item: object) -> str:
    if isinstance(item, dict):
        return str(_dict_ci_get(item, "name", "") or "").strip().lower()
    if isinstance(item, str):
        return item.partition(":")[0].strip().lower()
    return ""


def is_sensitive_header(name: object) -> bool:
    normalized = _normalized(name)
    compact = normalized.replace("-", "")
    return (
        normalized in {
            "authorization",
            "proxy-authorization",
            "cookie",
            "set-cookie",
            "x-api-key",
            "x-auth-token",
            "x-csrf-token",
        }
        or normalized.startswith("x-api-key-")
        or normalized.startswith("set-cookie-")
        or normalized.endswith("-authorization")
        or normalized.endswith("-api-key")
        or any(marker in compact for marker in ("token", "secret", "session"))
    )


def is_sensitive_field(name: object) -> bool:
    normalized = _normalized(name)
    parts = normalized.split("-") if normalized else []
    compact = normalized.replace("-", "")
    return (
        normalized in {"authorization", "cookie", "set-cookie", "password", "passwd", "secret"}
        or compact in {
            "accesstoken",
            "refreshtoken",
            "idtoken",
            "apikey",
            "clientsecret",
            "sessionid",
        }
        or compact.endswith(("token", "secret"))
        or "token" in parts
        or "secret" in parts
        or "password" in parts
        or "passwd" in parts
        or "cookie" in parts
        or "session" in parts
        or ("api" in parts and "key" in parts)
    )


def sanitize_url(value: object) -> object:
    if not isinstance(value, str):
        return value
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    has_userinfo = parsed.username is not None or parsed.password is not None
    if not parsed.query and not parsed.fragment and not has_userinfo:
        return value

    netloc = parsed.netloc
    if has_userinfo:
        hostname = parsed.hostname
        if hostname is None:
            netloc = ""
        else:
            netloc = f"[{hostname}]" if ":" in hostname else hostname
            try:
                port = parsed.port
            except ValueError:
                netloc = parsed.netloc.rsplit("@", 1)[-1]
            else:
                if port is not None:
                    netloc = f"{netloc}:{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))


def _replace_value_fields(item: dict, replacement: object = REDACTED) -> dict:
    out = dict(item)
    found = False
    for key in list(out):
        if str(key).casefold() == "value":
            out[key] = replacement
            found = True
    if not found:
        out["value"] = replacement
    return out


def _sanitize_name_value_list(value: object, *, mode: str) -> object:
    if not isinstance(value, list):
        return _sanitize(value)
    out: list[object] = []
    for item in value:
        if not isinstance(item, dict):
            out.append(_sanitize(item))
            continue
        cleaned = _sanitize(item)
        name = _dict_ci_get(item, "name", "") or ""
        redact = mode in {"query", "cookie"}
        if mode == "header":
            redact = is_sensitive_header(name)
        elif mode == "body":
            redact = is_sensitive_field(name)
        out.append(_replace_value_fields(cleaned) if redact else cleaned)
    return out


def sanitize_headers(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: REDACTED if is_sensitive_header(key) else _sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, str):
        lines = value.splitlines() or [value]
        cleaned: list[str] = []
        for line in lines:
            name, separator, _raw_value = line.partition(":")
            cleaned.append(
                f"{name}: {REDACTED}"
                if separator and is_sensitive_header(name)
                else line
            )
        return "\n".join(cleaned)
    if not isinstance(value, list):
        return _sanitize(value)
    out: list[object] = []
    for item in value:
        if isinstance(item, str):
            name, separator, _raw_value = item.partition(":")
            out.append(f"{name}: {REDACTED}" if separator and is_sensitive_header(name) else item)
        elif isinstance(item, dict):
            cleaned = _sanitize(item)
            name = _dict_ci_get(item, "name", "") or ""
            out.append(_replace_value_fields(cleaned) if is_sensitive_header(name) else cleaned)
        else:
            out.append(_sanitize(item))
    return out


def sanitize_body(value: object) -> object:
    if isinstance(value, dict):
        out: dict = {}
        for key, item in value.items():
            if str(key).lower() == "params":
                out[key] = _sanitize_name_value_list(item, mode="body")
            else:
                out[key] = _sanitize({key: item})[key]
        return out
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if not isinstance(value, str) or value == REDACTED:
        return value

    stripped = value.strip()
    if stripped.startswith(("{", "[")):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, (dict, list)):
            cleaned = _sanitize(decoded)
            if cleaned != decoded:
                return json.dumps(cleaned, ensure_ascii=False, separators=(",", ":"))
            return value

    if "=" in value:
        pairs = parse_qsl(value, keep_blank_values=True)
        if pairs and any(is_sensitive_field(key) for key, _item in pairs):
            encoded = urlencode(
                [(key, REDACTED if is_sensitive_field(key) else item) for key, item in pairs]
            )
            return encoded.replace("%5BREDACTED%5D", REDACTED)

    cleaned = BODY_PAIR_RE.sub(lambda match: match.group(1) + REDACTED, value)
    cleaned = BEARER_RE.sub(lambda match: match.group(1) + REDACTED, cleaned)
    cleaned = JWT_RE.sub(REDACTED, cleaned)
    return PREFIX_TOKEN_RE.sub(REDACTED, cleaned)


def _sanitize_response_content(value: object) -> object:
    """Keep HAR response metadata, but never retain the response body."""
    if isinstance(value, dict):
        return {
            key: REDACTED if str(key).casefold() == "text" else _sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, str):
        return REDACTED
    return _sanitize(value)


def _sanitize_response(value: object) -> object:
    if not isinstance(value, dict):
        return _sanitize(value)
    out = _sanitize(value)
    for key, item in value.items():
        if str(key).casefold() == "content":
            out[key] = _sanitize_response_content(item)
    return out


def _sanitize(value: object) -> object:
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if not isinstance(value, dict):
        return value
    out: dict = {}
    for key, item in value.items():
        lowered = str(key).lower()
        if lowered in URL_KEYS:
            out[key] = sanitize_url(item)
        elif lowered == "response":
            out[key] = _sanitize_response(item)
        elif lowered in HEADER_KEYS:
            out[key] = sanitize_headers(item)
        elif lowered in QUERY_KEYS:
            out[key] = _sanitize_name_value_list(item, mode="query")
        elif lowered in COOKIE_KEYS:
            out[key] = _sanitize_name_value_list(item, mode="cookie")
        elif lowered in BODY_KEYS:
            out[key] = sanitize_body(item)
        elif lowered in BODY_TEXT_KEYS:
            out[key] = sanitize_body(item)
        elif is_sensitive_field(key):
            out[key] = REDACTED
        else:
            out[key] = _sanitize(item)
    return out


def sanitize_network_document(value: object) -> object:
    """Return a detached, recursively sanitized network document."""
    return _sanitize(value)


def contains_unsanitized_network_data(value: object) -> bool:
    """Detect values that the shared sanitizer would change without exposing them."""
    return sanitize_network_document(value) != value


def raw_source_is_temporary(src: Path) -> bool:
    """Return whether a raw capture path resolves below an OS temporary root."""
    roots = {Path(tempfile.gettempdir()).resolve(), Path("/tmp").resolve()}
    configured = os.environ.get("TMPDIR")
    if configured:
        roots.add(Path(configured).resolve())
    resolved = src.resolve()
    return any(resolved == root or root in resolved.parents for root in roots)
