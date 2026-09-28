"""Review-only red regressions for the immutable bridge candidate.

All fixtures are synthetic, all writes are temporary. No network or source-system
calls. These tests express desired boundary behavior and are expected to fail on
the original candidate. A failure here is evidence of an unresolved gap, not PASS.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import unittest
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
TARGET = Path(os.environ.get("BRIDGE_CANDIDATE_DIR", str(
    HERE / "original" / "tyme_bridge_crosswalk_001"))).resolve()
sys.path.insert(0, str(TARGET))
import bridge_specimen as b

b.block_python_network()
NOW = datetime(2026, 9, 27, tzinfo=timezone.utc)
OBSERVATIONS: dict[str, Any] = {}


class BridgeReviewRegressions(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="tyme-bridge-review-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.worker = self.root / "worker"
        self.custody = self.root / "custody"
        self.controller = self.root / "controller"
        for path in (self.worker, self.custody, self.controller):
            path.mkdir()
        self.raw = (TARGET / "fixtures" / "packet.json").read_bytes()
        self.packet = b.decode(self.raw)
        self.source = self.controller / "packet.json"
        self.source.write_bytes(self.raw)
        self.control = b.FixtureControl(
            self.packet["packet_id"], b.digest(self.raw), "2026-09-28T00:00:00Z", True)
        self.obs: dict[str, Any] = {}
        OBSERVATIONS[self._testMethodName] = self.obs

    def record(self, name: str, operation: Callable[[], Any]) -> Any:
        try:
            value = operation()
            self.obs[name] = {"returned": value if isinstance(value, dict) else str(value)}
            return value
        except Exception as error:
            self.obs[name] = {"exception": type(error).__name__, "code": str(error)}
            raise

    def change_packet(self, change: Callable[[dict], None]) -> None:
        change(self.packet)
        self.raw = b.encode(self.packet)
        self.source.write_bytes(self.raw)
        self.control = replace(self.control, packet_sha256=b.digest(self.raw))

    def custody_for_current_packet(self, change_return=None) -> Path:
        # This models a controller truthfully hashing a malformed/profile-invalid
        # sample. It does NOT claim tampering can bypass an unchanged trusted hash.
        rp = self.worker / "return.json"
        b.fixture_return(self.source, rp)
        if change_return is not None:
            value = b.decode(rp.read_bytes())
            change_return(value)
            rp.write_bytes(b.encode(value))
        raw_return = rp.read_bytes()
        (self.custody / "packet.json").write_bytes(self.raw)
        (self.custody / "return.json").write_bytes(raw_return)
        expected_path = self.controller / "expected.json"
        expected_path.write_bytes(b.encode({
            "packet_id": self.control.packet_id,
            "packet_sha256": b.digest(self.raw),
            "return_sha256": b.digest(raw_return),
            "executor": b.EXECUTOR_MARKER,
        }))
        return expected_path

    def expect_staging_and_verification_reject(self, change_return=None) -> None:
        with self.assertRaises(b.BoundaryError):
            self.record("staging_validator", lambda: b.inspect_packet(
                self.raw, self.control, NOW))
        expected = self.custody_for_current_packet(change_return)
        with self.assertRaises(b.BoundaryError):
            self.record("standalone_verifier", lambda: b.verify_custody(self.custody, expected))

    def test_R01_verifier_rejects_non_synthetic_profile(self) -> None:
        self.change_packet(lambda p: p.update(sensitivity="restricted"))
        self.expect_staging_and_verification_reject()

    def test_R02_verifier_rejects_expanded_capability(self) -> None:
        self.change_packet(lambda p: p["executor_requirements"]["capabilities"].append(
            "repository_write"))
        self.expect_staging_and_verification_reject()

    def test_R03_verifier_cannot_take_weakened_schema_from_packet(self) -> None:
        self.change_packet(lambda p: p["envelope_contract"].update(required_fields=[]))
        self.expect_staging_and_verification_reject(lambda r: r.pop("timestamp_utc"))

    def test_R04_verifier_rejects_unknown_packet_version(self) -> None:
        self.change_packet(lambda p: p.update(packet_version="unreviewed-version"))
        self.expect_staging_and_verification_reject()

    def test_R05_duplicate_requires_nonempty_terminal_record(self) -> None:
        _, job = b.stage_once(self.source, self.worker, self.control, NOW)
        (job / "delivered.json").write_bytes(b"")
        with self.assertRaises(b.BoundaryError):
            self.record("replay", lambda: b.stage_once(self.source, self.worker, self.control, NOW))

    def test_R06_duplicate_rejects_contradictory_terminal_record(self) -> None:
        _, job = b.stage_once(self.source, self.worker, self.control, NOW)
        (job / "delivered.json").write_bytes(b.encode({"transport_only": False}))
        with self.assertRaises(b.BoundaryError):
            self.record("replay", lambda: b.stage_once(self.source, self.worker, self.control, NOW))

    def test_R07_final_deadline_failure_stays_held_on_next_call(self) -> None:
        ticks = iter([0.0, 0.0, 0.0, 0.0, 6.0])
        with self.assertRaisesRegex(b.BoundaryError, "elapsed_budget"):
            self.record("initial_call", lambda: b.stage_once(
                self.source, self.worker, self.control, NOW,
                b.Budget(5.0, lambda: next(ticks))))
        job = self.worker / b.digest(self.control.packet_id.encode())
        self.obs["terminal_record_after_timeout"] = (job / "delivered.json").read_text()
        try:
            replay = self.record("replay", lambda: b.stage_once(
                self.source, self.worker, self.control, NOW))
        except b.BoundaryError:
            return  # Explicit fail-closed hold is an acceptable repaired behavior.
        # A future structured held/late outcome is also acceptable; normal
        # duplicate suppression alone must not erase the preceding deadline error.
        self.assertNotIn(replay[0], {"delivered", "duplicate_suppressed"})

    def test_R08_malformed_input_returns_stable_boundary_error(self) -> None:
        self.change_packet(lambda p: p.update(inputs=[17]))
        with self.assertRaisesRegex(b.BoundaryError, "fixture_input"):
            self.record("staging_validator", lambda: b.inspect_packet(self.raw, self.control, NOW))

    def test_R09_nonfinite_decoded_numbers_are_rejected(self) -> None:
        # This is numeric overflow, not the literal NaN/Infinity tokens already
        # covered by json.loads(parse_constant=...).
        with self.assertRaises(b.BoundaryError):
            result = b.decode(b'{"elapsed":1e999}')
            self.obs["decoded_number_is_finite"] = math.isfinite(result["elapsed"])
            self.obs["decoded_number_repr"] = repr(result["elapsed"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BridgeReviewRegressions)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    outdir = Path(os.environ.get("BRIDGE_REVIEW_OUTPUT", str(HERE / "evidence")))
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "regression_observations.json").write_text(
        json.dumps(OBSERVATIONS, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    (outdir / "regression_result.json").write_text(json.dumps({
        "tests_run": result.testsRun, "failures": len(result.failures),
        "errors": len(result.errors), "successful": result.wasSuccessful(),
        "candidate_changed": False,
        "interpretation": "Red regression failures expose unresolved candidate behavior; not an acceptance PASS.",
    }, indent=2) + "\n")
    sys.exit(0 if result.wasSuccessful() else 1)
