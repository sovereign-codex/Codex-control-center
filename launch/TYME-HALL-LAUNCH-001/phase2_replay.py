#!/usr/bin/env python3
"""Phase 2 terminal receipt *offline replay* for TYME-HALL-LAUNCH-001.

This module reuses the exact fields and boundaries of the Notion Phase 2
Terminal Receipt Contract. It is NOT an authenticated scheduler adapter, Notion
writer, D1 carrier, or source of production Phase 2 proof. No network I/O.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Mapping

PHASE = "SOVEREIGN_CIRCULATION_PILOT_001_PHASE2"
TASK_ID = "69950f3cd9308191ada10df6607f4c08"
INBOX = "HORIZON_SIGNAL_INBOX.md"
RECEIPT_PREFIX = "P2-RECEIPT-" + TASK_ID + "-"
STATES = frozenset(("SIGNAL_PRESERVED", "NO_DURABLE_SIGNAL", "PHASE2_HANDOFF_FAILED"))
FAILURE_STAGES = frozenset(("search", "create", "receipt"))
FALSE_FLAGS = (
    "duplicate_created",
    "downstream_wake_attempted",
    "work_created",
    "repository_mutation",
    "hall_receipt_claimed",
    "canon_claimed",
)
ALLOWED_FIELDS = frozenset((
    "phase", "receipt_id", "source_task_id", "scheduled_run", "terminal_state",
    "signal_id", "intake_surface", "reason", "failure_stage",
    "signal_not_persisted", "next_review_posture", "next_state",
    "phase2_proof_credit", *FALSE_FLAGS,
))
RECEIPT_ID_RE = re.compile(r"^P2-RECEIPT-([0-9a-f]{32})-([0-9]{8})-0815$")
SIGNAL_RE = re.compile(r"^SIGNAL-SCAI-P2-([0-9]{8})-001$")


class ContractViolation(ValueError):
    """An incoming receipt is not governed Phase 2 data."""


class ReplayConflict(ValueError):
    """One deterministic identity was seen with different validated bytes."""


def canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def scheduled_day(value: Any) -> str:
    if not isinstance(value, str):
        raise ContractViolation("scheduled_run must be a timezone-aware ISO timestamp")
    try:
        at = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ContractViolation("invalid scheduled_run") from exc
    if at.tzinfo is None or at.utcoffset() != timedelta(hours=-7):
        raise ContractViolation("scheduled_run must use America/Phoenix UTC-07:00")
    if (at.hour, at.minute, at.second, at.microsecond) != (8, 15, 0, 0):
        raise ContractViolation("scheduled_run must be 08:15:00 Arizona time")
    if at.weekday() != 0:
        raise ContractViolation("production monitor must run on Monday")
    return at.strftime("%Y%m%d")


def validate_terminal_receipt(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a known-contract receipt; no proof of producer or Notion readback."""
    if not isinstance(packet, dict):
        raise ContractViolation("receipt must be a JSON object")
    unknown = set(packet) - ALLOWED_FIELDS
    if unknown:
        raise ContractViolation("unknown/unreviewed fields: " + ",".join(sorted(unknown)))
    if packet.get("phase") != PHASE:
        raise ContractViolation("wrong Phase 2 contract")
    if packet.get("source_task_id") != TASK_ID:
        raise ContractViolation("not the production SCAI monitor task")
    day = scheduled_day(packet.get("scheduled_run"))
    expected_id = RECEIPT_PREFIX + day + "-0815"
    if packet.get("receipt_id") != expected_id:
        raise ContractViolation("receipt ID is not deterministic for source run")
    if packet.get("intake_surface") != INBOX:
        raise ContractViolation("competing or unrecognized intake surface")
    state = packet.get("terminal_state")
    if state not in STATES:
        raise ContractViolation("invalid Phase 2 terminal state")
    if packet.get("next_state") != "dormant":
        raise ContractViolation("downstream activation is prohibited")
    for flag in FALSE_FLAGS:
        if packet.get(flag) is not False:
            raise ContractViolation(f"forbidden consequence or missing false boundary: {flag}")
    if packet.get("phase2_proof_credit", False) is not False:
        raise ContractViolation("offline fixture cannot grant Phase 2 proof")
    if state == "SIGNAL_PRESERVED":
        expected_signal = "SIGNAL-SCAI-P2-" + day + "-001"
        if packet.get("signal_id") != expected_signal:
            raise ContractViolation("positive signal ID is missing or invalid")
        if packet.get("reason") or packet.get("failure_stage"):
            raise ContractViolation("positive event carries failure/null content")
        if packet.get("signal_not_persisted") is not False:
            raise ContractViolation("positive event contradicts signal persistence")
    elif state == "NO_DURABLE_SIGNAL":
        if not isinstance(packet.get("reason"), str) or not packet["reason"].strip():
            raise ContractViolation("null event requires an evidence-based reason")
        if packet.get("next_review_posture") != "continue_monitoring":
            raise ContractViolation("null event must continue monitoring")
        if packet.get("signal_id") or packet.get("failure_stage"):
            raise ContractViolation("null path must not invent a signal or failure")
        if packet.get("signal_not_persisted") is not True:
            raise ContractViolation("null path must explicitly leave signal absent")
    else:
        if packet.get("signal_id"):
            raise ContractViolation("failed handoff cannot claim a signal")
        if packet.get("failure_stage") not in FAILURE_STAGES:
            raise ContractViolation("failed handoff must locate failing stage")
        if not isinstance(packet.get("reason"), str) or not packet["reason"].strip():
            raise ContractViolation("failed handoff requires bounded error")
        if packet.get("signal_not_persisted") is not True:
            raise ContractViolation("failed handoff cannot claim persistence")
    return dict(packet)


def make_test_receipt(
    scheduled_run: str,
    terminal_state: str,
    *,
    reason: str = "",
    failure_stage: str | None = None,
) -> dict[str, Any]:
    """Produce a synthetic contract fixture, never a runtime receipt."""
    day = scheduled_day(scheduled_run)
    packet: dict[str, Any] = {
        "phase": PHASE,
        "receipt_id": RECEIPT_PREFIX + day + "-0815",
        "source_task_id": TASK_ID,
        "scheduled_run": scheduled_run,
        "terminal_state": terminal_state,
        "intake_surface": INBOX,
        "next_state": "dormant",
        "phase2_proof_credit": False,
        **{flag: False for flag in FALSE_FLAGS},
    }
    if terminal_state == "SIGNAL_PRESERVED":
        packet["signal_id"] = "SIGNAL-SCAI-P2-" + day + "-001"
        packet["signal_not_persisted"] = False
    if terminal_state == "NO_DURABLE_SIGNAL":
        packet["reason"] = reason
        packet["signal_not_persisted"] = True
        packet["next_review_posture"] = "continue_monitoring"
    if terminal_state == "PHASE2_HANDOFF_FAILED":
        packet["reason"] = reason
        packet["failure_stage"] = failure_stage
        packet["signal_not_persisted"] = True
    return validate_terminal_receipt(packet)


class ReplayStore:
    """Append-only local SQLite evidence; NOT Notion and NOT Cloudflare D1."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS receipts(
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    receipt_id TEXT NOT NULL UNIQUE,
                    payload_digest TEXT NOT NULL,
                    terminal_state TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS receipts_no_update
                BEFORE UPDATE ON receipts
                BEGIN SELECT RAISE(ABORT,'append-only receipts'); END;
                CREATE TRIGGER IF NOT EXISTS receipts_no_delete
                BEFORE DELETE ON receipts
                BEGIN SELECT RAISE(ABORT,'append-only receipts'); END;
            """)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database_path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=5000")
        return db

    def capture(self, proposed: Mapping[str, Any]) -> dict[str, Any]:
        packet = validate_terminal_receipt(proposed)
        body = canonical(packet)
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT sequence,payload_digest FROM receipts WHERE receipt_id=?",
                (packet["receipt_id"],),
            ).fetchone()
            if existing is not None:
                if existing["payload_digest"] != digest:
                    raise ReplayConflict("same run identity with different receipt bytes")
                status = "DUPLICATE_SUPPRESSED"
                sequence = existing["sequence"]
            else:
                cursor = db.execute(
                    "INSERT INTO receipts(receipt_id,payload_digest,terminal_state,payload_json)"
                    " VALUES(?,?,?,?)",
                    (packet["receipt_id"], digest, packet["terminal_state"], body),
                )
                sequence = cursor.lastrowid
                status = "SYNTHETIC_ACCEPTED"
        return {
            "status": status,
            "sequence": sequence,
            "receipt_id": packet["receipt_id"],
            "payload_sha256": digest,
            "phase2_proof_credit": False,
            "authority_effect": "none",
            "notion_receipt_verified": False,
            "cloudflare_carrier_verified": False,
        }

    def snapshot(self) -> dict[str, Any]:
        with self._connect() as db:
            integrity = db.execute("PRAGMA quick_check").fetchone()[0]
            count = db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
            names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
        return {
            "integrity": integrity,
            "count": count,
            "append_only": {"receipts_no_update", "receipts_no_delete"}.issubset(names),
        }
