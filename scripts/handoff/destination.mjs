import { createHash } from 'node:crypto';

const classes = new Set(['github_dispatch', 'workspace_agent', 'codex_agent']);
const bounded = value => typeof value === 'string' && value.length > 0 && value.length <= 256 && value.trim() === value && !/[\u0000-\u001f\u007f]/.test(value);
const requestId = value => typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value);
const obj = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const canonical = value => {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (obj(value)) return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
  return JSON.stringify(value);
};
const digest = value => createHash('sha256').update(canonical(value), 'utf8').digest('hex');

export const DESTINATION_CONTRACT_VERSION = 'ccc-destination/1';

export function validateDestination(value) {
  const issues = [];
  if (!obj(value)) return { valid: false, issues: [{ code: 'invalid_destination', message: 'Destination must be an object.' }] };

  const allowed = ['class', 'endpoint_id', 'declared_role', 'operation', 'asynchronous'];
  const extra = Object.keys(value).filter(k => !allowed.includes(k));
  if (extra.length) issues.push({ code: 'unknown_destination_field', message: `Unknown destination field(s): ${extra.join(', ')}` });

  if (!classes.has(value.class)) issues.push({ code: 'unsupported_destination_class', message: 'Destination class must be github_dispatch, workspace_agent, or codex_agent.' });
  if (!bounded(value.endpoint_id)) issues.push({ code: 'invalid_endpoint_id', message: 'A bounded endpoint_id is required.' });
  if (!bounded(value.declared_role)) issues.push({ code: 'invalid_declared_role', message: 'A bounded declared_role is required.' });
  if (!bounded(value.operation)) issues.push({ code: 'invalid_operation', message: 'A bounded operation is required.' });
  if (value.asynchronous !== true && value.asynchronous !== false) issues.push({ code: 'invalid_asynchronous', message: 'asynchronous must be explicit boolean.' });

  return { valid: issues.length === 0, issues };
}

export function correlationFor({ request_id, trace_id, office_assignment_id, destination, repository = null, sha = null }) {
  const issues = [];
  if (!requestId(request_id)) issues.push({ code: 'invalid_request_id', message: 'request_id must be caller-assigned and bounded.' });
  if (!bounded(trace_id)) issues.push({ code: 'invalid_trace_id', message: 'trace_id is required.' });
  if (!bounded(office_assignment_id)) issues.push({ code: 'invalid_office_assignment_id', message: 'office_assignment_id is required.' });

  const dest = validateDestination(destination);
  issues.push(...dest.issues);

  const repoDeclared = repository !== null || sha !== null;
  if (repoDeclared) {
    if (!bounded(repository) || !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repository)) issues.push({ code: 'invalid_repository', message: 'repository must be owner/name when supplied.' });
    if (typeof sha !== 'string' || !/^[a-f0-9]{40}$/.test(sha)) issues.push({ code: 'invalid_sha', message: 'sha must be an exact 40-character Git SHA when repository context is supplied.' });
  }

  if (issues.length) return { valid: false, issues, correlation: null };

  const correlation = {
    contract_version: DESTINATION_CONTRACT_VERSION,
    request_id,
    trace_id,
    office_assignment_id,
    destination: {
      class: destination.class,
      endpoint_id: destination.endpoint_id,
      declared_role: destination.declared_role,
      operation: destination.operation,
      asynchronous: destination.asynchronous
    },
    repository_context: repoDeclared ? { repository, sha } : null
  };

  return {
    valid: true,
    issues: [],
    correlation: {
      ...correlation,
      correlation_sha256: digest(correlation)
    }
  };
}

export function runtimeCorrelation(base, runtime = {}) {
  if (!obj(base) || !bounded(base.correlation_sha256)) throw new TypeError('A validated base correlation is required.');
  const allowed = ['workspace_conversation_key', 'workspace_run_id', 'codex_session_id', 'codex_task_id', 'receipt_id'];
  const extra = Object.keys(runtime).filter(k => !allowed.includes(k));
  if (extra.length) throw new TypeError(`Unknown runtime correlation field(s): ${extra.join(', ')}`);
  for (const [key, value] of Object.entries(runtime)) {
    if (value !== null && !bounded(value)) throw new TypeError(`Invalid runtime correlation value for ${key}.`);
  }
  return Object.freeze({ ...base, runtime: { ...runtime } });
}
