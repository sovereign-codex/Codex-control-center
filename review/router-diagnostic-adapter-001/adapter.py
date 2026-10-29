"""Review-only portable core. No server, registration, scheduler or CLI dispatch.

Only a trusted OAuth resource-server wrapper may call Adapter.invoke. Dependencies
and approval are operator-owned, never MCP arguments. SQLite must be on durable
local storage, shared by all instances; never deploy replicas with separate DBs.
"""
import hashlib
import http.client
import json
import re
import sqlite3
import time
from dataclasses import dataclass

CCC = 'sovereign-codex/Codex-control-center'
AVOT = 'sovereign-codex/AVOT-engine'
DESTINATION = '/repos/' + CCC + '/dispatches'
PINS = {
    CCC: ('config/control-center-handoff.json', 'febfe44f69ca1c0c02c5394d5edfafb163a939a5'),
    AVOT: ('config/avot-receiver.json', '0b909340619f4ad4519c1aace97fdc72366de2b5'),
}
ID = r'ccc-thread-diag-v1-[a-z0-9]{8,32}'
SHA = r'[0-9a-f]{40}'


class Stop(Exception):
    """Fixed safe error codes only; never carry remote messages or input values."""


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def strict(raw, limit=8192):
    if not isinstance(raw, bytes) or len(raw) > limit:
        raise Stop('invalid_size')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Stop('duplicate_json_key')
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(Stop('invalid_json')))
    except (ValueError, UnicodeError, RecursionError):
        raise Stop('invalid_json') from None


def request(raw):
    data = strict(raw)
    if type(data) is not dict or set(data) != {'diagnostic_id', 'expected_source_revision'}:
        raise Stop('invalid_fields')
    for key, pattern in [('diagnostic_id', ID), ('expected_source_revision', SHA)]:
        if type(data[key]) is not str or not re.fullmatch(pattern, data[key]):
            raise Stop('invalid_field_value')
    return data


def template(data):
    # Versioned synthetic data only. Timestamp is deliberately fixed, not a run claim.
    return canonical({'event_type': 'route-event', 'client_payload': {
        'request_id': data['diagnostic_id'], 'trace_id': data['diagnostic_id'], 'target': 'avot-engine-runner',
        'repo': CCC, 'workflow': 'invoke_router_diagnostic_v1',
        'status': 'started', 'timestamp': '2026-10-29T00:00:00Z',
        'payload': {'template_version': 'router-disabled-diagnostic/1',
                    'synthetic': True, 'operation': 'observe_disabled_policy'},
        'governance': {'authority_effect': 'none', 'mutation_allowed': False,
                       'canon_posture': 'noncanonical'}}})


@dataclass(frozen=True)
class Principal:
    # Construct ONLY after resource-server signature/issuer/audience/expiry checks.
    subject: str
    scopes: frozenset


@dataclass(frozen=True)
class Approval:
    # Trusted deployment configuration, NEVER a tool field or self-attestation.
    diagnostic_id: str
    source_revision: str
    receiver_revision: str
    subject: str
    sender_id: int
    request_sha256: str
    authorization_ref: str
    review_ref: str
    freeze_ref: str
    expires_at: int


class Github:
    """Fixed GitHub-only HTTPS. No redirects, retries, response body logging.

    Credential providers return short-lived tokens from a reviewed secret broker.
    Use independent read-only and dispatch credentials. Never pass these via MCP.
    http.client has no implicit retry or redirect support.
    """
    def __init__(self, read_token, dispatch_token):
        self._read_token, self._dispatch_token = read_token, dispatch_token

    def _call(self, method, path, body=None):
        token = (self._dispatch_token if method == 'POST' else self._read_token)()
        if not token or '\n' in token or '\r' in token:
            raise Stop('credentials_unavailable')
        conn = http.client.HTTPSConnection('api.github.com', timeout=15)
        try:
            conn.request(method, path, body=body, headers={
                'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                'Content-Type': 'application/json', 'User-Agent': 'tyme-router-diagnostic-v1',
                'X-GitHub-Api-Version': '2022-11-28'})
            response = conn.getresponse()
            if method == 'POST':
                return response.status  # Do not read/retain response text or headers.
            if response.status != 200:
                raise Stop('read_unavailable')
            return strict(response.read(1048577), 1048576)
        except Exception:
            raise Stop('transport_unavailable') from None
        finally:
            conn.close()

    def snapshot(self):
        import base64
        result = {}
        for repo, (path, pin) in PINS.items():
            branch = self._call('GET', '/repos/' + repo + '/branches/main')
            sha = branch['commit']['sha']
            if not re.fullmatch(SHA, sha):
                raise Stop('invalid_revision')
            file = self._call('GET', '/repos/' + repo + '/contents/' + path + '?ref=' + sha)
            raw = base64.b64decode(file['content'], validate=False)
            blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            policy = strict(raw)
            if blob != pin or file['sha'] != pin or policy.get('enabled') is not False:
                raise Stop('policy_changed')
            result[repo] = {'revision': sha, 'policy_blob': blob}
        return result

    def post_once(self, body):
        # Defense in depth: no public arbitrary path/method/payload transport.
        data = strict(body)
        rid = data.get('client_payload', {}).get('request_id')
        if type(rid) is not str or not re.fullmatch(ID, rid):
            raise Stop('invalid_template')
        if body != template({'diagnostic_id': rid}):
            raise Stop('invalid_template')
        return self._call('POST', DESTINATION, body)


def check_snapshot(snapshot, approval):
    expected = {CCC: approval.source_revision, AVOT: approval.receiver_revision}
    if type(snapshot) is not dict or set(snapshot) != set(PINS):
        raise Stop('snapshot_unavailable')
    for repo, revision in expected.items():
        if snapshot[repo] != {'revision': revision, 'policy_blob': PINS[repo][1]}:
            raise Stop('snapshot_changed')


class Adapter:
    def __init__(self, db_path, github, approval=None):
        self.github, self.approval = github, approval
        self.db = sqlite3.connect(db_path, timeout=5)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS attempt ('
                        'slot INTEGER PRIMARY KEY CHECK(slot=1), id TEXT UNIQUE, '
                        'input BLOB, body BLOB, digest TEXT, provenance BLOB, '
                        'attempt_time INTEGER, status TEXT, http_status INTEGER)')
        self.db.commit()

    def invoke(self, raw, principal):
        data = request(raw)
        body = template(data)
        a = self.approval
        if (type(principal) is not Principal or not principal.subject or
                'router.diagnostic.invoke' not in principal.scopes):
            raise Stop('unauthorized')
        if (a is None or principal.subject != a.subject or
                data['diagnostic_id'] != a.diagnostic_id or
                data['expected_source_revision'] != a.source_revision or
                digest(body) != a.request_sha256 or time.time() >= a.expires_at or
                a.expires_at > time.time() + 3600 or
                not all((a.authorization_ref, a.review_ref, a.freeze_ref)) or
                not re.fullmatch(SHA, a.receiver_revision) or type(a.sender_id) is not int or a.sender_id <= 0):
            raise Stop('authorization_unavailable')
        try:
            check_snapshot(self.github.snapshot(), a)
        except Exception:
            raise Stop('preflight_unavailable_or_changed') from None
        # One slot for the entire experiment, not just one ID. A new ID cannot
        # bypass an accepted, uncertain, rejected or crashed attempt. No reset API.
        provenance = canonical({'subject_sha256': digest(a.subject.encode()),
                                'authorization_ref': a.authorization_ref,
                                'review_ref': a.review_ref, 'freeze_ref': a.freeze_ref,
                                'source_revision': a.source_revision,
                                'receiver_revision': a.receiver_revision})
        try:
            with self.db:
                self.db.execute('INSERT INTO attempt VALUES (1,?,?,?,?,?,?,?,NULL)',
                    (a.diagnostic_id, raw, body, digest(body), provenance,
                     int(time.time()), 'uncertain'))
        except sqlite3.IntegrityError:
            raise Stop('experiment_already_reserved') from None
        # Reservation is committed BEFORE external effect. Crash => uncertain.
        status, http_status = 'uncertain', None
        try:
            http_status = self.github.post_once(body)
            if type(http_status) is not int:
                http_status = None
            elif http_status == 204:
                status = 'accepted_204'
            elif 400 <= http_status < 500:
                status = 'rejected'
            # Redirects, 5xx and unexpected 2xx remain uncertain, never retry.
        except Exception:
            pass  # Do not expose exception strings, tokens, URLs or bodies.
        with self.db:
            self.db.execute('UPDATE attempt SET status=?, http_status=? WHERE slot=1',
                            (status, http_status))
        return {'dispatch_transport': status, 'http_status': http_status,
                'request_sha256': digest(body), 'router_arrival': 'not_observed',
                'router_policy': 'not_observed', 'custom_app_authentication': 'not_tested',
                'downstream_execution': 'not_tested', 'authority_effect': 'none'}
