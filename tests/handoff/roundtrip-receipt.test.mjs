import test from 'node:test';
import assert from 'node:assert/strict';
import { buildReceipt, receiptId, receiptPath, verifyReadback } from '../../scripts/handoff/roundtrip-receipt.mjs';

const base = {
  request_id: 'office-codex-001',
  trace_id: 'trace-office-codex-001',
  correlation_sha256: 'c'.repeat(64),
  origin_office_role: 'Repo Cartographer',
  executor: {
    runtime_class: 'codex_agent',
    endpoint_id: 'codex-managed-harness',
    session_or_run_id: 'sess_001'
  },
  task: {
    repository: 'sovereign-codex/Codex-control-center',
    sha: 'd8230a2f6fbc8c633c470f8446078f5f8d41abfb',
    authority_ceiling: 'READ_ONLY'
  },
  transport: {
    accepted: true,
    runtime_started: true,
    runtime_completed: true,
    result_returned: true,
    evidence_stored: true
  },
  result: {
    summary: 'Read-only inspection completed.',
    evidence_refs: ['trace://example'],
    assumptions: [],
    uncertainty: []
  },
  review: {
    reviewing_office_role: 'Promotion Reviewer',
    completed: true,
    verdict: 'PASS'
  }
};

test('receipt identity is deterministic', () => {
  const a = receiptId(base);
  const b = receiptId(base);
  assert.equal(a, b);
  assert.match(receiptPath(a), /^roundtrip-ledger\/v1\/ocr1-[a-f0-9]{32}\/receipt\.json$/);
});

test('builds a read-only non-authorizing receipt', () => {
  const out = buildReceipt(base);
  assert.equal(out.valid, true);
  assert.equal(out.receipt.standing.institutional_effect, 'none');
  assert.equal(out.receipt.standing.hall_receipt_claimed, false);
  assert.equal(out.receipt.standing.canon_claimed, false);
});

test('receipt round-trips through independent reconstruction', () => {
  const out = buildReceipt(base);
  const check = verifyReadback(JSON.parse(JSON.stringify(out.receipt)));
  assert.equal(check.valid, true);
});

test('tampering is detected by readback digest', () => {
  const out = buildReceipt(base);
  const changed = JSON.parse(JSON.stringify(out.receipt));
  changed.result.summary = 'Changed after persistence.';
  assert.equal(verifyReadback(changed).valid, false);
});

test('rejects mutation authority', () => {
  const out = buildReceipt({ ...base, task: { ...base.task, authority_ceiling: 'WRITE' } });
  assert.equal(out.valid, false);
  assert.equal(out.issues.some(x => x.code === 'invalid_authority_ceiling'), true);
});

test('rejects institutional effect claim', () => {
  const out = buildReceipt({ ...base, institutional_effect: 'approved' });
  assert.equal(out.valid, false);
  assert.equal(out.issues.some(x => x.code === 'institutional_effect_forbidden'), true);
});

test('accepts repository custody only with exact identities', () => {
  const out = buildReceipt({
    ...base,
    repository_receipt: {
      repository: 'sovereign-codex/Codex-control-center',
      commit_sha: 'd'.repeat(40),
      blob_sha: 'e'.repeat(40),
      content_sha256: 'f'.repeat(64)
    }
  });
  assert.equal(out.valid, true);
});

test('accepts independent Notion readback only when explicit', () => {
  const out = buildReceipt({
    ...base,
    notion_readback: {
      page_url: 'https://www.notion.so/example',
      reconstructed_content_sha256: 'a'.repeat(64),
      independent_readback: true
    }
  });
  assert.equal(out.valid, true);
});
