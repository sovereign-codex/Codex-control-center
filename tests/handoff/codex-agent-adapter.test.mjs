import test from 'node:test';
import assert from 'node:assert/strict';
import { buildCodexSessionRequest, classifyCodexLifecycleEvent, classifyCodexSessionResponse } from '../../scripts/handoff/codex-agent-adapter.mjs';

const base = {
  request_id: 'office-codex-001',
  correlation_sha256: 'b'.repeat(64),
  input: 'Read-only inspection. Do not mutate repositories.'
};

test('builds managed Codex session request without API key material', () => {
  const result = buildCodexSessionRequest(base);
  assert.equal(result.valid, true);
  assert.equal(result.request.url, 'https://api.openai.com/v1/agents/sessions');
  assert.equal(result.request.headers['OpenAI-Beta'], 'agents=v1');
  assert.equal('Authorization' in result.request.headers, false);
  assert.equal(result.request.body.environment.type, 'openai_hosted');
});

test('idempotency key is stable for identical institutional correlation', () => {
  const a = buildCodexSessionRequest(base);
  const b = buildCodexSessionRequest(base);
  assert.equal(a.request.headers['Idempotency-Key'], b.request.headers['Idempotency-Key']);
});

test('accepted session is not necessarily completed', () => {
  const result = classifyCodexSessionResponse({ status: 200, body: { id: 'sess_123', status: 'in_progress' } });
  assert.equal(result.accepted, true);
  assert.equal(result.runtime_started, true);
  assert.equal(result.runtime_completed, false);
});

test('reported completed session is classified without verifying task completion', () => {
  const result = classifyCodexSessionResponse({ status: 200, body: { id: 'sess_123', status: 'completed' } });
  assert.equal(result.state, 'completed');
  assert.equal(result.runtime_completed, true);
  assert.equal(result.completion_verified, false);
});

test('network ambiguity requires same idempotency key posture', () => {
  const result = classifyCodexSessionResponse({ status: null, network_error: 'timeout' });
  assert.equal(result.transport, 'uncertain');
  assert.equal(result.retry_same_idempotency_key_only, true);
});

test('lifecycle events distinguish completion from failure', () => {
  assert.equal(classifyCodexLifecycleEvent({ type: 'agent.turn.completed' }).state, 'completed');
  assert.equal(classifyCodexLifecycleEvent({ type: 'agent.turn.failed' }).state, 'failed');
});
