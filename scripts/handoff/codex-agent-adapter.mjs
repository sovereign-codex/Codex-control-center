import { createHash } from 'node:crypto';
import { validTimestamp } from './normalization.mjs';

const bounded = value => typeof value === 'string' && value.length > 0 && value.length <= 20_000 && value.trim() === value && !/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(value);
const hash = value => createHash('sha256').update(String(value), 'utf8').digest('hex');

export const CODEX_AGENT_ADAPTER_VERSION = 'ccc-codex-agent/1';

export function buildCodexSessionRequest({ request_id, correlation_sha256, input, model = 'gpt-5.6-codex', container_size = 'small' }) {
  const issues = [];
  if (typeof request_id !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(request_id)) issues.push({ code: 'invalid_request_id', message: 'A bounded caller-assigned request_id is required.' });
  if (typeof correlation_sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(correlation_sha256)) issues.push({ code: 'invalid_correlation', message: 'A validated institutional correlation digest is required.' });
  if (!bounded(input)) issues.push({ code: 'invalid_input', message: 'Codex task input must be bounded text.' });
  if (!['small', 'medium', 'large'].includes(container_size)) issues.push({ code: 'invalid_container_size', message: 'container_size must be small, medium, or large.' });
  if (!bounded(model) || model.length > 128) issues.push({ code: 'invalid_model', message: 'A bounded model identifier is required.' });
  if (issues.length) return { valid: false, issues, request: null };

  const idempotency_key = `tyme:${request_id}:${correlation_sha256.slice(0, 16)}:session-v1`;
  const body = {
    agent: { model },
    environment: { type: 'openai_hosted', container_size },
    input,
    stream: false
  };

  return {
    valid: true,
    issues: [],
    request: {
      adapter_version: CODEX_AGENT_ADAPTER_VERSION,
      method: 'POST',
      url: 'https://api.openai.com/v1/agents/sessions',
      headers: {
        'Content-Type': 'application/json',
        'OpenAI-Beta': 'agents=v1',
        'Idempotency-Key': idempotency_key
      },
      body,
      correlation: {
        request_id,
        correlation_sha256,
        idempotency_key,
        request_fingerprint: hash(JSON.stringify(body))
      }
    }
  };
}

export function classifyCodexSessionResponse({ status, body = null, network_error = null }) {
  if (network_error) return { transport: 'uncertain', accepted: false, retry_same_idempotency_key_only: true, runtime_started: false, runtime_completed: false, completion_verified: false };
  if (status >= 200 && status < 300) {
    const session_id = body && typeof body === 'object' && typeof body.id === 'string' ? body.id : null;
    const state = body && typeof body === 'object' && typeof body.status === 'string' ? body.status : null;
    return {
      transport: 'accepted',
      accepted: true,
      session_id,
      state,
      runtime_started: Boolean(session_id),
      runtime_completed: status !== 202 && Boolean(session_id) && ['completed', 'failed', 'cancelled'].includes(state),
      // Response classification does not authenticate a task or its source revision.
      completion_verified: false
    };
  }
  if ([400, 401, 403, 404, 409, 422].includes(status)) return { transport: 'rejected', accepted: false, status, runtime_started: false, runtime_completed: false, completion_verified: false };
  if (Number.isInteger(status) && status >= 500) return { transport: 'uncertain', accepted: false, status, retry_same_idempotency_key_only: true, runtime_started: false, runtime_completed: false, completion_verified: false };
  return { transport: 'rejected', accepted: false, status, runtime_started: false, runtime_completed: false, completion_verified: false };
}

/**
 * Pure check of a normalized observation against independently retained assignment
 * context. This is NOT a provider response schema or an authenticated observer.
 * Matching/fresh claims never become verified completion through this helper.
 */
export function checkCodexCompletionEvidence({ expected, evidence, now, max_age_ms } = {}) {
  const issues = [];
  const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
  const identifier = value => typeof value === 'string' && value.length > 0 && value.length <= 256 && value.trim() === value && !/[\u0000-\u001f\u007f]/.test(value);
  const identity = {
    request_id: value => typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value),
    correlation_sha256: value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value),
    session_id: identifier,
    task_id: identifier,
    repository: value => identifier(value) && /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(value),
    sha: value => typeof value === 'string' && /^[a-f0-9]{40}$/.test(value)
  };
  const keys = Object.keys(identity);
  const shape = (value, allowed) => object(value) && Object.keys(value).length === allowed.length && allowed.every(key => Object.hasOwn(value, key));
  if (!shape(expected, [...keys, 'started_at'])) issues.push('invalid_expected_context');
  if (!shape(evidence, [...keys, 'kind', 'status', 'completed_at', 'observed_at', 'evidence_ref'])) issues.push('invalid_completion_evidence');
  for (const [key, valid] of Object.entries(identity)) {
    if (!valid(expected?.[key])) issues.push(`invalid_expected_${key}`);
    if (!valid(evidence?.[key])) issues.push(`invalid_evidence_${key}`);
    if (valid(expected?.[key]) && valid(evidence?.[key]) && evidence[key] !== expected[key]) issues.push(`${key}_mismatch`);
  }
  if (evidence?.kind !== 'codex_task_completion' || evidence?.status !== 'completed') issues.push('not_task_completion');
  if (!identifier(evidence?.evidence_ref)) issues.push('missing_evidence_reference');
  const times = [expected?.started_at, evidence?.completed_at, evidence?.observed_at, now];
  if (!times.every(value => typeof value === 'string' && value.length <= 128 && validTimestamp(value)) ||
      !Number.isSafeInteger(max_age_ms) || max_age_ms <= 0) {
    issues.push('invalid_freshness_context');
  } else {
    const [started, completed, observed, checked] = times.map(value => Date.parse(value));
    if (completed < started) issues.push('completion_predates_assignment');
    if (observed < completed || checked < observed) issues.push('invalid_observation_order');
    if (checked - observed > max_age_ms || checked - completed > max_age_ms) issues.push('stale_completion_evidence');
  }
  return { valid: issues.length === 0, issues, completion_verified: false };
}

export function classifyCodexLifecycleEvent(event) {
  if (!event || typeof event !== 'object' || typeof event.type !== 'string') return { valid: false, state: 'unknown' };
  if (event.type === 'agent.session.started') return { valid: true, state: 'started' };
  if (event.type === 'agent.turn.completed') return { valid: true, state: 'completed' };
  if (event.type === 'agent.turn.failed') return { valid: true, state: 'failed' };
  if (event.type === 'agent.session.interrupted') return { valid: true, state: 'interrupted' };
  return { valid: true, state: 'other' };
}
