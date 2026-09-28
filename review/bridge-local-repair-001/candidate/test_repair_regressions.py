"""Repair-001 tests: local profile checks, record publication and failure replay.

Synthetic-only. Injected clocks and local I/O faults are not live crash tests.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import bridge_specimen as b

HERE = Path(__file__).resolve().parent
NOW = datetime(2026, 9, 27, tzinfo=timezone.utc)
b.block_python_network()


class RepairRegressions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tyme-bridge-repair-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.worker, self.custody, self.controller = [self.root / n for n in (
            "worker", "custody", "controller")]
        for path in (self.worker, self.custody, self.controller):
            path.mkdir()
        self.raw = (HERE / "fixtures/packet.json").read_bytes()
        self.source = self.controller / "packet.json"
        self.source.write_bytes(self.raw)
        self.packet = b.decode(self.raw)
        self.control = b.FixtureControl(self.packet["packet_id"], b.digest(self.raw),
                                        "2026-09-28T00:00:00Z", True)
        self.job = self.worker / b.digest(self.control.packet_id.encode())

    def stage(self, budget=None):
        return b.stage_once(self.source, self.worker, self.control, NOW, budget)

    def evidence(self):
        self.stage()
        rp = self.job / "return.json"
        b.fixture_return(self.job / "packet.json", rp)
        self.return_raw = rp.read_bytes()
        (self.custody / "packet.json").write_bytes(self.raw)
        (self.custody / "return.json").write_bytes(self.return_raw)
        self.expected = {"packet_id": self.control.packet_id,
                         "packet_sha256": b.digest(self.raw),
                         "return_sha256": b.digest(self.return_raw),
                         "executor": b.EXECUTOR_MARKER}
        self.expected_path = self.controller / "expected.json"
        self.expected_path.write_bytes(b.encode(self.expected))

    def set_custody_packet(self, packet):
        raw = b.encode(packet)
        (self.custody / "packet.json").write_bytes(raw)
        self.expected["packet_sha256"] = b.digest(raw)
        self.expected_path.write_bytes(b.encode(self.expected))
        return raw

    def set_custody_return(self, value):
        raw = b.encode(value)
        (self.custody / "return.json").write_bytes(raw)
        self.expected["return_sha256"] = b.digest(raw)
        self.expected_path.write_bytes(b.encode(self.expected))

    def test_P01_completion_record_binds_to_exact_claim_and_preparation(self):
        self.assertEqual(self.stage()[0], "delivered")
        claim_raw = (self.job / "claim.json").read_bytes()
        delivery_raw = (self.job / "delivered.json").read_bytes()
        delivery = b.decode(delivery_raw)
        outcome = b.decode((self.job / "outcome.json").read_bytes())
        self.assertEqual(delivery["claim_sha256"], b.digest(claim_raw))
        self.assertEqual(delivery["profile_blob"], b.PROFILE_BLOB)
        self.assertEqual(delivery["state"], "prepared")
        self.assertEqual(outcome["delivery_record_sha256"], b.digest(delivery_raw))
        self.assertEqual(outcome["state"], "delivered")
        self.assertEqual(self.stage()[0], "duplicate_suppressed")

    def test_P02_historical_verification_never_calls_current_permission_check(self):
        self.evidence()
        with patch.object(b.FixtureControl, "check", side_effect=AssertionError("no_renewal")):
            result = b.verify_custody(self.custody, self.expected_path)
        self.assertFalse(result["authorization_rechecked"])
        self.assertEqual(result["authority_effect"], "none")
        self.assertFalse(result["handoff_ready"])
        with self.assertRaisesRegex(b.BoundaryError, "fixture_expired"):
            b.stage_once(self.source, self.worker, self.control,
                         datetime(2026, 9, 29, tzinfo=timezone.utc))

    def test_P03_unknown_verifier_profile_cannot_be_selected_by_packet(self):
        self.evidence()
        with self.assertRaisesRegex(b.BoundaryError, "profile_unresolved"):
            b.verify_custody(self.custody, self.expected_path, profile_blob="other")

    def test_P04_changed_terminal_bindings_are_held_without_writes(self):
        self.stage()
        path = self.job / "delivered.json"
        original = path.read_bytes()
        for key in ("packet_id", "packet_sha256", "claim_sha256", "profile_blob",
                    "record_version", "state"):
            with self.subTest(field=key):
                record = b.decode(original)
                record[key] = "changed"
                raw = b.encode(record)
                path.write_bytes(raw)
                with self.assertRaisesRegex(b.BoundaryError, "delivery_record_invalid"):
                    self.stage()
                self.assertEqual(path.read_bytes(), raw)
                self.assertEqual((self.job / "packet.json").read_bytes(), self.raw)
        path.write_bytes(original)

    def test_P05_empty_malformed_or_contradictory_outcome_never_means_completed(self):
        self.stage()
        path = self.job / "outcome.json"
        for raw in (b"", b"{", b'{"transport_only":false}', b'{"state":"delivered"}'):
            with self.subTest(raw=raw):
                path.write_bytes(raw)
                with self.assertRaises(b.BoundaryError):
                    self.stage()
                self.assertEqual(path.read_bytes(), raw)

    def test_P06_unpublished_complete_pending_record_stays_held(self):
        self.stage()
        (self.job / "outcome.json").unlink()
        pending = (self.job / "outcome.pending.json").read_bytes()
        with patch.object(b, "write_exclusive", side_effect=AssertionError("no_retry")):
            with self.assertRaisesRegex(b.BoundaryError, "interrupted_hold"):
                self.stage()
        self.assertFalse((self.job / "outcome.json").exists())
        self.assertEqual((self.job / "outcome.pending.json").read_bytes(), pending)

    def test_P07_symlinked_decision_files_are_rejected(self):
        self.stage()
        for name in ("delivered.json", "outcome.json", "held.json"):
            with self.subTest(name=name):
                path = self.job / name
                exists = path.exists()
                original = path.read_bytes() if exists else None
                external = self.controller / (name + ".target")
                external.write_bytes(original or b'{}')
                if exists:
                    path.unlink()
                path.symlink_to(external)
                with self.assertRaisesRegex(b.BoundaryError, "symlink_rejected"):
                    self.stage()
                path.unlink()
                if exists:
                    path.write_bytes(original)

    def test_P08_prepared_record_legacy_boolean_is_not_a_completion(self):
        self.stage()
        (self.job / "delivered.json").write_bytes(b'{"transport_only":true}')
        with self.assertRaisesRegex(b.BoundaryError, "delivery_record_invalid"):
            self.stage()

    def test_P09_deadline_after_last_decision_preparation_is_retained(self):
        elapsed = [0.0]
        budget = b.Budget(5.0, lambda: elapsed[0])
        original = b.write_exclusive

        def slow_final_write(path, data):
            original(path, data)
            if path.name == "outcome.pending.json":
                elapsed[0] = 6.0

        with patch.object(b, "write_exclusive", side_effect=slow_final_write):
            with self.assertRaisesRegex(b.BoundaryError, "elapsed_budget"):
                self.stage(budget)
        self.assertFalse((self.job / "outcome.json").exists())
        self.assertTrue((self.job / "outcome.pending.json").exists())
        self.assertEqual(b.decode((self.job / "held.json").read_bytes())["reason"],
                         "elapsed_budget")
        with self.assertRaisesRegex(b.BoundaryError, "delivery_held_elapsed_budget"):
            self.stage()
        self.assertEqual((self.job / "packet.json").read_bytes(), self.raw)

    def test_P10_partial_preparation_write_never_publishes_success(self):
        original = b.write_exclusive

        def partial_write(path, data):
            if path.name == "delivered.json":
                path.write_bytes(data[:12])
                raise b.BoundaryError("write_failed")
            original(path, data)

        with patch.object(b, "write_exclusive", side_effect=partial_write):
            with self.assertRaisesRegex(b.BoundaryError, "write_failed"):
                self.stage()
        self.assertFalse((self.job / "outcome.json").exists())
        with self.assertRaises(b.BoundaryError):
            self.stage()

    def test_P11_partial_last_decision_write_stays_held(self):
        original = b.write_exclusive

        def partial_write(path, data):
            if path.name == "outcome.pending.json":
                path.write_bytes(data[:12])
                raise b.BoundaryError("write_failed")
            original(path, data)

        with patch.object(b, "write_exclusive", side_effect=partial_write):
            with self.assertRaisesRegex(b.BoundaryError, "write_failed"):
                self.stage()
        self.assertFalse((self.job / "outcome.json").exists())
        with self.assertRaisesRegex(b.BoundaryError, "delivery_held_write_failed"):
            self.stage()

    def test_P12_fully_written_but_failed_flush_cannot_be_completion(self):
        original = b.write_exclusive

        def failed_flush(path, data):
            original(path, data)
            if path.name == "outcome.pending.json":
                raise b.BoundaryError("write_failed")

        with patch.object(b, "write_exclusive", side_effect=failed_flush):
            with self.assertRaisesRegex(b.BoundaryError, "write_failed"):
                self.stage()
        self.assertEqual(b.decode((self.job / "outcome.pending.json").read_bytes())["state"],
                         "delivered")
        self.assertFalse((self.job / "outcome.json").exists())
        with self.assertRaisesRegex(b.BoundaryError, "delivery_held_write_failed"):
            self.stage()

    def test_P13_final_preparation_readback_mismatch_stays_held(self):
        original = b.read_bounded

        def changed_read(path, *args, **kwargs):
            raw = original(path, *args, **kwargs)
            return raw + b" " if path.name == "outcome.pending.json" else raw

        with patch.object(b, "read_bounded", side_effect=changed_read):
            with self.assertRaisesRegex(b.BoundaryError, "decision_mismatch"):
                self.stage()
        self.assertFalse((self.job / "outcome.json").exists())
        with self.assertRaisesRegex(b.BoundaryError, "delivery_held_decision_mismatch"):
            self.stage()

    def test_P14_atomic_publication_error_is_held_not_retried(self):
        with patch.object(b.os, "link", side_effect=OSError("synthetic fault")):
            with self.assertRaisesRegex(b.BoundaryError, "decision_publish_failed"):
                self.stage()
        with patch.object(b.os, "link", side_effect=AssertionError("must_not_retry")):
            with self.assertRaisesRegex(b.BoundaryError, "delivery_held_decision_publish_failed"):
                self.stage()

    def test_P15_failure_record_write_failure_cannot_leave_success(self):
        original = b.write_exclusive
        ticks = iter([0.0, 0.0, 0.0, 0.0, 6.0])

        def fail_held(path, data):
            if path.name == "held.json":
                raise b.BoundaryError("write_failed")
            original(path, data)

        with patch.object(b, "write_exclusive", side_effect=fail_held):
            with self.assertRaisesRegex(b.BoundaryError, "elapsed_budget"):
                self.stage(b.Budget(5.0, lambda: next(ticks)))
        self.assertFalse((self.job / "held.json").exists())
        self.assertFalse((self.job / "outcome.json").exists())
        with self.assertRaisesRegex(b.BoundaryError, "interrupted_hold"):
            self.stage()

    def test_P16_late_outcome_stays_held_in_fresh_process(self):
        ticks = iter([0.0, 0.0, 0.0, 0.0, 6.0])
        with self.assertRaisesRegex(b.BoundaryError, "elapsed_budget"):
            self.stage(b.Budget(5.0, lambda: next(ticks)))
        code = """
import sys, json
from pathlib import Path
from datetime import datetime, timezone
import bridge_specimen as b
b.block_python_network()
src, root = map(Path, sys.argv[1:])
raw = src.read_bytes()
control = b.FixtureControl(b.decode(raw)['packet_id'], b.digest(raw),
                          '2026-09-28T00:00:00Z', True)
try:
    b.stage_once(src, root, control, datetime(2026, 9, 27, tzinfo=timezone.utc))
except b.BoundaryError as e:
    print(json.dumps({'error_code': str(e)}))
    sys.exit(0)
sys.exit(3)
"""
        result = subprocess.run([sys.executable, "-B", "-c", code,
                                 str(self.source), str(self.worker)], cwd=HERE,
                                capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["error_code"],
                         "delivery_held_elapsed_budget")

    def test_P17_nested_input_variants_use_same_stable_error_at_both_gates(self):
        self.evidence()
        for inputs in (None, [], [17], [None], ["text"], [[]], [True],
                       [{"type": "synthetic_text", "value": 9}], {}, [self.packet["inputs"][0]] * 2):
            with self.subTest(inputs=inputs):
                packet = dict(self.packet, inputs=inputs)
                raw = self.set_custody_packet(packet)
                control = replace(self.control, packet_sha256=b.digest(raw))
                with self.assertRaisesRegex(b.BoundaryError, "fixture_input"):
                    b.inspect_packet(raw, control, NOW)
                with self.assertRaisesRegex(b.BoundaryError, "fixture_input"):
                    b.verify_custody(self.custody, self.expected_path)

    def test_P18_malformed_return_values_never_raise_uncontrolled_type_errors(self):
        self.evidence()
        cases = [("execution_status", []), ("execution_status", {}),
                 ("model_output", []), ("model_output", "[]"),
                 ("model_output", '{"packet_id":"x"}'),
                 ("timestamp_utc", None), ("timestamp_utc", "not-a-time"),
                 ("timestamp_utc", "2026-09-27"), ("warnings", [None]),
                 ("artifacts", ["unverified-object"])]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                result = b.decode(self.return_raw)
                result[field] = value
                self.set_custody_return(result)
                with self.assertRaises(b.BoundaryError):
                    b.verify_custody(self.custody, self.expected_path)

    def test_P19_malformed_expected_values_use_stable_boundary_error(self):
        self.evidence()
        cases = [{}, dict(self.expected, packet_id=None),
                 dict(self.expected, packet_sha256=17),
                 dict(self.expected, return_sha256="short"),
                 dict(self.expected, profile_blob="packet-selected-profile")]
        for expected in cases:
            with self.subTest(expected=expected):
                self.expected_path.write_bytes(b.encode(expected))
                with self.assertRaises(b.BoundaryError):
                    b.verify_custody(self.custody, self.expected_path)

    def test_P20_nonfinite_numbers_rejected_at_all_json_depths(self):
        for raw in (b'{"x":1e999}', b'{"x":-1e999}',
                    b'{"x":[{"y":1e999}]}', b'{"x":NaN}',
                    b'{"x":[Infinity]}', b'{"x":-Infinity}'):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(b.BoundaryError, "nonfinite_json"):
                    b.decode(raw)
        self.assertEqual(b.decode(b'{"x":[1,1.5,-2e3,1e308,0.0]}')["x"],
                         [1, 1.5, -2000.0, 1e308, 0.0])

    def test_P21_boolean_like_numbers_do_not_satisfy_flags(self):
        self.evidence()
        packet = b.decode(self.raw)
        packet["model_return_contract"]["json_only"] = 1
        self.set_custody_packet(packet)
        with self.assertRaisesRegex(b.BoundaryError, "model_contract_changed"):
            b.verify_custody(self.custody, self.expected_path)
        with self.assertRaisesRegex(b.BoundaryError, "fixture_not_permitted"):
            b.inspect_packet(self.raw, replace(self.control, permitted=1), NOW)
        record = b.decode((self.job / "delivered.json").read_bytes())
        record["transport_only"] = 1
        (self.job / "delivered.json").write_bytes(b.encode(record))
        with self.assertRaisesRegex(b.BoundaryError, "delivery_record_invalid"):
            self.stage()

    def test_P22_corrupt_held_record_overrides_apparent_completion(self):
        self.stage()
        for raw in (b"", b"{", b'{"state":"held"}', b'{"transport_only":false}'):
            with self.subTest(raw=raw):
                (self.job / "held.json").write_bytes(raw)
                with self.assertRaises(b.BoundaryError):
                    self.stage()

    def test_P23_valid_held_record_overrides_published_outcome(self):
        self.stage()
        prepared = (self.job / "delivered.json").read_bytes()
        b._record_failure(self.job, prepared, "elapsed_budget")
        with self.assertRaisesRegex(b.BoundaryError, "delivery_held_elapsed_budget"):
            self.stage()

    def test_P24_unknown_fields_or_changed_outcome_bindings_fail_closed(self):
        self.stage()
        original = (self.job / "outcome.json").read_bytes()
        for change in ({"delivery_record_sha256": "0" * 64}, {"transport_only": 1},
                       {"extra_authority": True}, {"reason": "unchecked"}):
            with self.subTest(change=change):
                (self.job / "outcome.json").write_bytes(b.encode(dict(b.decode(original), **change)))
                with self.assertRaisesRegex(b.BoundaryError, "outcome_record_invalid"):
                    self.stage()

    def test_P25_timestamp_model_inner_and_control_shapes_are_bounded(self):
        for expiry in (None, [], 17, "not-a-time"):
            with self.subTest(expiry=expiry):
                with self.assertRaisesRegex(b.BoundaryError, "invalid_expiry"):
                    b.inspect_packet(self.raw, replace(self.control, expires_at=expiry), NOW)
        for seconds in (None, "5", True, float("inf"), float("nan"), -1, 0):
            with self.subTest(seconds=seconds):
                with self.assertRaisesRegex(b.BoundaryError, "invalid_budget"):
                    b.Budget(seconds)
        for now in (None, "today"):
            with self.subTest(now=now):
                with self.assertRaisesRegex(b.BoundaryError, "invalid_now"):
                    b.inspect_packet(self.raw, self.control, now)

    def test_P26_success_publishes_only_after_final_budget_check(self):
        calls = []
        ticks = [0.0]

        def clock():
            calls.append("clock")
            return ticks[0]

        original = b.os.link

        def commit(src, dst, **kwargs):
            self.assertEqual(calls[-1], "clock")
            self.assertTrue(Path(src).is_file())
            self.assertFalse(Path(dst).exists())
            calls.append("publish")
            return original(src, dst, **kwargs)

        with patch.object(b.os, "link", side_effect=commit):
            self.assertEqual(self.stage(b.Budget(5.0, clock))[0], "delivered")
        self.assertEqual(calls[-1], "publish")
        self.assertEqual(calls.count("clock"), 6)

    def test_P27_commit_target_cannot_be_overwritten(self):
        def occupied(src, dst, **kwargs):
            Path(dst).write_bytes(b"preexisting synthetic collision")
            raise FileExistsError("synthetic collision")
        with patch.object(b.os, "link", side_effect=occupied):
            with self.assertRaisesRegex(b.BoundaryError, "decision_publish_failed"):
                self.stage()
        self.assertEqual((self.job / "outcome.json").read_bytes(),
                         b"preexisting synthetic collision")
        with self.assertRaisesRegex(b.BoundaryError, "delivery_held_decision_publish_failed"):
            self.stage()

    def test_P28_claim_format_change_breaks_record_binding(self):
        self.stage()
        claim_path = self.job / "claim.json"
        claim_path.write_bytes(claim_path.read_bytes() + b" ")
        with self.assertRaisesRegex(b.BoundaryError, "delivery_record_invalid"):
            self.stage()

    def test_P29_packet_readback_failure_preserves_bytes_without_success_marker(self):
        original = b.read_bounded

        def failed_read(path, *args, **kwargs):
            if path == self.job / "packet.json":
                raise b.BoundaryError("read_failed")
            return original(path, *args, **kwargs)

        with patch.object(b, "read_bounded", side_effect=failed_read):
            with self.assertRaisesRegex(b.BoundaryError, "read_failed"):
                self.stage()
        self.assertEqual((self.job / "packet.json").read_bytes(), self.raw)
        self.assertFalse((self.job / "outcome.json").exists())
        with self.assertRaisesRegex(b.BoundaryError, "interrupted_hold"):
            self.stage()

    def test_P30_oversized_terminal_record_is_bounded(self):
        self.stage()
        (self.job / "delivered.json").write_bytes(b"x" * (b.MAX_BYTES + 1))
        with self.assertRaisesRegex(b.BoundaryError, "byte_budget"):
            self.stage()


if __name__ == "__main__":
    unittest.main(verbosity=2)
