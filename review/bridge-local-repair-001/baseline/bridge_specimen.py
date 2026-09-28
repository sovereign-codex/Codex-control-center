"""Transport-only, synthetic acceptance specimen. NOT a deployed bridge.

No provider, model, shell, GitHub, Notion, or institutional receiver integration.
The caller's FixtureControl is TEST DATA, not an identity/authorization service.
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

    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=constant)
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
        require(math.isfinite(self.seconds) and self.seconds > 0, "invalid_budget")
        self.started = self.clock()

    def check(self) -> None:
        elapsed = self.clock() - self.started
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
        try:
            deadline = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            require(deadline.tzinfo is not None and now.tzinfo is not None,
                    "timezone_required")
        except (ValueError, TypeError) as exc:
            raise BoundaryError("invalid_expiry") from exc
        require(now < deadline, "fixture_expired")


def inspect_packet(raw: bytes, control: FixtureControl, now: datetime) -> dict:
    control.check(now)
    require(digest(raw) == control.packet_sha256, "packet_hash_mismatch")
    packet = decode(raw)
    require(packet.get("packet_id") == control.packet_id, "packet_identity_mismatch")
    require(packet.get("packet_version") == "executor-packet-v1", "packet_version")
    require("return_contract" not in packet, "legacy_contract_ambiguous")
    require(isinstance(packet.get("model_return_contract"), dict) and
            isinstance(packet.get("envelope_contract"), dict), "split_contract_required")
    require(packet.get("sensitivity") == "synthetic", "non_synthetic_rejected")
    require(packet.get("authority_ceiling") == "bounded_execute", "ceiling_changed")
    require(packet.get("teardown_required") is True, "teardown_required")
    requirements = packet.get("executor_requirements", {})
    require(requirements == {"capabilities": ["synthetic_transport_fixture"],
                             "preferred_model": None, "preferred_accelerator": None},
            "capability_scope_changed")
    require(packet["model_return_contract"] == {
        "required_fields": ["packet_id", "summary", "status"], "json_only": True},
        "model_contract_changed")
    require(packet["envelope_contract"] == {
        "event_type": "external_executor_return", "required_fields": [
            "event_type", "packet_id", "executor", "model", "timestamp_utc",
            "execution_status", "model_output"]}, "envelope_contract_changed")
    require(isinstance(packet.get("inputs"), list) and len(packet["inputs"]) == 1
            and packet["inputs"][0].get("type") == "synthetic_text"
            and isinstance(packet["inputs"][0].get("value"), str), "fixture_input")
    return packet


def stage_once(source: Path, root: Path, control: FixtureControl,
               now: datetime, budget: Budget | None = None) -> tuple[str, Path]:
    """Single-writer file-courier rehearsal. No network dispatch or execution.

    A partial claim is held, not retried. This is not an exactly-once remote queue.
    """
    budget = budget or Budget()
    budget.check()
    raw = read_bounded(source)
    inspect_packet(raw, control, now)
    budget.check()
    target = root / digest(control.packet_id.encode("utf-8"))
    try:
        target.mkdir(mode=0o700)
    except FileExistsError:
        require(not target.is_symlink() and target.is_dir(), "unsafe_job_directory")
        claim = decode(read_bounded(target / "claim.json"))
        require(claim == {"packet_id": control.packet_id,
                          "packet_sha256": control.packet_sha256}, "identity_collision")
        require((target / "delivered.json").is_file(), "interrupted_hold")
        require(read_bounded(target / "packet.json") == raw, "stored_packet_mismatch")
        budget.check()
        return "duplicate_suppressed", target
    write_exclusive(target / "claim.json", encode({
        "packet_id": control.packet_id, "packet_sha256": control.packet_sha256}))
    write_exclusive(target / "packet.json", raw)
    require(read_bounded(target / "packet.json") == raw, "transfer_mismatch")
    budget.check()
    write_exclusive(target / "delivered.json", encode({"transport_only": True}))
    budget.check()  # Includes final local processing, not just source reading.
    return "delivered", target


def fixture_return(packet_path: Path, destination: Path, status: str = "complete") -> None:
    """Deterministic test double, NOT an inference completion."""
    require(status in {"complete", "partial", "refused", "failed"}, "fixture_status")
    packet = decode(read_bounded(packet_path))
    inner = {"packet_id": packet["packet_id"],
             "summary": packet["inputs"][0]["value"], "status": "fixture_only"}
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


def verify_custody(custody: Path, expected_path: Path) -> dict:
    """Read-back verifier, callable in a fresh process. No promotion or writes.

    Expected values are harness-controller inputs outside the worker/custody bundle.
    Same-account process separation is NOT a production security boundary.
    """
    expected = decode(read_bounded(expected_path))
    packet_raw = read_bounded(custody / "packet.json")
    return_raw = read_bounded(custody / "return.json")
    require(digest(packet_raw) == expected["packet_sha256"], "packet_hash_mismatch")
    require(digest(return_raw) == expected["return_sha256"], "return_hash_mismatch")
    packet, result = decode(packet_raw), decode(return_raw)
    require(packet.get("packet_id") == expected["packet_id"] == result.get("packet_id"),
            "return_identity_mismatch")
    require("return_contract" not in packet, "legacy_contract_ambiguous")
    require(isinstance(packet.get("envelope_contract"), dict) and
            isinstance(packet.get("model_return_contract"), dict), "split_contract_required")
    for name in packet["envelope_contract"]["required_fields"]:
        require(name in result, "envelope_field_missing")
    require(result.get("event_type") == "external_executor_return", "event_type")
    require(result.get("executor") == expected["executor"] == EXECUTOR_MARKER,
            "executor_identity_mismatch")
    require(result.get("model") == MODEL_MARKER, "false_model_claim")
    require(result.get("execution_status") in {"complete", "partial", "refused", "failed"},
            "unknown_execution_status")
    require(isinstance(result.get("model_output"), str), "model_output_type")
    inner = decode(result["model_output"].encode("utf-8"))
    for name in packet["model_return_contract"]["required_fields"]:
        require(name in inner, "model_field_missing")
    require(inner["packet_id"] == expected["packet_id"], "inner_identity_mismatch")
    require(inner["status"] == "fixture_only", "false_inference_claim")
    require(inner["summary"] == packet["inputs"][0]["value"], "raw_payload_changed")
    # Only the local test report. Never reused as an actual CIT/TRACE receipt.
    return {"specimen": "BRIDGE_TRANSPORT_ACCEPTANCE_001", "schema_check": "passed",
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
