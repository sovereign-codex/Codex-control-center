"""Offline proof-ceiling and idempotency checks for synthetic Phase 2 intake.

Run with:
python3 -m unittest discover -s launch/TYME-HALL-LAUNCH-001 -p 'test_phase2_*.py' -v

No real scheduled automation, Notion, Cloudflare, or public Hall is accessed.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase2_replay import (  # noqa: E402
    PHASE,
    TASK_ID,
    ContractViolation,
    ReplayConflict,
    ReplayStore,
    make_test_receipt,
    validate_terminal_receipt,
)

RUN = "2026-10-12T08:15:00-07:00"
SECOND_RUN = "2026-10-19T08:15:00-07:00"


class Phase2ReceiptContractTests(unittest.TestCase):
    def _null(self):
        return make_test_receipt(
            RUN, "NO_DURABLE_SIGNAL", reason="No qualifying architectural delta."
        )

    def _positive(self):
        return make_test_receipt(RUN, "SIGNAL_PRESERVED")

    def _failed(self):
        return make_test_receipt(
            RUN,
            "PHASE2_HANDOFF_FAILED",
            reason="Notion ledger is unavailable; no alternate destination.",
            failure_stage="receipt",
        )

    def test_accepts_synthetic_null_positive_failure_shapes_without_proof_credit(self):
        for document in (self._null(), self._positive(), self._failed()):
            self.assertEqual(document["phase"], PHASE)
            self.assertEqual(document["source_task_id"], TASK_ID)
            self.assertEqual(document["next_state"], "dormant")
            self.assertFalse(document["phase2_proof_credit"])
            self.assertFalse(document["downstream_wake_attempted"])
            self.assertFalse(document["repository_mutation"])
            self.assertEqual(validate_terminal_receipt(document), document)

    def test_timestamp_identity_must_match_scheduled_monday_and_fixed_timezone(self):
        self.assertEqual(
            self._null()["receipt_id"],
            "P2-RECEIPT-" + TASK_ID + "-20261012-0815",
        )
        for invalid in (
            "2026-10-12T08:15:00",  # no timezone
            "2026-10-12T08:15:00Z",  # different absolute time
            "2026-10-12T08:15:01-07:00",
            "2026-10-12T08:16:00-07:00",
            "2026-10-13T08:15:00-07:00",  # not Monday
            "not-a-time",
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ContractViolation):
                    make_test_receipt(invalid, "NO_DURABLE_SIGNAL", reason="no change")

    def test_wrong_run_id_cannot_be_promoted_or_relabelled(self):
        packet = self._null()
        packet["source_task_id"] = "6ac989a44cd88191b72fad2ff76fefe6"
        with self.assertRaisesRegex(ContractViolation, "production SCAI monitor"):
            validate_terminal_receipt(packet)
        packet = self._null()
        packet["receipt_id"] = "P2-RUNTIME-RECEIPT-20261009-002"
        with self.assertRaisesRegex(ContractViolation, "deterministic"):
            validate_terminal_receipt(packet)

    def test_wrong_receipt_date_is_rejected(self):
        packet = self._null()
        packet["receipt_id"] = "P2-RECEIPT-" + TASK_ID + "-20261019-0815"
        with self.assertRaises(ContractViolation):
            validate_terminal_receipt(packet)

    def test_foreign_phase_and_alternate_inbox_are_rejected(self):
        for key, value in (
            ("phase", "Phase 3"),
            ("intake_surface", "HALL_NATIVE_RECEIPTS"),
        ):
            packet = self._null()
            packet[key] = value
            with self.subTest(key=key), self.assertRaises(ContractViolation):
                validate_terminal_receipt(packet)

    def test_forbidden_authority_flags_require_explicit_false(self):
        for flag in (
            "duplicate_created",
            "downstream_wake_attempted",
            "work_created",
            "repository_mutation",
            "hall_receipt_claimed",
            "canon_claimed",
        ):
            for invalid in (True, None, "false"):
                packet = self._null()
                packet[flag] = invalid
                with self.subTest(flag=flag, value=invalid):
                    with self.assertRaises(ContractViolation):
                        validate_terminal_receipt(packet)
            packet = self._null()
            del packet[flag]
            with self.subTest(flag=flag, value="missing"):
                with self.assertRaises(ContractViolation):
                    validate_terminal_receipt(packet)

    def test_phase2_proof_and_next_state_never_promoted(self):
        packet = self._null()
        packet["phase2_proof_credit"] = True
        with self.assertRaisesRegex(ContractViolation, "cannot grant Phase 2 proof"):
            validate_terminal_receipt(packet)
        packet = self._null()
        packet["next_state"] = "awake"
        with self.assertRaises(ContractViolation):
            validate_terminal_receipt(packet)

    def test_rejects_unreviewed_field_from_new_institutional_schema(self):
        packet = self._null()
        packet["hall_native_receipt"] = "made-up"
        with self.assertRaisesRegex(ContractViolation, "unknown/unreviewed"):
            validate_terminal_receipt(packet)

    def test_positive_requires_matching_signal_and_unchallenged_evidence_posture(self):
        for key, bad in (
            ("signal_id", "SIGNAL-SCAI-P2-20261019-001"),
            ("signal_id", None),
            ("signal_not_persisted", True),
            ("reason", "unverified"),
            ("failure_stage", "create"),
        ):
            packet = self._positive()
            packet[key] = bad
            with self.subTest(key=key), self.assertRaises(ContractViolation):
                validate_terminal_receipt(packet)

    def test_null_requires_reason_no_signal_and_review_posture(self):
        for key, bad in (
            ("reason", ""),
            ("signal_id", "SIGNAL-SCAI-P2-20261012-001"),
            ("next_review_posture", "activate_curator"),
            ("signal_not_persisted", False),
        ):
            packet = self._null()
            packet[key] = bad
            with self.subTest(key=key), self.assertRaises(ContractViolation):
                validate_terminal_receipt(packet)

    def test_failure_requires_stage_reason_and_no_signal(self):
        for key, bad in (
            ("failure_stage", "wake"),
            ("reason", ""),
            ("signal_id", "SIGNAL-SCAI-P2-20261012-001"),
            ("signal_not_persisted", False),
        ):
            packet = self._failed()
            packet[key] = bad
            with self.subTest(key=key), self.assertRaises(ContractViolation):
                validate_terminal_receipt(packet)

    def test_document_is_plain_json_without_secret_or_external_effect(self):
        packet = self._null()
        restored = json.loads(json.dumps(packet))
        self.assertEqual(validate_terminal_receipt(restored), packet)


class Phase2ReplayStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_path = Path(self.temp.name) / "synthetic-replay.sqlite3"
        self.store = ReplayStore(self.db_path)
        self.null = make_test_receipt(RUN, "NO_DURABLE_SIGNAL", reason="No qualifying delta.")

    def test_first_capture_only_writes_local_synthetic_receipt(self):
        result = self.store.capture(self.null)
        self.assertEqual(result["status"], "SYNTHETIC_ACCEPTED")
        self.assertEqual(self.store.snapshot()["count"], 1)
        self.assertEqual(self.store.snapshot()["integrity"], "ok")
        self.assertTrue(self.store.snapshot()["append_only"])
        self.assertFalse(result["phase2_proof_credit"])
        self.assertEqual(result["authority_effect"], "none")
        self.assertFalse(result["notion_receipt_verified"])
        self.assertFalse(result["cloudflare_carrier_verified"])

    def test_same_identity_and_payload_suppresses_duplicate_even_after_reopen(self):
        initial = self.store.capture(self.null)
        reopened = ReplayStore(self.db_path)
        repeated = reopened.capture(deepcopy(self.null))
        self.assertEqual(repeated["status"], "DUPLICATE_SUPPRESSED")
        self.assertEqual(initial["sequence"], repeated["sequence"])
        self.assertEqual(reopened.snapshot()["count"], 1)

    def test_same_identity_changed_content_is_conflict_not_overwrite(self):
        self.store.capture(self.null)
        changed = deepcopy(self.null)
        changed["reason"] = "Different valid reason for same run"
        with self.assertRaises(ReplayConflict):
            self.store.capture(changed)
        self.assertEqual(self.store.snapshot()["count"], 1)

    def test_same_identity_different_terminal_state_is_conflict(self):
        self.store.capture(self.null)
        positive = make_test_receipt(RUN, "SIGNAL_PRESERVED")
        with self.assertRaises(ReplayConflict):
            self.store.capture(positive)
        self.assertEqual(self.store.snapshot()["count"], 1)

    def test_two_valid_distinct_runs_remain_distinct(self):
        self.store.capture(self.null)
        another = make_test_receipt(
            SECOND_RUN, "NO_DURABLE_SIGNAL", reason="No material change a week later."
        )
        self.assertEqual(self.store.capture(another)["status"], "SYNTHETIC_ACCEPTED")
        self.assertEqual(self.store.snapshot()["count"], 2)

    def test_invalid_input_has_no_storage_effect(self):
        bad = deepcopy(self.null)
        bad["hall_receipt_claimed"] = True
        with self.assertRaises(ContractViolation):
            self.store.capture(bad)
        self.assertEqual(self.store.snapshot()["count"], 0)

    def test_append_only_database_rejects_direct_changes(self):
        self.store.capture(self.null)
        with sqlite3.connect(self.db_path) as connection:
            with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                connection.execute("UPDATE receipts SET terminal_state='forged'")
            with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                connection.execute("DELETE FROM receipts")
        self.assertEqual(self.store.snapshot()["count"], 1)

    def test_concurrent_replay_produces_exactly_one_insert(self):
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(self.store.capture, [self.null] * 5))
        self.assertEqual(
            [result["status"] for result in results].count("SYNTHETIC_ACCEPTED"), 1
        )
        self.assertEqual(
            [result["status"] for result in results].count("DUPLICATE_SUPPRESSED"), 4
        )
        self.assertEqual(self.store.snapshot()["count"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
