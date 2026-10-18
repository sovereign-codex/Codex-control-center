import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { createReviewHarness } from './candidate/adapter.mjs';

const read = name => readFileSync(new URL(`./fixtures/${name}`, import.meta.url), 'utf8');
const copy = value => JSON.parse(JSON.stringify(value));

export function runDemo() {
  const direct = read('direct-event.json');
  const nested = read('nested-event.json');
  const route = JSON.parse(read('route-decision.json'));
  const input = (rawJson, requestId, routeDecision = route) => ({ requestId, rawJson, ingressEventType: 'route-event', routeDecision: copy(routeDecision) });
  const scenarios = [];
  const h = createReviewHarness();
  const first = h.run(input(direct, 'DEMO-REQUEST-001'));
  scenarios.push({ id: 'direct_accepted', result: first, recorded_requests: h.requests });
  scenarios.push({ id: 'identical_duplicate', result: h.run(input(direct, 'DEMO-REQUEST-001')), recorded_request_count: h.requests.length });
  const changed = JSON.parse(direct);
  changed.payload.message = 'Changed work under the same request identity.';
  scenarios.push({ id: 'changed_content_collision', result: h.run(input(JSON.stringify(changed), 'DEMO-REQUEST-001')), recorded_request_count: h.requests.length });
  const hn = createReviewHarness();
  const nestedResult = hn.run(input(nested, 'DEMO-REQUEST-001'));
  scenarios.push({ id: 'nested_equivalent_fresh_instance', result: nestedResult, recorded_requests: hn.requests });
  for (const status of ['dispatch_failed', 'route_failed', 'result_failed', 'result_store_failed', 'incomplete', 'skipped', 'unknown']) {
    const e = JSON.parse(direct);
    e.status = status;
    const hs = createReviewHarness();
    scenarios.push({ id: `producer_${status}`, result: hs.run(input(JSON.stringify(e), `DEMO-STATUS-${status}`)), recorded_request_count: hs.requests.length });
  }
  const missing = JSON.parse(direct);
  delete missing.trace_id;
  const hm = createReviewHarness();
  scenarios.push({ id: 'missing_provenance', result: hm.run(input(JSON.stringify(missing), 'DEMO-MISSING-001')), recorded_request_count: hm.requests.length });
  const tyme = JSON.parse(direct);
  tyme.target = 'Tyme-Lab';
  const ht = createReviewHarness();
  scenarios.push({ id: 'tyme_missing_receiver', result: ht.run(input(JSON.stringify(tyme), 'DEMO-TYME-001', { ...route, target: 'Tyme-Lab', targetRepo: 'sovereign-codex/Tyme-Lab' })), recorded_request_count: ht.requests.length });
  for (const response of [{ type: 'http', status: 403 }, { type: 'error', message: 'Synthetic uncertain transport outcome.' }]) {
    const hf = createReviewHarness({ fakeResponse: response });
    const request = input(direct, `DEMO-RESPONSE-${response.type}`);
    scenarios.push({ id: `fake_${response.type}_response`, result: hf.run(request), repeated_result: hf.run(request), recorded_request_count: hf.requests.length });
  }
  return {
    schema_version: '1.0',
    candidate_id: 'CONTROL-CENTER-HANDOFF-001',
    generated_at_utc: new Date().toISOString(),
    standing: 'synthetic_local_demo',
    equality_checks: {
      normalized_event_digest_equal: first.evidence.normalized_event_sha256 === nestedResult.evidence.normalized_event_sha256,
      raw_digest_distinct: first.evidence.raw_sha256 !== nestedResult.evidence.raw_sha256,
      duplicate_and_collision_did_not_add_request: h.requests.length === 1
    },
    live_dispatch_performed: false,
    receiver_execution_observed: false,
    scenarios
  };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.stdout.write(`${JSON.stringify(runDemo(), null, 2)}\n`);
}
