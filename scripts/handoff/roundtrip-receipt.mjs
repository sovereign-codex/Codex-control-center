import { createHash } from 'node:crypto';

const obj = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const bounded = value => typeof value === 'string' && value.length > 0 && value.length <= 1024 && value.trim() === value && !/[\u0000-\u001f\u007f]/.test(value);
const hex40 = value => typeof value === 'string' && /^[a-f0-9]{40}$/.test(value);
const hex64 = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const canonical = value => {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (obj(value)) return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
  return JSON.stringify(value);
};
const sha256 = value => createHash('sha256').update(canonical(value), 'utf8').digest('hex');

export const ROUNDTRIP_RECEIPT_VERSION = 'office-codex-receipt/1';

export function receiptId({ request_id, trace_id, correlation_sha256 }) {
  if (!bounded(request_id) || !bounded(trace_id) || !hex64(correlation_sha256)) throw new TypeError('Invalid receipt identity inputs.');
  return 'ocr1-' + sha256(['office-codex-roundtrip-receipt-v1', request_id, trace_id, correlation_sha256]).slice(0, 32);
}

export function receiptPath(id) {
  if (typeof id !== 'string' || !/^ocr1-[a-f0-9]{32}$/.test(id)) throw new TypeError('Invalid receipt id.');
  return `roundtrip-ledger/v1/${id}/receipt.json`;
}

export function buildReceipt(input = {}) {
  const issues = [];
  const {
    request_id, trace_id, correlation_sha256, origin_office_role,
    executor, task, transport, result, review,
    institutional_effect = 'none',
    repository_receipt = null,
    notion_readback = null
  } = obj(input) ? input : {};

  if (!bounded(request_id)) issues.push({ code: 'invalid_request_id' });
  if (!bounded(trace_id)) issues.push({ code: 'invalid_trace_id' });
  if (!hex64(correlation_sha256)) issues.push({ code: 'invalid_correlation' });
  if (!bounded(origin_office_role)) issues.push({ code: 'invalid_origin_role' });

  if (!obj(executor) || !['workspace_agent','codex_agent'].includes(executor.runtime_class) || !bounded(executor.endpoint_id) || !bounded(executor.session_or_run_id)) {
    issues.push({ code: 'invalid_executor' });
  }

  if (!obj(task) || task.authority_ceiling !== 'READ_ONLY') issues.push({ code: 'invalid_authority_ceiling' });
  if (task?.repository !== null && task?.repository !== undefined) {
    if (!bounded(task.repository) || !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(task.repository)) issues.push({ code: 'invalid_repository' });
    if (!hex40(task.sha)) issues.push({ code: 'invalid_repository_sha' });
  }

  const transportFields = ['accepted','runtime_started','runtime_completed','result_returned','evidence_stored'];
  if (!obj(transport) || !transportFields.every(k => typeof transport[k] === 'boolean')) issues.push({ code: 'invalid_transport' });

  if (!obj(result) || !bounded(result.summary) || !Array.isArray(result.evidence_refs) || !Array.isArray(result.assumptions) || !Array.isArray(result.uncertainty)) {
    issues.push({ code: 'invalid_result' });
  }

  if (!obj(review) || !bounded(review.reviewing_office_role) || typeof review.completed !== 'boolean' || !['PASS','PARTIAL','FAIL','HOLD','UNREVIEWED'].includes(review.verdict)) {
    issues.push({ code: 'invalid_review' });
  }

  if (institutional_effect !== 'none') issues.push({ code: 'institutional_effect_forbidden' });

  if (repository_receipt !== null) {
    if (!obj(repository_receipt) || !bounded(repository_receipt.repository) || !hex40(repository_receipt.commit_sha) || !hex40(repository_receipt.blob_sha) || !hex64(repository_receipt.content_sha256)) {
      issues.push({ code: 'invalid_repository_receipt' });
    }
  }

  if (notion_readback !== null) {
    if (!obj(notion_readback) || !bounded(notion_readback.page_url) || !hex64(notion_readback.reconstructed_content_sha256) || notion_readback.independent_readback !== true) {
      issues.push({ code: 'invalid_notion_readback' });
    }
  }

  if (issues.length) return { valid: false, issues, receipt: null };

  const id = receiptId({ request_id, trace_id, correlation_sha256 });
  const core = {
    receipt_version: ROUNDTRIP_RECEIPT_VERSION,
    receipt_id: id,
    request_id,
    trace_id,
    correlation_sha256,
    origin_office_role,
    executor,
    task,
    transport,
    result,
    review,
    standing: {
      claimed_by_executor: 'none',
      institutional_effect: 'none',
      hall_receipt_claimed: false,
      canon_claimed: false
    },
    proof_ceiling: {
      persistence_is_not_authority: true,
      transport_acceptance_is_not_completion: true,
      runtime_completion_is_not_review: true,
      review_is_not_canon: true
    },
    repository_receipt,
    notion_readback
  };

  return {
    valid: true,
    issues: [],
    receipt: {
      ...core,
      content_sha256: sha256(core)
    }
  };
}

export function verifyReadback(receipt) {
  if (!obj(receipt) || receipt.receipt_version !== ROUNDTRIP_RECEIPT_VERSION || !hex64(receipt.content_sha256)) {
    return { valid: false, reason: 'invalid_receipt_shape' };
  }
  const { content_sha256, ...core } = receipt;
  const reconstructed = sha256(core);
  return {
    valid: reconstructed === content_sha256,
    reconstructed_content_sha256: reconstructed,
    expected_content_sha256: content_sha256
  };
}
