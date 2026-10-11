#!/usr/bin/env python3
"""Read-only external observation of public TYME Hall routes.

This script intentionally DOES NOT certify release gate G1, invoke private APIs,
write to the Hall, modify Cloudflare, or claim an endpoint is secure.
Runs from an internet-capable GitHub Actions runner, not from an internal origin.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPRedirectHandler, HTTPSHandler, Request, build_opener
)

HERE = Path(__file__).resolve().parent
ORIGIN = "https://tymehall.org"
IMMUTABLE = "https://8f2b21b4.codex-interface-83q.pages.dev"
ALLOWED_HOSTS = frozenset(
    {"tymehall.org", "www.tymehall.org", "8f2b21b4.codex-interface-83q.pages.dev"}
)
MAX_BODY = 1024 * 1024
TIMEOUT = 10
TESTS = [
    ("foyer", ORIGIN + "/", "html"),
    ("machine_bootstrap", ORIGIN + "/.well-known/tyme.json", "bootstrap"),
    ("office_state", ORIGIN + "/office/state.json", "office"),
    ("agi_manifest", ORIGIN + "/scrolls/AGI-0001/publication.json", "agi"),
    ("publication_reader", ORIGIN + "/scrolls/AGI-0001/", "html"),
    ("contribution", ORIGIN + "/contribute/", "html"),
    ("cit_learning", ORIGIN + "/projections/cit-learning-v0.1/", "html"),
    ("terminal", ORIGIN + "/terminal/", "html"),
    ("immutable_bootstrap", IMMUTABLE + "/.well-known/tyme.json", "bootstrap"),
    ("immutable_agi", IMMUTABLE + "/scrolls/AGI-0001/publication.json", "agi"),
]


class SafeRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError("Disallowed redirect (non-HTTPS or off allowlist)")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _check_payload(kind: str, body: bytes, mime: str) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    notes: dict = {}
    if kind == "html":
        if not (mime.startswith("text/html") or body.lstrip()[:20].lower().startswith(b"<!doctype html")):
            errors.append("Expected public HTML page")
        return errors, warnings, notes
    if "json" not in mime.lower():
        warnings.append("Unexpected Content-Type for JSON")
    try:
        doc = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        errors.append("Cannot parse public JSON document")
        return errors, warnings, notes
    if not isinstance(doc, dict):
        errors.append("JSON root must be an object")
        return errors, warnings, notes
    if kind == "bootstrap":
        notes["canonical_domain"] = doc.get("canonical_domain")
        if doc.get("canonical_domain") != ORIGIN:
            errors.append("Unexpected machine-bootstrap canonical domain")
        if doc.get("publications", {}).get("first_publication", {}).get("scroll_id") != "AGI-0001":
            errors.append("Bootstrap publication identity mismatch")
    if kind == "office":
        notes["snapshot_id"] = doc.get("snapshot_id")
        notes["generated_at"] = doc.get("generated_at")
        if doc.get("authority_posture") != "non_authorizing":
            errors.append("Public Office authority boundary changed")
        try:
            generated = datetime.fromisoformat(doc["generated_at"].replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - generated).total_seconds() / 86400
            notes["age_days"] = round(age_days, 1)
            if age_days > 14:
                warnings.append("Public Office snapshot is older than 14 days")
        except (TypeError, KeyError, ValueError, AttributeError):
            warnings.append("Office state timestamp not parseable")
    if kind == "agi":
        scroll = doc.get("scroll", {})
        auth = doc.get("authority", {})
        notes["scroll_id"] = scroll.get("scroll_id")
        notes["public_posture"] = scroll.get("public_posture")
        if (
            scroll.get("scroll_id") != "AGI-0001"
            or scroll.get("public_posture") != "PUBLISHED_CANONICAL"
            or auth.get("system_self_authorizing") is not False
        ):
            errors.append("Approved AGI publication standing/authority invariant failed")
    return errors, warnings, notes


def observe(name: str, url: str, kind: str, opener=None) -> dict:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("Only approved HTTPS public Hall hosts may be observed")
    opener = opener or build_opener(SafeRedirects(), HTTPSHandler(context=ssl.create_default_context()))
    recorded = {
        "name": name,
        "requested_url": url,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "UNKNOWN",
        "http_status": None,
        "redirected_url": None,
        "content_type": None,
        "bytes": None,
        "sha256": None,
        "errors": [],
        "warnings": [],
        "notes": {},
    }
    request = Request(url, headers={
        "User-Agent": "TYME-HALL-LAUNCH-001-public-readonly-smoke/0.1",
        "Accept": "application/json,text/html;q=0.9,*/*;q=0.2",
    }, method="GET")
    try:
        with opener.open(request, timeout=TIMEOUT) as response:
            recorded["http_status"] = response.status
            recorded["redirected_url"] = response.url
            recorded["content_type"] = response.headers.get("content-type", "")
            body = response.read(MAX_BODY + 1)
            if len(body) > MAX_BODY:
                recorded["errors"].append("Public response exceeds bounded size")
            else:
                recorded["bytes"] = len(body)
                recorded["sha256"] = hashlib.sha256(body).hexdigest()
                errors, warnings, notes = _check_payload(kind, body, recorded["content_type"])
                recorded["errors"].extend(errors)
                recorded["warnings"].extend(warnings)
                recorded["notes"] = notes
                if kind == "agi":
                    fixture = HERE / "fixtures" / "agi-0001-publication.json"
                    fixture_sha = hashlib.sha256(fixture.read_bytes()).hexdigest()
                    recorded["notes"]["pinned_source_sha256"] = fixture_sha
                    if fixture_sha != recorded["sha256"]:
                        recorded["errors"].append("Deployed AGI record bytes differ from pinned approved source")
            if recorded["http_status"] != 200:
                recorded["errors"].append("Expected HTTP 200")
            final = urlsplit(response.url)
            if final.scheme != "https" or final.hostname not in ALLOWED_HOSTS:
                recorded["errors"].append("Final host/scheme escaped the HTTPS allowlist")
            recorded["status"] = "OBSERVED_FAIL" if recorded["errors"] else "OBSERVED_OK"
    except HTTPError as exc:
        recorded["http_status"] = exc.code
        recorded["errors"].append("Public HTTP error; no successful body inspected")
        recorded["status"] = "OBSERVED_FAIL"
    except (URLError, OSError, ValueError, TimeoutError) as exc:
        recorded["errors"].append(type(exc).__name__ + ": " + str(exc)[:160])
        recorded["status"] = "UNREACHABLE_FROM_RUNNER"
    return recorded


def summarize(records: list[dict]) -> dict:
    by_name = {item["name"]: item for item in records}
    mismatches = []
    for canonical_name, immutable_name in (
        ("machine_bootstrap", "immutable_bootstrap"),
        ("agi_manifest", "immutable_agi"),
    ):
        a, b = by_name[canonical_name], by_name[immutable_name]
        if a["sha256"] and b["sha256"] and a["sha256"] != b["sha256"]:
            mismatches.append(canonical_name + ": canonical and immutable revision hashes differ")
    return {
        "schema": "tyme-hall-launch-001/public-http-observation/v0.1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "inspection_kind": "PUBLIC_HTTPS_GET_ONLY",
        "production_deployment_ref": "8f2b21b4",
        "source_baseline": "5342cbaf1098391879a15c7ccca752d3fbc241b8",
        "checks": records,
        "counts": {
            "observed_ok": sum(r["status"] == "OBSERVED_OK" for r in records),
            "observed_fail": sum(r["status"] == "OBSERVED_FAIL" for r in records),
            "unreachable": sum(r["status"] == "UNREACHABLE_FROM_RUNNER" for r in records),
        },
        "parity_mismatches": mismatches,
        "deployment_gate_G1": "OPEN",
        "why_gate_open": "Public GET observations alone do not prove rollback, rate controls, accessibility, independent release approval, or the security boundary.",
        "authority_effect": "none",
        "cloudflare_configuration_modified": False,
    }


def main() -> int:
    if len(sys.argv) > 2:
        print("Usage: smoke_public_hall.py [report.json]", file=sys.stderr)
        return 2
    output = Path(sys.argv[1]) if len(sys.argv) == 2 else Path("public-hall-observation.json")
    records = [observe(*test) for test in TESTS]
    report = summarize(records)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for item in records:
        print(item["name"], item["status"], item["http_status"],
              item["notes"].get("age_days", ""),
              "; ".join(item["errors"][:2]), "; ".join(item["warnings"][:1]))
    print("Counts:", report["counts"], "Parity:", report["parity_mismatches"])
    print("G1 remains OPEN; successful GET is not release certification.")
    return 0  # evidence collection must not disguise a partial probe as gate PASS


if __name__ == "__main__":
    raise SystemExit(main())
