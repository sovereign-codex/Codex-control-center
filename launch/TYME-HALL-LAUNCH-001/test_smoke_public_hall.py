"""Unit tests for non-mutating public route observation.

All responses are synthetic: no external network, DNS, deployment or rollback
claims are established by these tests.
"""
import io
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from smoke_public_hall import (  # noqa: E402
    ORIGIN, IMMUTABLE, _check_payload, observe, summarize,
)


class FakeResponse:
    def __init__(self, data: bytes, url: str, status=200, mime="application/json"):
        self._data = data
        self.url = url
        self.status = status
        self.headers = {"content-type": mime}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, count):
        return self._data[:count]


class FakeOpener:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request.full_url, request.get_method(), timeout))
        return self.response


class PublicHallObservationTests(unittest.TestCase):
    def test_valid_bootstrap_is_source_bounded(self):
        document = {
            "canonical_domain": ORIGIN,
            "publications": {"first_publication": {"scroll_id": "AGI-0001"}},
        }
        errors, warnings, notes = _check_payload(
            "bootstrap", json.dumps(document).encode(), "application/json"
        )
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(notes["canonical_domain"], ORIGIN)

    def test_other_canonical_domain_is_rejected(self):
        data = json.dumps({"canonical_domain": "https://fake.example",
                           "publications": {"first_publication": {"scroll_id": "AGI-0001"}}})
        errors, _, _ = _check_payload("bootstrap", data.encode(), "application/json")
        self.assertTrue(any("canonical domain" in e for e in errors))

    def test_stale_office_is_warning_not_hall_release_failure(self):
        data = json.dumps({
            "generated_at": "2026-09-08T10:31:00Z",
            "authority_posture": "non_authorizing",
        })
        errors, warnings, notes = _check_payload(
            "office", data.encode(), "application/json"
        )
        self.assertEqual(errors, [])
        self.assertTrue(any("older than 14 days" in e for e in warnings))
        self.assertGreater(notes["age_days"], 14)

    def test_office_forged_authority_fails(self):
        data = json.dumps({
            "generated_at": "2026-09-08T10:31:00Z", "authority_posture": "authorizing"
        })
        errors, _, _ = _check_payload("office", data.encode(), "application/json")
        self.assertTrue(any("authority boundary" in e for e in errors))

    def test_agi_source_cannot_grant_governance(self):
        data = json.dumps({
            "scroll": {"scroll_id": "AGI-0001", "public_posture": "PUBLISHED_CANONICAL"},
            "authority": {"system_self_authorizing": True},
        })
        errors, _, _ = _check_payload("agi", data.encode(), "application/json")
        self.assertTrue(any("authority invariant" in e for e in errors))

    def test_invalid_json_fails_without_crashing(self):
        errors, _, _ = _check_payload("bootstrap", b"not-json", "application/json")
        self.assertTrue(errors)

    def test_readonly_get_with_approved_host(self):
        body = b"<!doctype html><html></html>"
        opened = FakeOpener(FakeResponse(body, ORIGIN+"/", mime="text/html"))
        result = observe("foyer", ORIGIN+"/", "html", opener=opened)
        self.assertEqual(result["status"], "OBSERVED_OK")
        self.assertEqual(result["http_status"], 200)
        self.assertEqual(result["bytes"], len(body))
        self.assertEqual(opened.calls[0][1], "GET")
        self.assertIsNotNone(result["sha256"])

    def test_unapproved_redirect_target_is_rejected(self):
        opener = FakeOpener(FakeResponse(b"<html></html>", "https://evil.example", mime="text/html"))
        result = observe("foyer", ORIGIN+"/", "html", opener=opener)
        self.assertEqual(result["status"], "OBSERVED_FAIL")
        self.assertTrue(any("escaped" in e for e in result["errors"]))

    def test_unknown_input_host_is_rejected_before_opening(self):
        with self.assertRaises(ValueError):
            observe("unsafe", "https://outside.example/", "html")

    def test_payload_exceeding_limit_has_explicit_failure(self):
        from smoke_public_hall import MAX_BODY
        opened = FakeOpener(FakeResponse(b"x" * (MAX_BODY+1), ORIGIN+"/", mime="text/html"))
        result = observe("foyer", ORIGIN+"/", "html", opener=opened)
        self.assertEqual(result["status"], "OBSERVED_FAIL")
        self.assertIsNone(result["sha256"])

    def test_parity_mismatch_is_reported_and_gate_remains_open(self):
        def record(name, sha):
            return {"name": name, "status": "OBSERVED_OK", "sha256": sha}
        records = [
            record("machine_bootstrap", "abc"),
            record("immutable_bootstrap", "def"),
            record("agi_manifest", "same"),
            record("immutable_agi", "same"),
        ]
        report = summarize(records)
        self.assertEqual(len(report["parity_mismatches"]), 1)
        self.assertEqual(report["deployment_gate_G1"], "OPEN")
        self.assertFalse(report["cloudflare_configuration_modified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
