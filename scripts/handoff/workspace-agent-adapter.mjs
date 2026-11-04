import { createHash } from 'node:crypto';

const bounded = value => typeof value === 'string' && value.length > 0 && value.length <= 512 && value.trim() === value && !/[\u0000-\u001f\u007f]/.test(value);
const triggerId = value => typeof value === 'string' && /^agtch_[A-Za-z0-9_-]+$/.test(value);
const requestId = value => typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value);
const hash = value => createHash('sha256').update(String(value), 'utf8').digest('hex');

export const WORKSPACE_AGENT_ADAPTER_VERSION = 'ccc-workspace-agent/1';

export function buildWorkspaceAgentTrigger({ trigger_id, request_id, correlation_sha256, input }) {
  const issues = [];
  if (!triggerId(trigger_id)) issues.push({ code: 'invalid_trigger_id', message: 'Workspace Agent trigger_id must use the agtch_ form.' });
  if (!requestId(request_id)) issues.push({ code: 'invalid_request_id', message: 'A bounded caller-assigned request_id is required.' });
  if (typeof correlation_sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(correlation_sha256)) issues.push({ code: 'invalid_correlation', message: 'A validated institutional correlation digest is required.' });
  if (!bounded(input) || input.length > 20_000) issues.push({ code: 'invalid_input', message: 'Workspace Agent input must be bounded text.' });
  if (issues.length) return { valid: false, issues, request: null };

  const conversation_key = `tyme:${request_id}`;
  const idempotency_key = `tyme:${request_id}:${correlation_sha256.slice(0, 16)}:v1`;

  return {
    valid: true,
    issues: [],
    request: {
      adapter_version: WORKSPACE_AGENT_ADAPTER_VERSION,
      method: 'POST',
      url: `https://api.chatgpt.com/v1/workspace_agents/${trigger_id}/trigger`,
      headers: {
        'Content-Type': 'application/json',
        'Idempotency-Key': idempotency_key
      },
      body: {
        conversation_key,
        input
      },
      correlation: {
        request_id,
        correlation_sha256,
        conversation_key,
        idempotency_key,
        request_fingerprint: hash(JSON.stringify({ trigger_id, conversation_key, idempotency_key, input }))
      }
    }
  };
}

export function classifyWorkspaceAgentResponse({ status, body = null, network_error = null }) {
  if (network_error) return { transport: 'uncertain', accepted: false, retry_same_idempotency_key_only: true, completion_verified: false };
  if (status === 202) {
    const conversation_url = body && typeof body === 'object' && typeof body.conversation_url === 'string' ? body.conversation_url : null;
    const run_id = body && typeof body === 'object' && typeof body.run_id === 'string' ? body.run_id : null;
    return { transport: 'accepted', accepted: true, conversation_url, run_id, completion_verified: false };
  }
  if ([401, 403, 404, 409].includes(status)) return { transport: 'rejected', accepted: false, status, completion_verified: false };
  if (Number.isInteger(status) && status >= 500) return { transport: 'uncertain', accepted: false, status, retry_same_idempotency_key_only: true, completion_verified: false };
  return { transport: 'rejected', accepted: false, status, completion_verified: false };
}
