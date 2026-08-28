#!/usr/bin/env python3
"""Hall Core 0: signed GitHub observation -> append-only Hall event."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import signal
import sqlite3
import threading
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

VERSION = "0.1.0"
DELIVERY_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,200}$")
EVENT_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
SIG_RE = re.compile(r"^sha256=([0-9a-f]{64})$")
PROHIBITED = [
    "repository_mutation", "workflow_dispatch", "work_promotion",
    "participant_binding", "execution_authorization", "canon_promotion",
]
LOG = logging.getLogger("hall-core")


class BadRequest(Exception):
    pass


class BadSignature(Exception):
    pass


class ReplayMismatch(Exception):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_hash(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def nested(value: Any, *path: str) -> Any:
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def verify(secret: str, raw: bytes, signature: str | None) -> None:
    if not secret:
        raise RuntimeError("HALL_GITHUB_WEBHOOK_SECRET is not configured")
    match = SIG_RE.fullmatch((signature or "").strip())
    if not match:
        raise BadSignature("missing or malformed X-Hub-Signature-256")
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, match.group(1)):
        raise BadSignature("invalid GitHub webhook signature")


def normalize(delivery: str, event_name: str, payload: dict[str, Any], raw: bytes,
              adapter_id: str, node_id: str, accepted_at: str | None = None) -> dict[str, Any]:
    if not DELIVERY_RE.fullmatch(delivery):
        raise BadRequest("invalid X-GitHub-Delivery")
    if not EVENT_RE.fullmatch(event_name):
        raise BadRequest("invalid X-GitHub-Event")
    if not isinstance(payload, dict):
        raise BadRequest("payload must be a JSON object")

    accepted_at = accepted_at or now()
    repo = str(nested(payload, "repository", "full_name") or "unknown-repository")
    sender = str(nested(payload, "sender", "login") or "unknown")
    sender_type = str(nested(payload, "sender", "type") or "").lower()
    actor_type = "human" if sender_type == "user" else "service" if sender_type == "bot" else "external"
    number = payload.get("number") or nested(payload, "pull_request", "number") or nested(payload, "issue", "number")
    source_record = f"github://{repo}/{event_name}" + (f"/{number}" if number else "")
    occurred_at = (
        nested(payload, "pull_request", "updated_at")
        or nested(payload, "issue", "updated_at")
        or nested(payload, "workflow_run", "updated_at")
        or nested(payload, "head_commit", "timestamp")
        or accepted_at
    )
    links = []
    for candidate in (
        nested(payload, "repository", "html_url"), nested(payload, "pull_request", "html_url"),
        nested(payload, "issue", "html_url"), nested(payload, "workflow_run", "html_url"),
    ):
        if isinstance(candidate, str) and candidate.startswith("https://") and candidate not in links:
            links.append(candidate)
    artifacts = [f"repo:{repo}"]
    for sha in (nested(payload, "pull_request", "head", "sha"), nested(payload, "workflow_run", "head_sha"), payload.get("after")):
        if isinstance(sha, str) and sha and set(sha) != {"0"}:
            value = f"commit:{sha}"
            if value not in artifacts:
                artifacts.append(value)

    event_id = f"evt:github:{delivery}"
    digest = content_hash(raw)
    return {"hall_event": {
        "envelope_version": "0.1",
        "event_id": event_id,
        "event_type": f"github.{event_name}",
        "occurred_at": str(occurred_at),
        "accepted_at": accepted_at,
        "lineage": {
            "lineage_id": f"github:{repo}",
            "parent_event_id": None,
            "correlation_id": f"github:{repo}:{event_name}:{number or delivery}",
        },
        "identity": {"actor_id": f"github:{sender}", "actor_type": actor_type, "adapter_id": adapter_id},
        "provenance": {
            "source_surface": "github", "source_record": source_record,
            "artifact_ids": artifacts, "evidence_links": links,
        },
        "authority": {
            "posture": "observe",
            "authorization_basis": "Verified transport authenticity; no consequence authority follows.",
            "authorized_actions": [], "prohibited_actions": PROHIBITED, "gate_id": "",
        },
        "payload": {
            "summary": f"GitHub {event_name} observed for {repo} from {sender}",
            "content_ref": f"hall-db://{node_id}/events/{event_id}/raw-payload",
            "content_hash": digest,
        },
        "state": {
            "recorded_state": "github_webhook_accepted",
            "current_resolution": "accepted_observation",
            "execution_state": "not_started",
            "verification_state": "unverified",
        },
        "return": {
            "evidence_ids": [f"github-delivery:{delivery}", digest],
            "return_event_ids": [],
            "next_valid_action": "route_or_review_under_separate_hall_gate",
        },
    }}


class Store:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS events(
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    adapter_id TEXT NOT NULL,
                    delivery_id TEXT NOT NULL,
                    body_hash TEXT NOT NULL,
                    accepted_at TEXT NOT NULL,
                    envelope TEXT NOT NULL,
                    raw_payload BLOB NOT NULL,
                    UNIQUE(adapter_id, delivery_id)
                );
                CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
                BEGIN SELECT RAISE(ABORT, 'events is append-only'); END;
                CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
                BEGIN SELECT RAISE(ABORT, 'events is append-only'); END;
            """)

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        return db

    def ingest(self, adapter_id: str, delivery: str, envelope: dict[str, Any], raw_body: bytes) -> dict[str, Any]:
        event = envelope["hall_event"]
        digest = event["payload"]["content_hash"]
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT sequence,event_id,body_hash FROM events WHERE adapter_id=? AND delivery_id=?",
                (adapter_id, delivery),
            ).fetchone()
            if existing:
                if existing["body_hash"] != digest:
                    raise ReplayMismatch("delivery id was replayed with different bytes")
                return {"status": "duplicate", "sequence": existing["sequence"], "event_id": existing["event_id"]}
            cursor = db.execute(
                "INSERT INTO events(event_id,adapter_id,delivery_id,body_hash,accepted_at,envelope,raw_payload) VALUES(?,?,?,?,?,?,?)",
                (event["event_id"], adapter_id, delivery, digest, event["accepted_at"], canonical(envelope), sqlite3.Binary(raw_body)),
            )
            return {"status": "accepted", "sequence": cursor.lastrowid, "event_id": event["event_id"]}

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 100))
        with self.connect() as db:
            rows = db.execute("SELECT sequence,envelope FROM events ORDER BY sequence DESC LIMIT ?", (limit,)).fetchall()
        return [{"sequence": row["sequence"], "envelope": json.loads(row["envelope"])} for row in rows]

    def get(self, event_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT sequence,envelope FROM events WHERE event_id=?", (event_id,)).fetchone()
        return None if not row else {"sequence": row["sequence"], "envelope": json.loads(row["envelope"])}

    def snapshot(self) -> dict[str, Any]:
        with self.connect() as db:
            integrity = db.execute("PRAGMA quick_check").fetchone()[0]
            count = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            last = db.execute("SELECT sequence,event_id,accepted_at FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
            triggers = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
        return {
            "database_integrity": integrity,
            "append_only_triggers": {"events_no_update", "events_no_delete"}.issubset(triggers),
            "event_count": count,
            "last_sequence": last["sequence"] if last else 0,
            "last_event_id": last["event_id"] if last else None,
            "last_accepted_at": last["accepted_at"] if last else None,
        }


class Runtime:
    def __init__(self):
        self.node_id = os.getenv("HALL_NODE_ID", "hall-core-0")
        self.commit = os.getenv("HALL_BUILD_COMMIT", "unknown")
        self.secret = os.getenv("HALL_GITHUB_WEBHOOK_SECRET", "")
        self.read_token = os.getenv("HALL_READ_TOKEN", "")
        self.adapter_id = os.getenv("HALL_GITHUB_ADAPTER_ID", "github-webhook-v0")
        self.max_body = int(os.getenv("HALL_MAX_BODY_BYTES", "1048576"))
        self.store = Store(os.getenv("HALL_DB_PATH", "/var/lib/hall-core/hall.db"))

    def readiness(self) -> tuple[bool, dict[str, Any]]:
        snapshot = self.store.snapshot()
        missing = [name for name, value in (
            ("HALL_GITHUB_WEBHOOK_SECRET", self.secret), ("HALL_READ_TOKEN", self.read_token)
        ) if not value]
        ready = not missing and snapshot["database_integrity"] == "ok" and snapshot["append_only_triggers"]
        return ready, {
            "status": "ready" if ready else "degraded", "node_id": self.node_id,
            "runtime_version": VERSION, "build_commit": self.commit,
            "missing_configuration": missing,
            "database_integrity": snapshot["database_integrity"],
            "append_only_triggers": snapshot["append_only_triggers"],
        }


class Server(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address: tuple[str, int], runtime: Runtime):
        super().__init__(address, Handler)
        self.runtime = runtime


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "HallCore/0.1"

    @property
    def runtime(self) -> Runtime:
        return self.server.runtime  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        LOG.info("%s %s %s", self.client_address[0], self.command, fmt % args)

    def send_json(self, status: int, value: Any) -> None:
        body = canonical(value).encode()
        self.send_response(status)
        for key, val in (
            ("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "DENY"), ("Referrer-Policy", "no-referrer"),
        ):
            self.send_header(key, val)
        self.end_headers()
        self.wfile.write(body)

    def error(self, status: int, code: str, message: str) -> None:
        self.send_json(status, {"error": code, "message": message})

    def authorized(self) -> bool:
        bearer = self.headers.get("Authorization", "")
        token = bearer[7:] if bearer.startswith("Bearer ") else ""
        return bool(self.runtime.read_token and token and hmac.compare_digest(token, self.runtime.read_token))

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlsplit(self.path)
        if parsed.path == "/healthz":
            self.send_json(200, {"status": "alive", "node_id": self.runtime.node_id, "runtime_version": VERSION, "build_commit": self.runtime.commit})
            return
        if parsed.path == "/readyz":
            ready, value = self.runtime.readiness()
            self.send_json(200 if ready else 503, value)
            return
        if not self.authorized():
            self.error(401, "unauthorized", "valid Hall read token required")
            return
        if parsed.path == "/v0/snapshot":
            self.send_json(200, {"node_id": self.runtime.node_id, "authority_ceiling": "observe", **self.runtime.store.snapshot()})
            return
        if parsed.path == "/v0/events":
            try:
                limit = int(parse_qs(parsed.query).get("limit", ["50"])[0])
            except ValueError:
                self.error(400, "invalid_query", "limit must be an integer")
                return
            self.send_json(200, {"events": self.runtime.store.list(limit), "authority_posture": "read_only_projection"})
            return
        if parsed.path.startswith("/v0/events/"):
            value = self.runtime.store.get(unquote(parsed.path[len("/v0/events/"):]))
            self.send_json(200, value) if value else self.error(404, "event_not_found", "event not found")
            return
        self.error(404, "not_found", "route not found")

    def do_POST(self) -> None:  # noqa: N802
        if urlsplit(self.path).path != "/v0/webhooks/github":
            self.error(404, "not_found", "route not found")
            return
        try:
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                raise BadRequest("Content-Type must be application/json")
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > self.runtime.max_body:
                raise BadRequest("invalid request body length")
            raw = self.rfile.read(length)
            verify(self.runtime.secret, raw, self.headers.get("X-Hub-Signature-256"))
            delivery = self.headers.get("X-GitHub-Delivery", "").strip()
            event_name = self.headers.get("X-GitHub-Event", "").strip()
            payload = json.loads(raw.decode())
            envelope = normalize(delivery, event_name, payload, raw, self.runtime.adapter_id, self.runtime.node_id)
            result = self.runtime.store.ingest(self.runtime.adapter_id, delivery, envelope, raw)
            self.send_json(202 if result["status"] == "accepted" else 200, {
                **result, "authority_posture": "observe", "institutional_effect": "accepted_event_only",
                "next_valid_action": "route_or_review_under_separate_hall_gate",
            })
        except RuntimeError as exc:
            self.error(503, "not_ready", str(exc))
        except BadSignature as exc:
            self.error(401, "invalid_signature", str(exc))
        except ReplayMismatch as exc:
            self.error(409, "replay_mismatch", str(exc))
        except (BadRequest, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            self.error(400, "invalid_request", str(exc))
        except sqlite3.Error:
            LOG.exception("database error")
            self.error(500, "database_error", "event was not accepted")

    def do_PUT(self) -> None:  # noqa: N802
        self.error(405, "method_not_allowed", "Hall Core 0 has no mutation API")
    do_PATCH = do_PUT
    do_DELETE = do_PUT


def main() -> None:
    logging.basicConfig(level=os.getenv("HALL_LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
    runtime = Runtime()
    server = Server((os.getenv("HALL_BIND", "0.0.0.0"), int(os.getenv("HALL_PORT", "8080"))), runtime)
    def stop(signum: int, _frame: Any) -> None:
        LOG.info("received signal %s", signum)
        threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    LOG.info("Hall Core 0 listening; node=%s commit=%s", runtime.node_id, runtime.commit)
    server.serve_forever()


if __name__ == "__main__":
    main()
