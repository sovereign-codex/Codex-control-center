from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("hall_core_app", ROOT / "services/hall-core/app.py")
assert SPEC and SPEC.loader
app = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = app
SPEC.loader.exec_module(app)


class HallCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = app.Store(str(Path(self.temp.name) / "hall.db"))
        self.secret = "test-secret"
        self.token = "test-token"
        self.payload = {
            "action": "opened", "number": 7,
            "repository": {"full_name": "sovereign-codex/Codex-control-center", "html_url": "https://github.com/sovereign-codex/Codex-control-center"},
            "pull_request": {"number": 7, "updated_at": "2026-08-28T18:00:00Z", "html_url": "https://github.com/sovereign-codex/Codex-control-center/pull/7", "head": {"sha": "a" * 40}},
            "sender": {"login": "sovereign-codex", "type": "User"},
        }
        self.raw = app.canonical(self.payload).encode()

    def envelope(self, delivery: str = "delivery-1", raw: bytes | None = None, payload=None):
        return app.normalize(delivery, "pull_request", payload or self.payload, raw or self.raw,
                             "github-webhook-v0", "hall-core-0", "2026-08-28T18:01:00Z")

    def test_signature_and_authority_boundary(self) -> None:
        digest = hmac.new(self.secret.encode(), self.raw, hashlib.sha256).hexdigest()
        app.verify(self.secret, self.raw, "sha256=" + digest)
        with self.assertRaises(app.BadSignature):
            app.verify(self.secret, self.raw, "sha256=" + "0" * 64)
        event = self.envelope()["hall_event"]
        self.assertEqual(event["authority"]["posture"], "observe")
        self.assertEqual(event["authority"]["authorized_actions"], [])
        self.assertEqual(event["state"]["execution_state"], "not_started")

    def test_idempotency_mismatch_and_append_only(self) -> None:
        first = self.store.ingest("github-webhook-v0", "delivery-1", self.envelope(), self.raw)
        second = self.store.ingest("github-webhook-v0", "delivery-1", self.envelope(), self.raw)
        self.assertEqual(first["status"], "accepted")
        self.assertEqual(second["status"], "duplicate")
        changed = dict(self.payload, action="closed")
        raw = app.canonical(changed).encode()
        with self.assertRaises(app.ReplayMismatch):
            self.store.ingest("github-webhook-v0", "delivery-1", self.envelope(raw=raw, payload=changed), raw)
        self.assertEqual(self.store.snapshot()["event_count"], 1)
        db = sqlite3.connect(self.store.path)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM events")
        finally:
            db.close()

    def test_http_path(self) -> None:
        runtime = object.__new__(app.Runtime)
        runtime.node_id = "hall-core-test"
        runtime.commit = "test"
        runtime.secret = self.secret
        runtime.read_token = self.token
        runtime.adapter_id = "github-webhook-v0"
        runtime.max_body = 1048576
        runtime.store = self.store
        server = app.Server(("127.0.0.1", 0), runtime)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_port}"

        with urlopen(base + "/readyz", timeout=5) as response:
            self.assertEqual(response.status, 200)

        digest = hmac.new(self.secret.encode(), self.raw, hashlib.sha256).hexdigest()
        request = Request(base + "/v0/webhooks/github", data=self.raw, method="POST", headers={
            "Content-Type": "application/json", "X-Hub-Signature-256": "sha256=" + digest,
            "X-GitHub-Delivery": "delivery-http", "X-GitHub-Event": "pull_request",
        })
        with urlopen(request, timeout=5) as response:
            body = json.load(response)
            self.assertEqual(response.status, 202)
            self.assertEqual(body["institutional_effect"], "accepted_event_only")
        with urlopen(request, timeout=5) as response:
            self.assertEqual(json.load(response)["status"], "duplicate")

        with self.assertRaises(HTTPError) as denied:
            urlopen(base + "/v0/events", timeout=5)
        self.assertEqual(denied.exception.code, 401)
        read = Request(base + "/v0/events", headers={"Authorization": "Bearer " + self.token})
        with urlopen(read, timeout=5) as response:
            events = json.load(response)["events"]
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["envelope"]["hall_event"]["authority"]["posture"], "observe")


if __name__ == "__main__":
    unittest.main()
