import { createHash } from 'node:crypto';

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
  if (network_error) return { transport: 'uncertain', accepted: false, retry_same_idempotency_key_only: true, runtime_started: false, runtime_completed: false };
  if (status >= 200 && status < 300) {
    const session_id = body && typeof body === 'object' && typeof body.id === 'string' ? body.id : null;
    const state = body && typeof body === 'object' && typeof body.status === 'string' ? body.status : null;
    return {
      transport: 'accepted',
      accepted: true,
      session_id,
      state,
      runtime_started: Boolean(session_id),
      runtime_completed: ['completed', 'failed', 'cancelled'].includes(state),
      completion_verified: state === 'completed'
    };
  }
  if ([400, 401, 403, 404, 409, 422].includes(status)) return { transport: 'rejected', accepted: false, status, runtime_started: false, runtime_completed: false };
  if (Number.isInteger(status) && status >= 500) return { transport: 'uncertain', accepted: false, status, retry_same_idempotency_key_only: true, runtime_started: false, runtime_completed: false };
  return { transport: 'rejected', accepted: false, status, runtime_started: false, runtime_completed: false };
}

export function classifyCodexLifecycleEvent(event) {
  if (!event || typeof event !== 'object' || typeof event.type !== 'string') return { valid: false, state: 'unknown' };
  if (event.type === 'agent.session.started') return { valid: true, state: 'started' };
  if (event.type === 'agent.turn.completed') return { valid: true, state: 'completed' };
  if (event.type === 'agent.turn.failed') return { valid: true, state: 'failed' };
  if (event.type === 'agent.session.interrupted') return { valid: true, state: 'interrupted' };
  return { valid: true, state: 'other' };
}
