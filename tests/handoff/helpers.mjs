import assert from 'node:assert/strict';
import { prepareHandoff, CONTROL_CENTER, recordBytes, gitBlobSha } from '../../scripts/handoff/contract.mjs';

export const clone = value => structuredClone(value);

export function fixturePolicy() {
  return {
    schema_version: 'ccc-handoff-policy/1',
    enabled: true,
    ledger_branch: 'main',
    producer_bindings: [{ sender_id: '123', source_repo: 'org/producer', source_workflow: 'dispatch-workflow' }],
    dispatcher_sender_ids: ['456'],
    receiver: {
      repository: 'sovereign-codex/AVOT-engine',
      event_type: 'avot_execution',
      compatible: true,
      verified_commit: 'a'.repeat(40),
      evidence_ref: 'fixture-only:receiver-review'
    }
  };
}

export function producerEvent(overrides = {}) {
  return {
    trace_id: 'trace-fixture-001',
    repo: 'org/producer',
    workflow: 'dispatch-workflow',
    status: 'received',
    timestamp: '2026-10-17T22:30:00-07:00',
    payload: { content: 'preserved producer content', count: 3 },
    governance: { posture: 'review', authorized: false },
    runtime_packet: { packet_id: 'fixture-packet-001', execution_state: 'received' },
    ...overrides
  };
}

export function producerPayload(overrides = {}) {
  return {
    request_id: 'caller-request-001',
    target: 'avot-engine-runner',
    event: producerEvent(),
    note: { preserved_wrapper_extension: true },
    ...overrides
  };
}

export function observation(overrides = {}) {
  return {
    eventName: 'repository_dispatch',
    repository: CONTROL_CENTER,
    runId: '7001',
    runAttempt: '1',
    observedAt: '2026-10-18T05:31:00.000Z',
    ...overrides
  };
}

export function actionsEvent(payload, { stage = 'router', senderId = stage === 'router' ? 123 : 456, overrides = {} } = {}) {
  return {
    action: stage === 'router' ? 'route-event' : 'engine_handoff',
    repository: { full_name: CONTROL_CENTER },
    sender: { id: senderId },
    client_payload: payload,
    ...overrides
  };
}

export function prepareRouter({ payload = producerPayload(), policy = fixturePolicy(), obs = observation(), event, bytes } = {}) {
  return prepareHandoff({
    stage: 'router',
    eventBytes: bytes ?? Buffer.from(JSON.stringify(event ?? actionsEvent(payload))),
    observation: obs,
    policy
  });
}

export function prepareDispatcher(routerPrepared, { payload, policy = fixturePolicy(), obs = observation({ runId: '8001' }), event } = {}) {
  const incoming = payload ?? clone(routerPrepared.request.body.client_payload);
  return prepareHandoff({
    stage: 'dispatcher',
    eventBytes: Buffer.from(JSON.stringify(event ?? actionsEvent(incoming, { stage: 'dispatcher' }))),
    observation: obs,
    policy
  });
}

export function assertReady(prepared) {
  assert.equal(prepared.disposition, 'ready', JSON.stringify(prepared.issues));
  assert.ok(prepared.identity?.key && /^[0-9a-f]{64}$/.test(prepared.identity.key));
  assert.ok(prepared.binding?.fingerprint);
  assert.equal(prepared.execution.status, 'unverified');
  assert.equal(prepared.execution.completion_claim, false);
  return prepared;
}

export function assertNoCompletion(result) {
  assert.equal(result.execution.status, 'unverified');
  assert.equal(result.execution.completion_claim, false);
}

// Shared persistent state models independently executing workflow instances.
// The barrier starts competing claim requests together; Map insertion is the
// single atomic create point, and a record is never overwritten by the fake.
export class MemoryService {
  constructor({ raceClaims = 0, claimReply, outcomeReply, dispatchReply = { status: 204 } } = {}) {
    this.records = new Map();
    this.calls = [];
    this.claimReply = claimReply;
    this.outcomeReply = outcomeReply;
    this.dispatchReply = dispatchReply;
    this.raceClaims = raceClaims;
    this.waitingClaims = 0;
    if (raceClaims) this.claimGate = new Promise(resolve => { this.openClaimGate = resolve; });
  }

  get dispatches() { return this.calls.filter(call => call.kind === 'dispatch'); }

  async createRecord(path, record) {
    this.calls.push({ kind: 'createRecord', path, record: clone(record) });
    const isClaim = path.endsWith('/claim.json');
    if (isClaim && this.raceClaims && this.waitingClaims < this.raceClaims) {
      this.waitingClaims += 1;
      if (this.waitingClaims === this.raceClaims) this.openClaimGate();
      await this.claimGate;
    }
    const override = isClaim ? this.claimReply : this.outcomeReply;
    if (override instanceof Error) throw override;
    if (override && override.status !== 201) return clone(override);
    if (this.records.has(path)) return { status: 409, blobSha: null };
    const stored = { record: clone(record), blobSha: gitBlobSha(recordBytes(record)) };
    this.records.set(path, stored);
    return override ? clone(override) : { status: 201, blobSha: stored.blobSha };
  }

  async readRecord(path) {
    this.calls.push({ kind: 'readRecord', path });
    const stored = this.records.get(path);
    return stored ? { status: 200, ...clone(stored) } : { status: 404, record: null, blobSha: null };
  }

  async dispatch(request) {
    this.calls.push({ kind: 'dispatch', request: clone(request) });
    if (this.dispatchReply instanceof Error) throw this.dispatchReply;
    return clone(this.dispatchReply);
  }
}
