import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  classifyStatus,
  normalizeHandoff,
  createReviewHarness,
} from '../candidate/adapter.mjs';

// Independent contract tests for the isolated, fake-transport review candidate.
// The ten category IDs come from TYME-HANDOFF-REVIEW-001, not live workflows.
// No baseline workflow is imported, no credential is read, and no network is used.
const INTERNAL_REPO = 'sovereign-codex/Codex-control-center';
const ENGINE_REPO = 'sovereign-codex/AVOT-engine';
const TYME_REPO = 'sovereign-codex/Tyme-Lab';
const TARGET = 'avot-engine-runner';
const PRODUCED_AT = '2026-10-17T16:42:00-07:00';
const OBSERVED_AT = '2026-10-18T00:00:00Z';
const ROUTE = Object.freeze({
  stage: 'cross-repo-dispatcher',
  target: TARGET,
  targetRepo: ENGINE_REPO,
  receivingEventType: 'avot_execution',
});

function fixtureEvent(changes = {}) {
  return {
    trace_id: 'trace-acceptance-001',
    repo: 'sovereign-codex/AVOT-ARCHIVIST',
    workflow: 'archivist-dispatch',
    status: 'received',
    timestamp: PRODUCED_AT,
    payload: {
      task: 'read_only_diagnostic',
      input: { text: 'TYME — preserve this request', values: [0, false, null] },
    },
    governance: { authority_effect: 'none', mutation_allowed: false },
    runtime_packet: {
      packet_id: 'runtime-acceptance-001',
      execution_state: 'pending',
      open_conditions: ['receiver execution has not been observed'],
    },
    extension: { keep: 'event extension' },
    ...changes,
  };
}

function inputFor(rawObject = { target: TARGET, event: fixtureEvent() }, changes = {}) {
  return {
    requestId: 'request-acceptance-001',
    rawJson: JSON.stringify(rawObject),
    ingressEventType: 'route-event',
    routeDecision: { ...ROUTE },
    ...changes,
  };
}

function harness(options = {}) {
  return createReviewHarness({
    observedAt: OBSERVED_AT,
    diagnosticPrefix: 'acceptance-local',
    fakeResponse: { type: 'http', status: 204 },
    ...options,
  });
}

function assertUnverified(result) {
  assert.equal(result.execution.status, 'unverified');
  assert.equal(result.execution.completed, false);
  assert.equal(result.execution.receiver_run_id, null);
  assert.equal(result.execution.artifact_id, null);
  assert.equal(result.provenance.authenticated, false);
}

function assertHeldWithoutDispatch(result, reviewHarness) {
  assert.equal(result.disposition, 'hold');
  assert.ok(result.issues.length > 0, 'a hold must explain the missing or conflicting evidence');
  assert.equal(result.transport.status, 'not_attempted');
  assert.equal(reviewHarness.requests.length, 0);
  assertUnverified(result);
}

function sha256(value) {
  return createHash('sha256').update(value, 'utf8').digest('hex');
}

test('[legacy_shapes] direct and wrapped inputs preserve one normalized event and distinct raw evidence', () => {
  const event = fixtureEvent();
  const direct = inputFor({ target: TARGET, ...event });
  const wrapped = inputFor({ target: TARGET, event });
  const beforeDirect = structuredClone(direct);
  const beforeWrapped = structuredClone(wrapped);
  const directResult = harness().run(direct);
  const wrappedResult = harness().run(wrapped);

  assert.equal(directResult.disposition, 'transport_accepted');
  assert.equal(wrappedResult.disposition, 'transport_accepted');
  assert.deepEqual(directResult.event, wrappedResult.event);
  assert.deepEqual(directResult.provenance, wrappedResult.provenance);
  assert.equal(directResult.evidence.normalized_event_sha256, wrappedResult.evidence.normalized_event_sha256);
  for (const result of [directResult, wrappedResult]) {
    for (const field of ['payload', 'governance', 'runtime_packet', 'extension']) {
      assert.deepEqual(result.event[field], event[field]);
    }
    assert.equal(result.evidence.raw_sha256, sha256(result.evidence.raw_json));
    assertUnverified(result);
  }
  assert.equal(directResult.evidence.raw_json, direct.rawJson);
  assert.equal(wrappedResult.evidence.raw_json, wrapped.rawJson);
  assert.notEqual(directResult.evidence.raw_sha256, wrappedResult.evidence.raw_sha256);
  assert.deepEqual(direct, beforeDirect);
  assert.deepEqual(wrapped, beforeWrapped);
});

test('[legacy_shapes] wrapper-only rich fields and wrapper extensions survive the recorded request', () => {
  const event = fixtureEvent();
  const { payload, governance, runtime_packet, ...inner } = event;
  const wrapper = {
    target: TARGET,
    event: inner,
    payload,
    governance,
    runtime_packet,
    wrapper_extension: { source_artifact: 'artifact-fixture-001', retained: true },
  };
  const h = harness();
  const result = h.run(inputFor(wrapper));
  assert.equal(result.disposition, 'transport_accepted');
  for (const field of ['payload', 'governance', 'runtime_packet']) {
    assert.deepEqual(result.event[field], event[field]);
    assert.deepEqual(h.requests[0].body.client_payload.event[field], event[field]);
  }
  assert.deepEqual(h.requests[0].body.client_payload.wrapper_extension, wrapper.wrapper_extension);
});

test('[legacy_shapes] canonical producer aliases agree with legacy identity without manufacturing authentication', () => {
  const legacy = fixtureEvent();
  const canonical = fixtureEvent({ source_repo: legacy.repo, source_workflow: legacy.workflow });
  delete canonical.repo;
  delete canonical.workflow;
  const matching = fixtureEvent({ source_repo: legacy.repo, source_workflow: legacy.workflow });
  const results = [legacy, canonical, matching].map((event) => normalizeHandoff(inputFor({ target: TARGET, event })));
  for (const result of results) {
    assert.equal(result.disposition, 'ready');
    assert.equal(result.provenance.declared_source_repo, legacy.repo);
    assert.equal(result.provenance.declared_source_workflow, legacy.workflow);
    assert.equal(result.provenance.authenticated, false);
  }
});

test('[internal_event] records exactly the internal engine_handoff request while preserving final destination', () => {
  const h = harness();
  const result = h.run(inputFor());
  assert.equal(result.disposition, 'transport_accepted');
  assert.equal(h.requests.length, 1);
  const request = h.requests[0];
  assert.equal(request.repository, INTERNAL_REPO);
  assert.equal(request.body.event_type, 'engine_handoff');
  assert.equal(request.body.client_payload.target, TARGET);
  assert.deepEqual(request.body.client_payload.event, result.event);
  assert.deepEqual(result.request, request);
  assert.equal(result.routing.next_stage, 'cross-repo-dispatcher');
  assert.equal(result.routing.internal_event_type, 'engine_handoff');
  assert.equal(result.routing.destination.target, TARGET);
  assert.equal(result.routing.destination.repository, ENGINE_REPO);
  assert.equal(result.routing.destination.event_type, 'avot_execution');
  assert.equal(result.routing.destination.live_receiver_verified, false);
  assert.notEqual(request.repository, result.routing.destination.repository);
  assert.notEqual(request.body.event_type, result.routing.destination.event_type);
});

test('[internal_event] unsupported ingress or stage does not silently select the accepted contract', () => {
  for (const change of [
    { ingressEventType: 'route_event' },
    { ingressEventType: 'engine_handoff' },
    { routeDecision: { ...ROUTE, stage: 'control-center-result-receiver' } },
  ]) {
    const h = harness();
    assertHeldWithoutDispatch(h.run(inputFor(undefined, change)), h);
  }
});

test('[conflicting_target] contradictory route declarations hold and preserve their original evidence', () => {
  const cases = [
    inputFor({ target: TARGET, event: fixtureEvent({ target: 'avot-forge' }) }),
    inputFor(undefined, { routeDecision: { ...ROUTE, target: 'avot-forge' } }),
    inputFor(undefined, { routeDecision: { ...ROUTE, targetRepo: 'sovereign-codex/AVOT-forge' } }),
    inputFor({ target: TARGET, target_repo: 'sovereign-codex/AVOT-forge', event: fixtureEvent() }),
    inputFor(undefined, { routeDecision: { ...ROUTE, receivingEventType: 'unreviewed_event' } }),
  ];
  for (const input of cases) {
    const h = harness();
    const before = structuredClone(input);
    const result = h.run(input);
    assertHeldWithoutDispatch(result, h);
    assert.equal(result.evidence.raw_json, input.rawJson);
    assert.equal(result.evidence.raw_sha256, sha256(input.rawJson));
    assert.deepEqual(input, before);
  }
});

test('[conflicting_target] missing target cannot be inferred from the route stage alone', () => {
  const input = inputFor({ event: fixtureEvent() }, { routeDecision: { stage: 'cross-repo-dispatcher' } });
  const h = harness();
  assertHeldWithoutDispatch(h.run(input), h);
});

test('[conflicting_target] conflicting rich wrapper and event data is held rather than overwritten', () => {
  for (const field of ['payload', 'governance', 'runtime_packet']) {
    const event = fixtureEvent();
    const h = harness();
    const input = inputFor({ target: TARGET, event, [field]: { different: 'contradictory wrapper value' } });
    const result = h.run(input);
    assertHeldWithoutDispatch(result, h);
    assert.deepEqual(JSON.parse(result.evidence.raw_json), JSON.parse(input.rawJson));
  }
});

test('[conflicting_target] identical double declarations of rich data do not create a false conflict', () => {
  const event = fixtureEvent();
  const h = harness();
  const result = h.run(inputFor({
    target: TARGET,
    event,
    payload: structuredClone(event.payload),
    governance: structuredClone(event.governance),
    runtime_packet: structuredClone(event.runtime_packet),
  }));
  assert.equal(result.disposition, 'transport_accepted');
  assert.equal(h.requests.length, 1);
});

test('[missing_provenance] absent, null, or blank required producer fields hold without local substitution', () => {
  for (const field of ['trace_id', 'repo', 'workflow', 'timestamp']) {
    for (const value of [undefined, null, '', '   ']) {
      const event = fixtureEvent({ [field]: value });
      const h = harness();
      const result = h.run(inputFor({ target: TARGET, event }));
      assertHeldWithoutDispatch(result, h);
      assert.equal(result.observation.observed_at, OBSERVED_AT);
      assert.equal(result.evidence.raw_json, JSON.stringify({ target: TARGET, event }));
      if (field === 'trace_id') {
        assert.notEqual(result.provenance.trace_id, result.observation.diagnostic_id);
      }
      if (field === 'timestamp') {
        assert.notEqual(result.event?.timestamp, OBSERVED_AT);
      }
    }
  }
});

test('[missing_provenance] caller request identity is required and never replaced by a diagnostic identity', () => {
  for (const requestId of [undefined, null, '', '   ', 42]) {
    const h = harness();
    const result = h.run(inputFor(undefined, { requestId }));
    assertHeldWithoutDispatch(result, h);
    assert.notEqual(result.provenance.request_id, result.observation.diagnostic_id);
  }
});

test('[missing_provenance] disagreeing canonical and legacy producer identities are explicit holds', () => {
  for (const changes of [
    { source_repo: 'sovereign-codex/AVOT-forge' },
    { source_workflow: 'different-producer-workflow' },
  ]) {
    const h = harness();
    const input = inputFor({ target: TARGET, event: fixtureEvent(changes) });
    const result = h.run(input);
    assertHeldWithoutDispatch(result, h);
    assert.equal(result.evidence.raw_json, input.rawJson);
  }
});

test('[missing_provenance] invalid or timezone-free timestamps do not gain authority through Date.parse coercion', () => {
  for (const timestamp of [
    '2026-10-17T16:42:00',
    '2026-10-17',
    '2026-02-30T12:00:00Z',
    '2026-13-01T12:00:00Z',
    '2026-10-17T16:42:00+24:00',
    'not-a-timestamp',
    1792280520000,
  ]) {
    const h = harness();
    const result = h.run(inputFor({ target: TARGET, event: fixtureEvent({ timestamp }) }));
    assertHeldWithoutDispatch(result, h);
    assert.equal(result.event?.timestamp, timestamp);
  }
});

test('[missing_provenance] malformed JSON and non-object roots are held before fake transport', () => {
  for (const rawJson of ['{', 'null', '[]', '"plain text"', '42']) {
    const h = harness();
    const result = h.run(inputFor(undefined, { rawJson }));
    assertHeldWithoutDispatch(result, h);
    assert.equal(result.evidence.raw_json, rawJson);
  }
});

test('[missing_provenance] duplicate JSON keys are rejected at the root, nested, and escaped-name boundaries', () => {
  const normal = inputFor();
  const raws = [
    normal.rawJson.replace('"target":"avot-engine-runner"', '"target":"avot-engine-runner","target":"avot-forge"'),
    normal.rawJson.replace('"trace_id":"trace-acceptance-001"', '"trace_id":"trace-acceptance-001","trace_id":"other-trace"'),
    normal.rawJson.replace('"trace_id":"trace-acceptance-001"', '"trace_id":"trace-acceptance-001","\\u0074race_id":"other-trace"'),
    normal.rawJson.replace('"values":[0,false,null]', '"values":[0,false,null],"values":[1]'),
  ];
  for (const rawJson of raws) {
    assert.notEqual(rawJson, normal.rawJson, 'the adversarial fixture must actually differ');
    const h = harness();
    const result = h.run({ ...normal, rawJson });
    assertHeldWithoutDispatch(result, h);
    assert.equal(result.evidence.raw_json, rawJson);
  }
});

test('[failure_status] failure-bearing labels never normalize to progress or completion', () => {
  for (const status of [
    'dispatch_failed',
    'route_failed',
    'result_failed',
    'result_store_failed',
    'result_send_error',
    'decision_created_failed',
    'execution_completed_failed',
    '  DISPATCH_FAILED  ',
  ]) {
    const classified = classifyStatus(status);
    assert.equal(classified.raw, status);
    assert.equal(classified.category, 'failure');
    const h = harness();
    const result = h.run(inputFor({ target: TARGET, event: fixtureEvent({ status }) }));
    assertHeldWithoutDispatch(result, h);
    assert.equal(result.event.status, status);
    assert.equal(result.producer_outcome.raw, status);
    assert.equal(result.producer_outcome.category, 'failure');
  }
});

test('[non_success] incomplete, partial, skipped, blocked, and unknown outcomes remain non-success', () => {
  const cases = [
    ['incomplete', 'incomplete'],
    ['partial', 'partial'],
    ['skipped', 'skipped'],
    ['blocked', 'blocked'],
    ['unknown', 'unknown'],
    ['not_complete', 'unknown'],
    ['mystery_stage', 'unknown'],
    ['completed_with_warnings', 'unknown'],
    ['', 'unknown'],
  ];
  for (const [status, category] of cases) {
    const classified = classifyStatus(status);
    assert.equal(classified.raw, status);
    assert.equal(classified.category, category);
    const h = harness();
    const result = h.run(inputFor({ target: TARGET, event: fixtureEvent({ status }) }));
    assertHeldWithoutDispatch(result, h);
    assert.equal(result.producer_outcome.raw, status);
    assert.equal(result.producer_outcome.category, category);
    assert.equal(result.event.status, status);
  }
});

test('[non_success] non-string status values are held without truthy coercion', () => {
  for (const status of [undefined, null, true, 1, { state: 'completed' }, ['completed']]) {
    const h = harness();
    const result = h.run(inputFor({ target: TARGET, event: fixtureEvent({ status }) }));
    assertHeldWithoutDispatch(result, h);
  }
});

test('[non_success] an exact producer completion report does not become verified receiver completion', () => {
  const h = harness();
  const result = h.run(inputFor({ target: TARGET, event: fixtureEvent({ status: 'execution_completed' }) }));
  assert.equal(result.disposition, 'transport_accepted');
  assert.equal(result.producer_outcome.category, 'reported_completion');
  assert.equal(result.producer_outcome.raw, 'execution_completed');
  assert.equal(result.event.timestamp, PRODUCED_AT);
  assert.equal(result.observation.observed_at, OBSERVED_AT);
  assert.notEqual(result.event.timestamp, result.observation.observed_at);
  assertUnverified(result);
});

test('[identity_collision] same request identity with changed rich content collides without a second request', () => {
  for (const field of ['payload', 'governance', 'runtime_packet']) {
    const h = harness();
    const first = h.run(inputFor());
    assert.equal(first.disposition, 'transport_accepted');
    const changed = inputFor({ target: TARGET, event: fixtureEvent({ [field]: { changed: true } }) });
    const result = h.run(changed);
    assert.equal(result.disposition, 'identity_collision');
    assert.equal(h.requests.length, 1);
    assert.equal(result.transport.status, 'not_attempted');
    assert.equal(result.evidence.raw_json, changed.rawJson);
    assertUnverified(result);
  }
});

test('[identity_collision] byte changes collide even when parsed JSON values are equivalent', () => {
  const original = inputFor();
  const parsed = JSON.parse(original.rawJson);
  const reordered = { event: parsed.event, target: parsed.target };
  for (const rawJson of [JSON.stringify(parsed, null, 2), JSON.stringify(reordered)]) {
    assert.deepEqual(JSON.parse(rawJson), parsed);
    const h = harness();
    h.run(original);
    const result = h.run({ ...original, rawJson });
    assert.equal(result.disposition, 'identity_collision');
    assert.equal(h.requests.length, 1);
    assert.equal(result.transport.status, 'not_attempted');
  }
});

test('[identity_collision] route decision and ingress are included in the request identity binding', () => {
  for (const changed of [
    { ingressEventType: 'route_event' },
    { routeDecision: { ...ROUTE, receivingEventType: 'changed_event' } },
  ]) {
    const h = harness();
    const original = inputFor();
    h.run(original);
    const result = h.run({ ...original, ...changed });
    assert.equal(result.disposition, 'identity_collision');
    assert.equal(h.requests.length, 1);
    assert.equal(result.transport.status, 'not_attempted');
  }
});

test('[duplicate] identical repeats are explicit local duplicates and keep the prior observation', () => {
  const h = harness();
  const input = inputFor();
  const first = h.run(input);
  const second = h.run(structuredClone(input));
  assert.equal(first.disposition, 'transport_accepted');
  assert.equal(second.disposition, 'duplicate');
  assert.equal(h.requests.length, 1);
  assert.equal(second.transport.status, 'not_attempted');
  assert.ok(second.prior_observation, 'duplicate handling must retain the original local outcome');
  assertUnverified(second);

  const fresh = harness();
  assert.equal(fresh.run(input).disposition, 'transport_accepted');
  assert.equal(fresh.requests.length, 1, 'deduplication is confined to one harness instance');
});

test('[duplicate] fake HTTP rejection and fake error are not retried by an identical repeat', () => {
  for (const [fakeResponse, disposition] of [
    [{ type: 'http', status: 503 }, 'transport_rejected'],
    [{ type: 'error', message: 'fixture connection error' }, 'transport_error'],
  ]) {
    const h = harness({ fakeResponse });
    const first = h.run(inputFor());
    assert.equal(first.disposition, disposition);
    const second = h.run(inputFor());
    assert.equal(second.disposition, 'duplicate');
    assert.equal(second.transport.status, 'not_attempted');
    assert.equal(h.requests.length, 1);
    assert.ok(second.prior_observation);
  }
});

test('[duplicate] a hold with complete declared identity reserves its request without attempting transport', () => {
  const h = harness();
  const input = inputFor({ target: TARGET, event: fixtureEvent({ status: 'blocked' }) });
  const first = h.run(input);
  assertHeldWithoutDispatch(first, h);
  const repeat = h.run(input);
  assert.equal(repeat.disposition, 'duplicate');
  assert.equal(repeat.transport.status, 'not_attempted');
  assert.equal(h.requests.length, 0);
  assert.ok(repeat.prior_observation);
});

test('[duplicate] a missing declared producer namespace cannot reserve or fabricate request identity', () => {
  const event = fixtureEvent();
  delete event.repo;
  const h = harness();
  const input = inputFor({ target: TARGET, event });
  assertHeldWithoutDispatch(h.run(input), h);
  assertHeldWithoutDispatch(h.run(input), h);
});

test('[duplicate] equal request IDs from distinct declared producer repositories are separate local identities', () => {
  const h = harness();
  const first = h.run(inputFor());
  const second = h.run(inputFor({ target: TARGET, event: fixtureEvent({ repo: TYME_REPO }) }));
  assert.equal(first.disposition, 'transport_accepted');
  assert.equal(second.disposition, 'transport_accepted');
  assert.equal(h.requests.length, 2);
  assert.notEqual(first.provenance.declared_source_repo, second.provenance.declared_source_repo);
  assert.equal(second.provenance.authenticated, false);
});

test('[transport_only] HTTP 204 means fake transport acceptance with no receiver execution or artifact', () => {
  const h = harness();
  const result = h.run(inputFor());
  assert.equal(result.disposition, 'transport_accepted');
  assert.equal(result.transport.mode, 'fake');
  assert.equal(result.transport.status, 'accepted');
  assert.equal(result.transport.http_status, 204);
  assert.equal(h.requests.length, 1);
  assertUnverified(result);
});

test('[transport_only] every other fake HTTP status remains rejected, including other 2xx statuses', () => {
  for (const status of [200, 202, 400, 401, 403, 422, 500, 503]) {
    const h = harness({ fakeResponse: { type: 'http', status } });
    const result = h.run(inputFor());
    assert.equal(result.disposition, 'transport_rejected');
    assert.equal(result.transport.mode, 'fake');
    assert.equal(result.transport.status, 'rejected');
    assert.equal(result.transport.http_status, status);
    assert.equal(h.requests.length, 1);
    assertUnverified(result);
  }
});

test('[transport_only] fake transport exceptions retain an error outcome without a success label', () => {
  const h = harness({ fakeResponse: { type: 'error', message: 'fixture transport unavailable' } });
  const result = h.run(inputFor());
  assert.equal(result.disposition, 'transport_error');
  assert.equal(result.transport.mode, 'fake');
  assert.equal(result.transport.status, 'error');
  assert.equal(result.transport.http_status, null);
  assert.equal(h.requests.length, 1);
  assertUnverified(result);
});

test('[transport_only] returned request snapshots cannot mutate recorded fake transport evidence', () => {
  const h = harness();
  const result = h.run(inputFor());
  const expected = structuredClone(h.requests);
  const externalCopy = h.requests;
  externalCopy[0].body.event_type = 'altered_event';
  externalCopy[0].body.client_payload.event.payload.input.text = 'altered payload';
  externalCopy.push({ repository: 'unexpected' });
  result.request.body.client_payload.event.governance.authority_effect = 'altered';
  assert.deepEqual(h.requests, expected);
});

test('[missing_receiver] selecting Tyme-Lab holds before even the available fake 204 response', () => {
  const cases = [
    inputFor({ target: 'tyme-lab', event: fixtureEvent() }, {
      routeDecision: { ...ROUTE, target: 'tyme-lab', targetRepo: TYME_REPO },
    }),
    inputFor(undefined, { routeDecision: { ...ROUTE, targetRepo: TYME_REPO } }),
    inputFor({ target: TARGET, target_repo: TYME_REPO, event: fixtureEvent() }),
    inputFor({ target: TARGET, event: fixtureEvent({ target_repo: TYME_REPO }) }),
  ];
  for (const input of cases) {
    const h = harness();
    const result = h.run(input);
    assertHeldWithoutDispatch(result, h);
    assert.ok(result.issues.some((issue) => issue.code === 'missing_receiver'));
    assert.equal(result.evidence.raw_json, input.rawJson);
  }
});

test('[missing_receiver] Tyme-Lab as a producer or text value is not mistaken for a selected destination', () => {
  const event = fixtureEvent({ repo: TYME_REPO });
  event.payload.note = 'Tyme-Lab receiver remains a later prerequisite';
  const h = harness();
  const result = h.run(inputFor({ target: TARGET, event }));
  assert.equal(result.disposition, 'transport_accepted');
  assert.equal(result.routing.destination.repository, ENGINE_REPO);
  assert.equal(result.provenance.declared_source_repo, TYME_REPO);
  assertUnverified(result);
});

test('[missing_receiver] another unreviewed destination is held rather than accepted because a map entry exists', () => {
  const h = harness();
  const input = inputFor({ target: 'avot-forge', event: fixtureEvent() }, {
    routeDecision: { ...ROUTE, target: 'avot-forge', targetRepo: 'sovereign-codex/AVOT-forge' },
  });
  const result = h.run(input);
  assertHeldWithoutDispatch(result, h);
  assert.ok(result.issues.some((issue) => issue.code === 'unreviewed_destination'));
});
