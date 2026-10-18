import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createReviewHarness } from '../candidate/adapter.mjs';

const fixture = JSON.parse(readFileSync(new URL('../fixtures/direct-event.json', import.meta.url), 'utf8'));
const route = JSON.parse(readFileSync(new URL('../fixtures/route-decision.json', import.meta.url), 'utf8'));
const copy = value => JSON.parse(JSON.stringify(value));
const request = (event = copy(fixture), extra = {}) => ({ requestId: 'review-regression-001', rawJson: JSON.stringify(event), ingressEventType: 'route-event', routeDecision: copy(route), ...extra });
const held = (harness, result, code) => {
  assert.equal(result.disposition, 'hold');
  assert.equal(harness.requests.length, 0);
  assert.ok(result.issues.some(issue => issue.code === code), JSON.stringify(result.issues));
  assert.equal(result.execution.completed, false);
};

test('R01: conflicting legacy source cannot survive repo normalization', () => {
  for (const nested of [false, true]) {
    const e = copy(fixture);
    e.source = 'sovereign-codex/DIFFERENT';
    const raw = nested ? { target: e.target, source: e.source, event: Object.fromEntries(Object.entries(e).filter(([k]) => !['target', 'source'].includes(k))) } : e;
    const h = createReviewHarness();
    const result = h.run(request(raw));
    held(h, result, 'conflicting_source');
    assert.equal(JSON.parse(result.evidence.raw_json).source, e.source);
  }
});

test('R02: consistent legacy source is preserved; source alone cannot fill repo', () => {
  const e = copy(fixture);
  e.source = e.repo;
  const h = createReviewHarness();
  const result = h.run(request(e));
  assert.equal(result.disposition, 'transport_accepted');
  assert.equal(result.event.source, e.source);
  delete e.repo;
  const missing = createReviewHarness();
  held(missing, missing.run(request(e)), 'missing_source_repo');
});

test('R03: non-null workflow and AVOT destination selectors require a reviewed meaning', () => {
  for (const key of ['workflow', 'avot']) {
    for (const nested of [false, true]) {
      const e = copy(fixture);
      e.destination = { repo: route.targetRepo, [key]: 'control-center-recovery' };
      const raw = nested ? { target: e.target, destination: e.destination, event: Object.fromEntries(Object.entries(e).filter(([k]) => !['target', 'destination'].includes(k))) } : e;
      const h = createReviewHarness();
      held(h, h.run(request(raw)), 'unsupported_destination_selector');
    }
  }
});

test('R04: null workflow and AVOT selectors remain unspecified, preserved values', () => {
  const e = copy(fixture);
  e.destination = { repo: route.targetRepo, workflow: null, avot: null };
  const h = createReviewHarness();
  const result = h.run(request(e));
  assert.equal(result.disposition, 'transport_accepted');
  assert.deepEqual(result.event.destination, e.destination);
});

test('R05: literal lone surrogates are rejected before a misleading byte digest exists', () => {
  const h = createReviewHarness();
  for (const unit of [0xD800, 0xD801, 0xDC00]) {
    const rawJson = JSON.stringify(fixture).replace('Synthetic local input.', String.fromCharCode(unit));
    const result = h.run(request(undefined, { rawJson }));
    held(h, result, 'invalid_unicode');
    assert.equal(result.evidence.raw_sha256, null);
    assert.equal(result.evidence.raw_json, rawJson);
  }
});

test('R06: escaped surrogate JSON sequences retain distinct exact-byte identities', () => {
  const h = createReviewHarness();
  const raw1 = JSON.stringify(fixture).replace('Synthetic local input.', '\\ud800');
  const raw2 = JSON.stringify(fixture).replace('Synthetic local input.', '\\ud801');
  const first = h.run(request(undefined, { rawJson: raw1 }));
  const second = h.run(request(undefined, { rawJson: raw2 }));
  assert.equal(first.disposition, 'transport_accepted');
  assert.equal(second.disposition, 'identity_collision');
  assert.notEqual(first.evidence.raw_sha256, second.evidence.raw_sha256);
  assert.equal(h.requests.length, 1);
});

test('R07: well-formed astral Unicode survives request preservation', () => {
  const e = copy(fixture);
  e.payload.message = 'Fixture \u{1F30D}';
  const h = createReviewHarness();
  const result = h.run(request(e));
  assert.equal(result.disposition, 'transport_accepted');
  assert.equal(h.requests[0].body.client_payload.event.payload.message, e.payload.message);
});

test('R08: nonobject API inputs produce structured holds without fabricated provenance', () => {
  for (const input of [null, [], 'payload', 1, true]) {
    const h = createReviewHarness();
    const result = h.run(input);
    held(h, result, 'invalid_input');
    assert.equal(result.provenance.trace_id, null);
    assert.equal(result.provenance.declared_source_repo, null);
  }
});

test('R09: an external mutation cannot alter the configured observation clock', () => {
  const options = { observedAt: '2026-10-18T04:00:00Z' };
  const h = createReviewHarness(options);
  options.observedAt = 'not-a-time';
  const result = h.run(request());
  assert.equal(result.observation.observed_at, '2026-10-18T04:00:00Z');
  assert.equal(result.observation.clock_mode, 'fixed_fixture');
  assert.equal(result.event.timestamp, fixture.timestamp);
});

test('R10: wrapper-only source_event is held instead of becoming legacy producer evidence', () => {
  const e = copy(fixture);
  const raw = { target: e.target, source_event: 'claimed-event', event: Object.fromEntries(Object.entries(e).filter(([k]) => k !== 'target')) };
  const h = createReviewHarness();
  const result = h.run(request(raw));
  held(h, result, 'misplaced_source_event');
  assert.equal(Object.hasOwn(result.event, 'source_event'), false);
});
