"""Transport-only, synthetic acceptance specimen. NOT a deployed bridge.

No provider, model, shell, GitHub, Notion, or institutional receiver integration.
The caller's FixtureControl is TEST DATA, not an identity/authorization service.
Repair 001: shared static profile checks, fail-closed local decision records,
and stable nested-input / non-finite-number rejection. No live binding.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

MAX_BYTES = 65536
MODEL_MARKER = "none:deterministic-fixture"
EXECUTOR_MARKER = "fixture:byte-return-worker"
PROFILE_BLOB = "7ca63782a5b980b5a5ba8470eb92190b8c9c4c62"
DELIVERY_RECORD_VERSION = "bridge-fixture-delivery-local-v1"
OUTCOME_RECORD_VERSION = "bridge-fixture-outcome-local-v1"
NATIVE_STATUSES = frozenset({"complete", "partial", "refused", "failed"})


class BoundaryError(Exception):
    """Only stable error codes leave this specimen."""


def require(ok: bool, code: str) -> None:
    if not ok:
        raise BoundaryError(code)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      sort_keys=True, indent=2).encode("utf-8") + b"\n"


def decode(data: bytes) -> dict:
    def pairs(items: list[tuple[str, Any]]) -> dict:
        result: dict[str, Any] = {}
        for key, value in items:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result

    def constant(_: str) -> None:
        raise BoundaryError("nonfinite_json")

    def finite_float(text: str) -> float:
        number = float(text)
        require(math.isfinite(number), "nonfinite_json")
        return number

    require(isinstance(data, bytes), "json_bytes_required")
    require(len(data) <= MAX_BYTES, "byte_budget")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=constant, parse_float=finite_float)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise BoundaryError("invalid_json") from exc
    require(isinstance(value, dict), "object_required")
    return value


def read_bounded(path: Path, limit: int = MAX_BYTES) -> bytes:
    require(not path.is_symlink(), "symlink_rejected")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            require(stat.S_ISREG(info.st_mode), "regular_file_required")
            require(info.st_size <= limit, "byte_budget")
            data = stream.read(limit + 1)
    except OSError as exc:
        raise BoundaryError("read_failed") from exc
    require(len(data) <= limit, "byte_budget")
    return data


def write_exclusive(path: Path, data: bytes) -> None:
    require(len(data) <= MAX_BYTES, "byte_budget")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise BoundaryError("overwrite_rejected") from exc
    except OSError as exc:
        raise BoundaryError("write_failed") from exc


@dataclass
class Budget:
    seconds: float = 5.0
    clock: Callable[[], float] = time.monotonic

    def __post_init__(self) -> None:
        require(type(self.seconds) in (int, float) and
                math.isfinite(self.seconds) and self.seconds > 0, "invalid_budget")
        self.started = self.clock()
        require(type(self.started) in (int, float) and math.isfinite(self.started),
                "invalid_clock")

    def check(self) -> None:
        current = self.clock()
        require(type(current) in (int, float) and math.isfinite(current), "invalid_clock")
        elapsed = current - self.started
        require(math.isfinite(elapsed) and 0 <= elapsed <= self.seconds,
                "elapsed_budget")


@dataclass(frozen=True)
class FixtureControl:
    """Harness-local control; never inferred from the packet or its prose."""
    packet_id: str
    packet_sha256: str
    expires_at: str
    permitted: bool = False
    profile_blob: str = PROFILE_BLOB

    def check(self, now: datetime) -> None:
        require(self.permitted is True, "fixture_not_permitted")
        require(self.profile_blob == PROFILE_BLOB, "profile_unresolved")
        require(isinstance(self.packet_id, str) and bool(self.packet_id.strip()),
                "packet_identity_mismatch")
        require(_sha256_string(self.packet_sha256), "invalid_expected_digest")
        require(isinstance(self.expires_at, str), "invalid_expiry")
        require(isinstance(now, datetime), "invalid_now")
        try:
            deadline = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            require(deadline.tzinfo is not None and now.tzinfo is not None,
                    "timezone_required")
        except (ValueError, TypeError) as exc:
            raise BoundaryError("invalid_expiry") from exc
        require(now < deadline, "fixture_expired")


def _sha256_string(value: Any) -> bool:
    return (isinstance(value, str) and len(value) == 64 and
            all(char in "0123456789abcdef" for char in value))


def _fixture_input(packet: dict) -> str:
    inputs = packet.get("inputs")
    require(isinstance(inputs, list) and len(inputs) == 1 and
            isinstance(inputs[0], dict) and
            inputs[0].get("type") == "synthetic_text" and
            isinstance(inputs[0].get("value"), str), "fixture_input")
    return inputs[0]["value"]


def validate_packet_profile(packet: dict, *, profile_blob: str = PROFILE_BLOB) -> None:
    """Pure selected-fixture conformance, NOT an authorization or truth check.

    The profile is pinned in code/caller configuration, never selected by packet
    prose. Historical custody verification needs no current permission or clock.
    This is a narrow synthetic profile, not the full institutional contract.
    """
    require(profile_blob == PROFILE_BLOB, "profile_unresolved")
    require(isinstance(packet, dict), "object_required")
    require(packet.get("packet_version") == "executor-packet-v1", "packet_version")
    require("return_contract" not in packet, "legacy_contract_ambiguous")
    require(isinstance(packet.get("model_return_contract"), dict) and
            isinstance(packet.get("envelope_contract"), dict), "split_contract_required")
    require(isinstance(packet.get("packet_id"), str) and
            bool(packet["packet_id"].strip()), "packet_identity_mismatch")
    require(packet.get("sensitivity") == "synthetic", "non_synthetic_rejected")
    require(packet.get("authority_ceiling") == "bounded_execute", "ceiling_changed")
    require(packet.get("teardown_required") is True, "teardown_required")
    requirements = packet.get("executor_requirements")
    require(requirements == {"capabilities": ["synthetic_transport_fixture"],
                             "preferred_model": None, "preferred_accelerator": None},
            "capability_scope_changed")
    require(packet["model_return_contract"].get("json_only") is True and
            packet["model_return_contract"] == {
                "required_fields": ["packet_id", "summary", "status"], "json_only": True},
            "model_contract_changed")
    require(packet["envelope_contract"] == {
        "event_type": "external_executor_return", "required_fields": [
            "event_type", "packet_id", "executor", "model", "timestamp_utc",
            "execution_status", "model_output"]}, "envelope_contract_changed")
    _fixture_input(packet)
    require(isinstance(packet.get("task"), str) and bool(packet["task"].strip()),
            "fixture_task")
    require(isinstance(packet.get("commission_ref"), str) and
            bool(packet["commission_ref"].strip()), "fixture_commission")
    require(isinstance(packet.get("constraints"), list) and
            all(isinstance(item, str) for item in packet["constraints"]),
            "fixture_constraints")
    require(set(packet) == {
        "packet_version", "packet_id", "commission_ref", "task", "sensitivity",
        "authority_ceiling", "executor_requirements", "constraints", "inputs",
        "model_return_contract", "envelope_contract", "teardown_required"},
        "fixture_packet_fields")


def inspect_packet(raw: bytes, control: FixtureControl, now: datetime) -> dict:
    """Check present test permission, byte identity, then the pure profile."""
    require(isinstance(control, FixtureControl), "invalid_fixture_control")
    control.check(now)
    require(digest(raw) == control.packet_sha256, "packet_hash_mismatch")
    packet = decode(raw)
    require(packet.get("packet_id") == control.packet_id, "packet_identity_mismatch")
    validate_packet_profile(packet, profile_blob=control.profile_blob)
    return packet


def _delivery_record(claim: dict, claim_raw: bytes) -> dict:
    return {"record_version": DELIVERY_RECORD_VERSION, "state": "prepared",
            "packet_id": claim["packet_id"], "packet_sha256": claim["packet_sha256"],
            "claim_sha256": digest(claim_raw), "profile_blob": PROFILE_BLOB,
            "transport_only": True}


def _outcome_record(delivery_raw: bytes, *, state: str, reason: str) -> dict:
    return {"record_version": OUTCOME_RECORD_VERSION, "state": state,
            "reason": reason, "delivery_record_sha256": digest(delivery_raw),
            "transport_only": True}


def _require_record(observed: dict, expected: dict, code: str) -> None:
    # Explicit identity check avoids Python's True == 1 equality shortcut.
    require(observed.get("transport_only") is True and observed == expected, code)


def _record_failure(target: Path, delivery_raw: bytes, reason: str) -> None:
    """Best-effort stable failure evidence; never repairs or overwrites a job.

    If this write fails, no outcome was published and replay remains held.
    No path, exception text, credentials, or permission grant are recorded here.
    """
    if reason not in {"elapsed_budget", "invalid_clock", "write_failed",
                      "read_failed", "transfer_mismatch", "decision_mismatch",
                      "overwrite_rejected", "decision_publish_failed"}:
        reason = "local_boundary_failure"
    try:
        write_exclusive(target / "held.json", encode(_outcome_record(
            delivery_raw, state="held", reason=reason)))
    except BoundaryError:
        # Absence of outcome.json is independently enough to prevent success.
        pass


def _replay(target: Path, raw: bytes, claim_expected: dict, budget: Budget) -> str:
    """Read-only replay; incomplete/corrupt records never trigger redelivery."""
    claim_raw = read_bounded(target / "claim.json")
    claim = decode(claim_raw)
    require(claim == claim_expected, "identity_collision")
    delivery_path = target / "delivered.json"
    require(os.path.lexists(delivery_path), "interrupted_hold")
    delivery_raw = read_bounded(delivery_path)
    _require_record(decode(delivery_raw), _delivery_record(claim, claim_raw),
                    "delivery_record_invalid")
    require(read_bounded(target / "packet.json") == raw, "stored_packet_mismatch")
    held_path = target / "held.json"
    if os.path.lexists(held_path):
        held = decode(read_bounded(held_path))
        reason = held.get("reason")
        require(isinstance(reason, str) and reason in {
            "elapsed_budget", "invalid_clock", "write_failed", "read_failed",
            "transfer_mismatch", "decision_mismatch", "overwrite_rejected",
            "decision_publish_failed", "local_boundary_failure"}, "held_record_invalid")
        _require_record(held, _outcome_record(delivery_raw, state="held", reason=reason),
                        "held_record_invalid")
        raise BoundaryError("delivery_held_" + reason)
    outcome_path = target / "outcome.json"
    require(os.path.lexists(outcome_path), "interrupted_hold")
    _require_record(decode(read_bounded(outcome_path)), _outcome_record(
        delivery_raw, state="delivered", reason="deadline_checked_before_publication"),
        "outcome_record_invalid")
    budget.check()
    return "duplicate_suppressed"


def stage_once(source: Path, root: Path, control: FixtureControl,
               now: datetime, budget: Budget | None = None) -> tuple[str, Path]:
    """Single-writer file-courier rehearsal, NOT an exactly-once remote queue.

    delivered.json records PREPARATION, not completion. Completion requires a
    separately published outcome.json, bound to the prepared record and claim.
    All payload and decision preparation/read-back is deadline-checked. Publishing
    outcome.json with one no-overwrite hard link is the local commit point. That
    syscall and return latency are not preemptible or covered by an end-to-end
    wall-clock promise. Failure recording is deliberately allowed after timeout.
    fsync(file) is used; directory/power-loss durability is NOT claimed.
    """
    budget = budget or Budget()
    budget.check()
    raw = read_bounded(source)
    inspect_packet(raw, control, now)
    budget.check()
    target = root / digest(control.packet_id.encode("utf-8"))
    claim = {"packet_id": control.packet_id, "packet_sha256": control.packet_sha256}
    claim_raw = encode(claim)
    delivery_raw = encode(_delivery_record(claim, claim_raw))
    try:
        target.mkdir(mode=0o700)
    except FileExistsError:
        require(not target.is_symlink() and target.is_dir(), "unsafe_job_directory")
        return _replay(target, raw, claim, budget), target
    except OSError as exc:
        raise BoundaryError("job_directory_failed") from exc
    try:
        write_exclusive(target / "claim.json", claim_raw)
        write_exclusive(target / "packet.json", raw)
        require(read_bounded(target / "packet.json") == raw, "transfer_mismatch")
        budget.check()
        write_exclusive(target / "delivered.json", delivery_raw)
        require(read_bounded(target / "delivered.json") == delivery_raw, "decision_mismatch")
        budget.check()  # Preserves R07's post-delivery timeout checkpoint.
        outcome_raw = encode(_outcome_record(
            delivery_raw, state="delivered", reason="deadline_checked_before_publication"))
        pending_path = target / "outcome.pending.json"
        write_exclusive(pending_path, outcome_raw)
        require(read_bounded(pending_path) == outcome_raw, "decision_mismatch")
        budget.check()  # Includes the final decision-file write and read-back.
        try:
            # Same controlled local directory, single writer, fail if unsupported.
            # No overwrite; unpublished partial writes cannot look completed.
            os.link(pending_path, target / "outcome.json", follow_symlinks=False)
        except OSError as exc:
            raise BoundaryError("decision_publish_failed") from exc
    except BoundaryError as exc:
        _record_failure(target, delivery_raw, str(exc))
        raise
    # Keep the preparation record for diagnosis. No cleanup I/O after commit.
    return "delivered", target


def fixture_return(packet_path: Path, destination: Path, status: str = "complete") -> None:
    """Deterministic test double, NOT an inference completion."""
    require(isinstance(status, str) and status in NATIVE_STATUSES, "fixture_status")
    packet = decode(read_bounded(packet_path))
    # Intentionally a test-data builder, not a profile acceptance gate. Review
    # tests use it to construct returns for correctly hashed invalid packets.
    payload = _fixture_input(packet)
    require(isinstance(packet.get("packet_id"), str), "packet_identity_mismatch")
    inner = {"packet_id": packet["packet_id"],
             "summary": payload, "status": "fixture_only"}
    outer = {"event_type": "external_executor_return", "packet_id": packet["packet_id"],
             "executor": EXECUTOR_MARKER, "model": MODEL_MARKER,
             "timestamp_utc": "2026-09-27T00:00:00Z", "accelerator": "none",
             "model_output": encode(inner).decode("utf-8"), "execution_status": status,
             "artifacts": [], "warnings": ["Synthetic test double. No model invoked."]}
    # Deliberately different whitespace/newlines from canonical JSON.
    raw = json.dumps(outer, ensure_ascii=False, allow_nan=False, indent=3).replace(
        "\n", "\r\n").encode("utf-8") + b"\r\n"
    write_exclusive(destination, raw)


def collect_return(source: Path, custody: Path, expected_sha256: str,
                   budget: Budget | None = None) -> None:
    """Opaque bytes only. No schema verdict or institutional acceptance here."""
    budget = budget or Budget()
    budget.check()
    raw = read_bounded(source)
    require(digest(raw) == expected_sha256, "return_hash_mismatch")
    write_exclusive(custody / "return.json", raw)
    require(read_bounded(custody / "return.json") == raw, "custody_mismatch")
    budget.check()


def verify_custody(custody: Path, expected_path: Path, *,
                   profile_blob: str = PROFILE_BLOB) -> dict:
    """Read-back verifier, callable in a fresh process. No promotion or writes.

    Expected values are harness-controller inputs outside the worker/custody bundle.
    Same-account process separation is NOT a production security boundary.
    """
    require(profile_blob == PROFILE_BLOB, "profile_unresolved")
    expected = decode(read_bounded(expected_path))
    require(set(expected) == {"packet_id", "packet_sha256", "return_sha256", "executor"},
            "expected_fields")
    require(isinstance(expected["packet_id"], str) and bool(expected["packet_id"].strip()),
            "expected_identity")
    require(_sha256_string(expected["packet_sha256"]) and
            _sha256_string(expected["return_sha256"]), "invalid_expected_digest")
    require(expected["executor"] == EXECUTOR_MARKER, "executor_identity_mismatch")
    packet_raw = read_bounded(custody / "packet.json")
    return_raw = read_bounded(custody / "return.json")
    require(digest(packet_raw) == expected["packet_sha256"], "packet_hash_mismatch")
    require(digest(return_raw) == expected["return_sha256"], "return_hash_mismatch")
    packet, result = decode(packet_raw), decode(return_raw)
    validate_packet_profile(packet, profile_blob=profile_blob)
    require(packet.get("packet_id") == expected["packet_id"] == result.get("packet_id"),
            "return_identity_mismatch")
    for name in packet["envelope_contract"]["required_fields"]:
        require(name in result, "envelope_field_missing")
    require(result.get("event_type") == "external_executor_return", "event_type")
    require(result.get("executor") == expected["executor"] == EXECUTOR_MARKER,
            "executor_identity_mismatch")
    require(result.get("model") == MODEL_MARKER, "false_model_claim")
    require(isinstance(result.get("execution_status"), str) and
            result["execution_status"] in NATIVE_STATUSES, "unknown_execution_status")
    require(isinstance(result.get("timestamp_utc"), str), "invalid_return_timestamp")
    try:
        observed_at = datetime.fromisoformat(result["timestamp_utc"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise BoundaryError("invalid_return_timestamp") from exc
    require(observed_at.tzinfo is not None, "invalid_return_timestamp")
    require(isinstance(result.get("artifacts"), list) and result["artifacts"] == [],
            "fixture_artifacts")
    require(isinstance(result.get("warnings"), list) and
            all(isinstance(warning, str) for warning in result["warnings"]),
            "fixture_warnings")
    require(result.get("accelerator") == "none", "false_accelerator_claim")
    require(isinstance(result.get("model_output"), str), "model_output_type")
    try:
        inner_raw = result["model_output"].encode("utf-8")
    except UnicodeError as exc:
        raise BoundaryError("invalid_model_output_encoding") from exc
    inner = decode(inner_raw)
    for name in packet["model_return_contract"]["required_fields"]:
        require(name in inner, "model_field_missing")
    require(inner["packet_id"] == expected["packet_id"], "inner_identity_mismatch")
    require(inner["status"] == "fixture_only", "false_inference_claim")
    require(inner["summary"] == packet["inputs"][0]["value"], "raw_payload_changed")
    # Only the local test report. Never reused as an actual CIT/TRACE receipt.
    return {"specimen": "BRIDGE_TRANSPORT_ACCEPTANCE_001", "schema_check": "passed",
            "profile_blob": profile_blob, "validation_scope": "synthetic_fixture_only",
            "authorization_rechecked": False,
            "raw_execution_status": result["execution_status"],
            "byte_custody_check": "passed", "packet_sha256": digest(packet_raw),
            "return_sha256": digest(return_raw), "model_execution": "not_performed",
            "institutional_acceptance": "not_assessed", "authority_effect": "none",
            "hall_receipt_claimed": False, "handoff_ready": False}


def block_python_network() -> None:
    """Defense-in-depth for this Python-only specimen; not OS isolation."""
    def guard(event: str, _: tuple) -> None:
        if event.startswith("socket."):
            raise BoundaryError("network_forbidden")
    sys.addaudithook(guard)


def main() -> int:
    block_python_network()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["verify"])
    parser.add_argument("--custody", type=Path, required=True)
    parser.add_argument("--expected", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(encode(verify_custody(args.custody, args.expected)).decode("utf-8"), end="")
    except (BoundaryError, KeyError, TypeError) as exc:
        code = str(exc) if isinstance(exc, BoundaryError) else "invalid_fixture_shape"
        print(json.dumps({"error_code": code, "authority_effect": "none"}))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
