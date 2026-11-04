import test from 'node:test';
import assert from 'node:assert/strict';
import { correlationFor, runtimeCorrelation, validateDestination } from '../../scripts/handoff/destination.mjs';

const destination = {
  class: 'codex_agent',
  endpoint_id: 'codex-managed-harness',
  declared_role: 'repository-inspector',
  operation: 'inspect',
  asynchronous: true
};

test('accepts explicit codex destination', () => {
  const result = validateDestination(destination);
  assert.equal(result.valid, true);
  assert.deepEqual(result.issues, []);
});

test('fails closed on unknown destination class', () => {
  const result = validateDestination({ ...destination, class: 'mystery_runtime' });
  assert.equal(result.valid, false);
  assert.equal(result.issues.some(x => x.code === 'unsupported_destination_class'), true);
});

test('fails closed on unexpected control fields', () => {
  const result = validateDestination({ ...destination, authority_transfer: true });
  assert.equal(result.valid, false);
  assert.equal(result.issues.some(x => x.code === 'unknown_destination_field'), true);
});

test('builds stable correlation with exact repository state', () => {
  const input = {
    request_id: 'office-codex-roundtrip-001',
    trace_id: 'trace-office-codex-001',
    office_assignment_id: 'repo-cartographer-001',
    destination,
    repository: 'sovereign-codex/Codex-control-center',
    sha: 'd8230a2f6fbc8c633c470f8446078f5f8d41abfb'
  };
  const a = correlationFor(input);
  const b = correlationFor(input);
  assert.equal(a.valid, true);
  assert.equal(a.correlation.correlation_sha256, b.correlation.correlation_sha256);
  assert.equal(a.correlation.repository_context.sha, input.sha);
});

test('repository context requires exact SHA', () => {
  const result = correlationFor({
    request_id: 'r1',
    trace_id: 't1',
    office_assignment_id: 'a1',
    destination,
    repository: 'sovereign-codex/Codex-control-center',
    sha: 'main'
  });
  assert.equal(result.valid, false);
  assert.equal(result.issues.some(x => x.code === 'invalid_sha'), true);
});

test('runtime-specific identifiers remain subordinate to institutional correlation', () => {
  const result = correlationFor({
    request_id: 'r2',
    trace_id: 't2',
    office_assignment_id: 'a2',
    destination
  });
  assert.equal(result.valid, true);
  const bound = runtimeCorrelation(result.correlation, {
    codex_session_id: 'session_123',
    codex_task_id: 'task_456',
    receipt_id: 'receipt_789'
  });
  assert.equal(bound.request_id, 'r2');
  assert.equal(bound.runtime.codex_session_id, 'session_123');
});

test('runtime correlation rejects unknown fields', () => {
  const result = correlationFor({
    request_id: 'r3',
    trace_id: 't3',
    office_assignment_id: 'a3',
    destination
  });
  assert.throws(() => runtimeCorrelation(result.correlation, { hidden_authority: 'yes' }));
});
