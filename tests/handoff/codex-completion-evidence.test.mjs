import test from 'node:test';
import assert from 'node:assert/strict';
import * as adapter from '../../scripts/handoff/codex-agent-adapter.mjs';

// All data is synthetic. No provider calls, credentials, clocks, or persistence.
const expected = Object.freeze({
  request_id: 'office-codex-001',
  correlation_sha256: 'a'.repeat(64),
  session_id: 'sess_current',
  task_id: 'task_current',
  repository: 'sovereign-codex/Codex-control-center',
  sha: '7492b95f3a8268488ea6df1ed2cebae048cf2447',
  started_at: '2026-11-13T09:00:00Z'
});
const { started_at, ...identity } = expected;
const evidence = Object.freeze({
  ...identity,
  kind: 'codex_task_completion',
  status: 'completed',
  completed_at: '2026-11-13T09:01:00Z',
  observed_at: '2026-11-13T09:01:10Z',
  evidence_ref: 'fixture://codex/observation-current'
});
const policy = Object.freeze({ now: '2026-11-13T09:01:20Z', max_age_ms: 60_000 });
const check = overrides => adapter.checkCodexCompletionEvidence({ expected, evidence, ...policy, ...overrides });
const rejected = result => {
  assert.equal(result.valid, false);
  assert.ok(result.issues.length > 0);
  assert.equal(result.completion_verified, false);
};

test('matching fresh task evidence passes only the data check, without authenticating completion', () => {
  assert.deepEqual(check(), { valid: true, issues: [], completion_verified: false });
});

test('absent expected context cannot be reconstructed from the observation', () => {
  rejected(check({ expected: undefined }));
});

test('missing completion evidence fails closed', () => {
  rejected(check({ evidence: undefined }));
});

for (const [field, wrong] of Object.entries({
  session_id: 'sess_other',
  task_id: 'task_prior_in_same_session',
  request_id: 'office-codex-prior',
  correlation_sha256: 'b'.repeat(64),
  repository: 'sovereign-codex/Tyme-Lab',
  sha: 'd1516ac92bb26875036b5d32db3c5e6dd79da314'
})) {
  test(`rejects mismatched ${field}`, () => {
    const result = check({ evidence: { ...evidence, [field]: wrong } });
    rejected(result);
    assert.ok(result.issues.includes(`${field}_mismatch`));
  });
}

for (const side of ['expected', 'evidence']) {
  for (const field of ['session_id', 'task_id', 'request_id', 'correlation_sha256', 'repository', 'sha']) {
    test(`rejects missing ${side}.${field}`, () => {
      const incomplete = { ...(side === 'expected' ? expected : evidence) };
      delete incomplete[field];
      rejected(check({ [side]: incomplete }));
    });
  }
}

for (const [field, malformed] of Object.entries({
  session_id: '',
  task_id: 'task\nforged',
  request_id: 'unbounded request identity',
  correlation_sha256: 'not-a-digest',
  repository: 'main',
  sha: 'main'
})) {
  test(`rejects malformed identity even when both sides agree: ${field}`, () => {
    rejected(check({
      expected: { ...expected, [field]: malformed },
      evidence: { ...evidence, [field]: malformed }
    }));
  });
}

test('rejects stale completion from before the current assignment', () => {
  const result = check({ evidence: { ...evidence, completed_at: '2026-11-13T08:59:59Z' } });
  rejected(result);
  assert.ok(result.issues.includes('completion_predates_assignment'));
});

test('fresh retrieval cannot refresh an old completion timestamp', () => {
  const result = check({ evidence: { ...evidence, completed_at: '2026-11-13T09:00:01Z' } });
  rejected(result);
  assert.ok(result.issues.includes('stale_completion_evidence'));
});

test('rejects a matching completion whose observation has expired', () => {
  const result = check({ now: '2026-11-13T09:03:00Z' });
  rejected(result);
  assert.ok(result.issues.includes('stale_completion_evidence'));
});

test('rejects future observation time', () => {
  rejected(check({ now: '2026-11-13T09:01:05Z' }));
});

test('rejects observation that predates completion', () => {
  rejected(check({ evidence: { ...evidence, observed_at: '2026-11-13T09:00:59Z' } }));
});

for (const [label, overrides] of [
  ['missing expected start time', { expected: { ...expected, started_at: undefined } }],
  ['missing completion time', { evidence: { ...evidence, completed_at: undefined } }],
  ['missing observation time', { evidence: { ...evidence, observed_at: undefined } }],
  ['missing check time', { now: undefined }],
  ['invalid calendar time', { evidence: { ...evidence, completed_at: '2026-02-30T09:01:00Z' } }],
  ['missing maximum age', { max_age_ms: undefined }],
  ['zero maximum age', { max_age_ms: 0 }],
  ['negative maximum age', { max_age_ms: -1 }]
]) {
  test(`rejects freshness policy: ${label}`, () => rejected(check(overrides)));
}

test('accepts the explicit freshness boundary, without authenticating completion', () => {
  assert.equal(check({ now: '2026-11-13T09:02:00Z' }).valid, true);
});

test('rejects one millisecond beyond completion freshness boundary', () => {
  rejected(check({ now: '2026-11-13T09:02:00.001Z' }));
});

for (const status of ['accepted', 'in_progress', 'failed', 'cancelled']) {
  test(`does not treat ${status} as successful task completion`, () => {
    rejected(check({ evidence: { ...evidence, status } }));
  });
}

test('transport-acceptance evidence cannot masquerade as task-completion evidence', () => {
  rejected(check({ evidence: { ...evidence, kind: 'transport_acceptance' } }));
});

test('generic lifecycle event cannot masquerade as a bound completion observation', () => {
  rejected(check({ evidence: { type: 'agent.turn.completed' } }));
});

test('missing evidence reference fails closed', () => {
  rejected(check({ evidence: { ...evidence, evidence_ref: '' } }));
});

test('unexpected authority flag in evidence is rejected rather than trusted', () => {
  rejected(check({ evidence: { ...evidence, completion_verified: true } }));
});

for (const status of [200, 201, 202, 204]) {
  test(`HTTP ${status} with a completed string never verifies completion`, () => {
    const result = adapter.classifyCodexSessionResponse({
      status, body: { id: expected.session_id, status: 'completed' }
    });
    assert.equal(result.accepted, true);
    assert.equal(result.completion_verified, false);
    if (status === 202) assert.equal(result.runtime_completed, false);
  });
}

test('completed string with no session identifier cannot establish runtime completion', () => {
  const result = adapter.classifyCodexSessionResponse({ status: 200, body: { status: 'completed' } });
  assert.equal(result.runtime_completed, false);
  assert.equal(result.completion_verified, false);
});

for (const response of [
  { status: null, network_error: 'synthetic timeout' },
  { status: 401 }, { status: 403 }, { status: 404 }, { status: 409 }, { status: 500 }
]) {
  test(`nonaccepted/uncertain response ${response.status} explicitly remains unverified`, () => {
    assert.equal(adapter.classifyCodexSessionResponse(response).completion_verified, false);
  });
}

test('checking evidence does not mutate retained assignment or observation', () => {
  const before = JSON.stringify({ expected, evidence });
  check();
  assert.equal(JSON.stringify({ expected, evidence }), before);
});

