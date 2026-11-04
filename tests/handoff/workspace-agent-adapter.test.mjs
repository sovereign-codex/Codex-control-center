import test from 'node:test';
import assert from 'node:assert/strict';
import { buildWorkspaceAgentTrigger, classifyWorkspaceAgentResponse } from '../../scripts/handoff/workspace-agent-adapter.mjs';

const base = {
  trigger_id: 'agtch_demo123',
  request_id: 'office-codex-001',
  correlation_sha256: 'a'.repeat(64),
  input: 'Inspect the repository read-only and return evidence.'
};

test('builds stable workspace agent request without authorization material', () => {
  const a = buildWorkspaceAgentTrigger(base);
  const b = buildWorkspaceAgentTrigger(base);
  assert.equal(a.valid, true);
  assert.equal(a.request.headers['Idempotency-Key'], b.request.headers['Idempotency-Key']);
  assert.equal(a.request.body.conversation_key, 'tyme:office-codex-001');
  assert.equal('Authorization' in a.request.headers, false);
});

test('rejects malformed trigger id', () => {
  const result = buildWorkspaceAgentTrigger({ ...base, trigger_id: 'agent-1' });
  assert.equal(result.valid, false);
});

test('202 means accepted but not completed', () => {
  const result = classifyWorkspaceAgentResponse({ status: 202, body: { conversation_url: 'https://chatgpt.com/c/example' } });
  assert.equal(result.accepted, true);
  assert.equal(result.completion_verified, false);
});

test('network ambiguity permits only same-idempotency retry posture', () => {
  const result = classifyWorkspaceAgentResponse({ status: null, network_error: 'timeout' });
  assert.equal(result.transport, 'uncertain');
  assert.equal(result.retry_same_idempotency_key_only, true);
});

test('409 is rejected, not completion', () => {
  const result = classifyWorkspaceAgentResponse({ status: 409 });
  assert.equal(result.transport, 'rejected');
  assert.equal(result.completion_verified, false);
});
