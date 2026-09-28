"""One acceptance specimen, including bounded negative and recovery cases."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from bridge_specimen import (BoundaryError, Budget, FixtureControl, MAX_BYTES,
    EXECUTOR_MARKER, block_python_network, collect_return, decode, digest, encode,
    fixture_return, inspect_packet, read_bounded, stage_once, verify_custody,
    write_exclusive)

HERE = Path(__file__).resolve().parent
NOW = datetime(2026, 9, 27, tzinfo=timezone.utc)
block_python_network()


class TransportAcceptance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="tyme-bridge-specimen-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.worker, self.custody, self.controller = [self.root / n for n in (
            "worker", "custody", "controller")]
        for directory in (self.worker, self.custody, self.controller):
            directory.mkdir()
        self.raw = (HERE / "fixtures/packet.json").read_bytes()
        self.packet = decode(self.raw)
        self.source = self.controller / "packet.json"
        self.source.write_bytes(self.raw)
        self.control = FixtureControl(self.packet["packet_id"], digest(self.raw),
                                      "2026-09-28T00:00:00Z", True)

    def change_packet(self, change):
        change(self.packet)
        self.raw = encode(self.packet)
        self.source.write_bytes(self.raw)
        self.control = replace(self.control, packet_sha256=digest(self.raw))

    def returned(self, status="complete", change=None):
        _, job = stage_once(self.source, self.worker, self.control, NOW)
        self.return_path = job / "return.json"
        fixture_return(job / "packet.json", self.return_path, status)
        if change:
            value = decode(self.return_path.read_bytes())
            change(value)
            self.return_path.write_bytes(encode(value))
        self.return_raw = self.return_path.read_bytes()
        self.expected = {"packet_id": self.control.packet_id,
                         "packet_sha256": self.control.packet_sha256,
                         "return_sha256": digest(self.return_raw), "executor": EXECUTOR_MARKER}
        self.expected_path = self.controller / "expected.json"
        self.expected_path.write_bytes(encode(self.expected))
        write_exclusive(self.custody / "packet.json", self.raw)
        collect_return(self.return_path, self.custody, self.expected["return_sha256"])
        return job

    def test_01_roundtrip_preserves_exact_bytes(self):
        self.returned()
        report = verify_custody(self.custody, self.expected_path)
        self.assertEqual((self.custody / "packet.json").read_bytes(), self.raw)
        self.assertEqual((self.custody / "return.json").read_bytes(), self.return_raw)
        self.assertEqual(report["raw_execution_status"], "complete")
        self.assertFalse(report["handoff_ready"])
        self.assertEqual(report["institutional_acceptance"], "not_assessed")

    def test_02_duplicate_after_new_call_is_suppressed(self):
        first, job = stage_once(self.source, self.worker, self.control, NOW)
        second, replay = stage_once(self.source, self.worker, self.control, NOW)
        self.assertEqual((first, second), ("delivered", "duplicate_suppressed"))
        self.assertEqual(job, replay)
        self.assertEqual(len(list(self.worker.iterdir())), 1)

    def test_03_same_id_new_digest_is_collision_not_second_delivery(self):
        stage_once(self.source, self.worker, self.control, NOW)
        self.change_packet(lambda p: p.update(task="different request"))
        with self.assertRaisesRegex(BoundaryError, "identity_collision"):
            stage_once(self.source, self.worker, self.control, NOW)

    def test_04_interrupted_claim_holds_without_retry(self):
        job = self.worker / digest(self.control.packet_id.encode())
        job.mkdir()
        write_exclusive(job / "claim.json", encode({"packet_id": self.control.packet_id,
                                                   "packet_sha256": self.control.packet_sha256}))
        with self.assertRaisesRegex(BoundaryError, "interrupted_hold"):
            stage_once(self.source, self.worker, self.control, NOW)
        self.assertFalse((job / "packet.json").exists())

    def test_05_missing_fixture_permission_is_denied(self):
        with self.assertRaisesRegex(BoundaryError, "fixture_not_permitted"):
            stage_once(self.source, self.worker, replace(self.control, permitted=False), NOW)
        self.assertEqual(list(self.worker.iterdir()), [])

    def test_06_expired_fixture_permission_is_denied(self):
        with self.assertRaisesRegex(BoundaryError, "fixture_expired"):
            stage_once(self.source, self.worker,
                       replace(self.control, expires_at="2026-09-27T00:00:00Z"), NOW)

    def test_07_packet_tamper_is_denied(self):
        self.source.write_bytes(self.raw + b" ")
        with self.assertRaisesRegex(BoundaryError, "packet_hash_mismatch"):
            stage_once(self.source, self.worker, self.control, NOW)

    def test_08_legacy_combined_contract_is_not_silently_migrated(self):
        def legacy(p):
            p["return_contract"] = p.pop("envelope_contract")
            p.pop("model_return_contract")
        self.change_packet(legacy)
        with self.assertRaisesRegex(BoundaryError, "legacy_contract_ambiguous"):
            stage_once(self.source, self.worker, self.control, NOW)

    def test_09_unknown_source_profile_is_denied(self):
        with self.assertRaisesRegex(BoundaryError, "profile_unresolved"):
            stage_once(self.source, self.worker, replace(self.control, profile_blob="unknown"), NOW)

    def test_10_capability_expansion_is_denied_even_with_new_digest(self):
        self.change_packet(lambda p: p["executor_requirements"]["capabilities"].append("repository_write"))
        with self.assertRaisesRegex(BoundaryError, "capability_scope_changed"):
            stage_once(self.source, self.worker, self.control, NOW)

    def test_11_private_content_is_outside_this_fixture_profile(self):
        self.change_packet(lambda p: p.update(sensitivity="restricted"))
        with self.assertRaisesRegex(BoundaryError, "non_synthetic_rejected"):
            stage_once(self.source, self.worker, self.control, NOW)

    def test_12_return_tamper_after_custody_is_detected(self):
        self.returned()
        with (self.custody / "return.json").open("ab") as f:
            f.write(b" ")
        with self.assertRaisesRegex(BoundaryError, "return_hash_mismatch"):
            verify_custody(self.custody, self.expected_path)

    def test_13_wrong_packet_id_is_detected_despite_valid_transport_hash(self):
        self.returned(change=lambda r: r.update(packet_id="wrong"))
        with self.assertRaisesRegex(BoundaryError, "return_identity_mismatch"):
            verify_custody(self.custody, self.expected_path)

    def test_14_refusal_is_retained_not_successfully_executed(self):
        self.returned(status="refused")
        result = verify_custody(self.custody, self.expected_path)
        self.assertEqual(result["raw_execution_status"], "refused")
        self.assertFalse(result["handoff_ready"])

    def test_15_partial_return_is_retained_not_completed(self):
        self.returned(status="partial")
        self.assertEqual(verify_custody(self.custody, self.expected_path)["raw_execution_status"], "partial")

    def test_16_failed_return_is_retained_not_completed(self):
        self.returned(status="failed")
        self.assertEqual(verify_custody(self.custody, self.expected_path)["raw_execution_status"], "failed")

    def test_17_custody_cannot_be_overwritten(self):
        self.returned()
        with self.assertRaisesRegex(BoundaryError, "overwrite_rejected"):
            collect_return(self.return_path, self.custody, self.expected["return_sha256"])

    def test_18_fresh_process_verifies_after_worker_directory_removal(self):
        self.returned()
        shutil.rmtree(self.worker)
        result = subprocess.run([sys.executable, "-B", str(HERE / "bridge_specimen.py"),
            "verify", "--custody", str(self.custody), "--expected", str(self.expected_path)],
            capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["byte_custody_check"], "passed")
        self.assertEqual(report["model_execution"], "not_performed")

    def test_19_bytes_and_python_network_guard(self):
        self.source.write_bytes(b"x" * (MAX_BYTES + 1))
        with self.assertRaisesRegex(BoundaryError, "byte_budget"):
            read_bounded(self.source)
        with self.assertRaisesRegex(BoundaryError, "network_forbidden"):
            socket.socket()

    def test_20_final_processing_overrun_is_not_success(self):
        self.returned()
        another = self.root / "late_custody"
        another.mkdir()
        ticks = iter([0.0, 0.0, 6.0])
        with self.assertRaisesRegex(BoundaryError, "elapsed_budget"):
            collect_return(self.return_path, another, self.expected["return_sha256"],
                           Budget(5.0, lambda: next(ticks)))
        # Bytes may have arrived. A late operation must still NOT report success.
        self.assertTrue((another / "return.json").exists())

    def test_21_untrusted_instruction_text_remains_inert(self):
        with patch("os.system", side_effect=AssertionError("shell_forbidden")), \
             patch("subprocess.Popen", side_effect=AssertionError("child_process_forbidden")):
            self.returned()
        inner = decode(decode(self.return_raw)["model_output"].encode())
        self.assertIn("$(touch SHOULD_NOT_EXIST)", inner["summary"])
        self.assertIn("\r\n", inner["summary"])
        self.assertIn("\u03a9", inner["summary"])
        self.assertFalse((self.root / "SHOULD_NOT_EXIST").exists())
        self.assertEqual(inner["summary"], self.packet["inputs"][0]["value"])

    def test_22_duplicate_json_keys_and_false_model_claim_fail(self):
        with self.assertRaisesRegex(BoundaryError, "duplicate_json_key"):
            decode(b'{"packet_id":"a","packet_id":"b"}')
        self.returned(change=lambda r: r.update(model="a-real-model-we-did-not-run"))
        with self.assertRaisesRegex(BoundaryError, "false_model_claim"):
            verify_custody(self.custody, self.expected_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
