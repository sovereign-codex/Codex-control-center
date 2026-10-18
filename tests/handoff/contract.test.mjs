import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { prepareHandoff, CONTROL_CENTER } from '../../scripts/handoff/contract.mjs';
import { strictJson } from '../../scripts/handoff/normalization.mjs';
import { executeHandoff } from '../../scripts/handoff/executor.mjs';
import {
  actionsEvent, assertReady, fixturePolicy, MemoryService, observation,
  prepareDispatcher, prepareRouter, producerEvent, producerPayload, clone
} from './helpers.mjs';

test('disabled or unconfigured policy stops before all service calls', async () => {
  for (const mutate of [
    policy => { policy.enabled = false; },
    policy => { policy.producer_bindings = []; },
    policy => { policy.receiver.compatible = false; },
    policy => { policy.receiver.verified_commit = null; },
    policy => { policy.receiver.evidence_ref = null; }
  ]) {
    const policy = fixturePolicy(); mutate(policy);
    const prepared = prepareRouter({ policy });
    assert.equal(prepared.disposition, 'hold');
    const service = new MemoryService();
    const result = await executeHandoff(prepared, service);
    assert.equal(result.disposition, 'hold');
    assert.deepEqual(service.calls, []);
  }
});

test('trusted outer sender is bound to exact declared producer repository and workflow', async () => {
  const payloads = [
    producerPayload({ event: producerEvent({ repo: 'org/another' }) }),
    producerPayload({ event: producerEvent({ workflow: 'another-workflow' }) })
  ];
  const cases = payloads.map(payload => prepareRouter({ payload }));
  cases.push(prepareRouter({ event: actionsEvent(producerPayload(), { senderId: 999 }) }));
  for (const prepared of cases) {
    assert.equal(prepared.disposition, 'hold');
    const service = new MemoryService(); await executeHandoff(prepared, service);
    assert.deepEqual(service.calls, []);
  }
});

test('Router and Dispatcher have independent sender admission lists', async () => {
  const router = assertReady(prepareRouter());
  const valid = assertReady(prepareDispatcher(router));
  assert.equal(valid.request.body.event_type, 'avot_execution');
  const payload = clone(router.request.body.client_payload);
  const dispatcher = prepareDispatcher(router, { event: actionsEvent(payload, { stage: 'dispatcher', senderId: 123 }) });
  assert.equal(dispatcher.disposition, 'hold');
  const service = new MemoryService(); await executeHandoff(dispatcher, service);
  assert.deepEqual(service.calls, []);
});

test('caller request identity is required at root and contradictory nested identities hold', () => {
  const missing = producerPayload(); delete missing.request_id;
  const nestedOnly = producerPayload({ event: producerEvent({ request_id: 'nested-only-001' }) }); delete nestedOnly.request_id;
  const cases = [missing, nestedOnly,
    producerPayload({ request_id: ' padded' }),
    producerPayload({ request_id: '' }),
    producerPayload({ request_id: '../path' }),
    producerPayload({ request_id: 'a'.repeat(129) }),
    producerPayload({ request_id: 'line\nbreak' }),
    producerPayload({ request_id: 'unicode-\u2603' }),
    producerPayload({ event: producerEvent({ request_id: 'different-request' }) })
  ];
  for (const payload of cases) assert.equal(prepareRouter({ payload }).disposition, 'hold');
  assertReady(prepareRouter({ payload: producerPayload({ event: producerEvent({ request_id: 'caller-request-001' }) }) }));
});

test('delivery run, retry attempt, formatting, and observation time do not change semantic binding', () => {
  const payload = producerPayload();
  const outer = actionsEvent(payload);
  const a = assertReady(prepareRouter({ event: outer }));
  const b = assertReady(prepareRouter({
    bytes: Buffer.from(JSON.stringify(outer, null, 2) + '\n'),
    obs: observation({ runId: '7002', runAttempt: '3', observedAt: '2026-10-18T06:31:00.000Z' })
  }));
  const reverse = value => Array.isArray(value) ? value.map(reverse) : value && typeof value === 'object'
    ? Object.fromEntries(Object.entries(value).reverse().map(([key, entry]) => [key, reverse(entry)])) : value;
  const c = assertReady(prepareRouter({ event: reverse(outer) }));
  assert.equal(a.identity.key, b.identity.key);
  assert.equal(a.binding.fingerprint, b.binding.fingerprint);
  assert.equal(a.binding.fingerprint, c.binding.fingerprint);
  assert.notDeepEqual(a.evidence, b.evidence);
  const byteHash = createHash('sha256').update(Buffer.from(JSON.stringify(outer))).digest('hex');
  assert.ok(JSON.stringify(a.evidence).includes(byteHash), 'exact observed file hash remains in evidence');
});

test('same request identity binds changed substantive input and policy evidence differently', () => {
  const a = assertReady(prepareRouter());
  const b = assertReady(prepareRouter({ payload: producerPayload({ event: producerEvent({ payload: { content: 'changed' } }) }) }));
  const policy = fixturePolicy(); policy.receiver.verified_commit = 'b'.repeat(40);
  const c = assertReady(prepareRouter({ policy }));
  assert.equal(a.identity.key, b.identity.key);
  assert.notEqual(a.binding.fingerprint, b.binding.fingerprint);
  assert.equal(a.identity.key, c.identity.key);
  assert.notEqual(a.binding.fingerprint, c.binding.fingerprint);
});

test('full direct and wrapped event content survives normalization without changing producer status/time', () => {
  const event = producerEvent({ extension: { nested: ['a', 2, false] } });
  for (const payload of [producerPayload({ event }), { ...event, request_id: 'direct-request-001', target: 'avot-engine-runner' }]) {
    const ready = assertReady(prepareRouter({ payload }));
    const carried = ready.request.body.client_payload.event;
    for (const key of ['payload', 'governance', 'runtime_packet', 'extension', 'status', 'timestamp', 'trace_id']) {
      assert.deepEqual(carried[key], event[key]);
    }
    assert.equal(Object.keys(ready.request.body.client_payload).length, 4);
    assert.equal(ready.request.repository, CONTROL_CENTER);
    assert.equal(ready.request.body.event_type, 'engine_handoff');
  }
});

test('negative and compound positive-looking statuses hold; completion remains only a producer claim', () => {
  for (const status of ['dispatch_failed', 'route_failed', 'incomplete', 'partial', 'skipped', 'blocked', 'unknown', 'success_pending']) {
    assert.equal(prepareRouter({ payload: producerPayload({ event: producerEvent({ status }) }) }).disposition, 'hold', status);
  }
  const ready = assertReady(prepareRouter({ payload: producerPayload({ event: producerEvent({ status: 'completed' }) }) }));
  assert.equal(ready.request.body.client_payload.event.status, 'completed');
  assert.equal(ready.execution.completion_claim, false);
});

test('missing provenance is never backfilled from wrapper metadata or local observation', () => {
  for (const key of ['trace_id', 'repo', 'workflow', 'timestamp', 'status']) {
    const payload = producerPayload(); payload[key] = payload.event[key]; delete payload.event[key];
    assert.equal(prepareRouter({ payload }).disposition, 'hold', key);
  }
});

test('contradictory aliases, rich fields, and unreviewed destination selectors hold', () => {
  const cases = [
    producerPayload({ event: producerEvent({ source_repo: 'org/elsewhere' }) }),
    producerPayload({ event: producerEvent({ source: 'org/elsewhere' }) }),
    producerPayload({ governance: { posture: 'contradiction' } }),
    producerPayload({ target: 'cross-repo-dispatcher' }),
    producerPayload({ target: 'Tyme-Lab' }),
    producerPayload({ event: producerEvent({ destination: { repo: 'sovereign-codex/AVOT-engine', workflow: 'unreviewed.yml' } }) }),
    producerPayload({ event: producerEvent({ target_repo: 'sovereign-codex/Tyme-Lab' }) })
  ];
  for (const payload of cases) assert.equal(prepareRouter({ payload }).disposition, 'hold');
});

test('reserved Router metadata cannot be supplied at wrapper or event root', () => {
  for (const payload of [producerPayload({ _ccc_handoff: {} }), producerPayload({ event: producerEvent({ _ccc_handoff: {} }) })]) {
    assert.equal(prepareRouter({ payload }).disposition, 'hold');
  }
});

test('shell and prototype-shaped content remains inert preserved data', () => {
  const malicious = "'; touch /tmp/ccc_should_never_exist; #\n::error::not-a-command $(id) " + String.fromCharCode(96) + 'uname' + String.fromCharCode(96);
  const data = JSON.parse('{"__proto__":{"polluted":true},"constructor":{"prototype":{"danger":true}},"text":"safe"}');
  data.text = malicious;
  const ready = assertReady(prepareRouter({ payload: producerPayload({ event: producerEvent({ payload: data }) }) }));
  assert.deepEqual(ready.request.body.client_payload.event.payload, data);
  assert.equal(Object.hasOwn(ready.request.body.client_payload.event.payload, '__proto__'), true);
  assert.equal({}.polluted, undefined);
  assert.equal({}.danger, undefined);
});

test('invalid bytes, duplicate decoded keys, unsafe numbers, and impossible dates hold', () => {
  const valid = JSON.stringify(actionsEvent(producerPayload()));
  const cases = [
    Buffer.from(valid.replace('"trace_id":"trace-fixture-001"', '"trace_id":"trace-fixture-001","trace_id":"second"')),
    Buffer.from(valid.replace('"count":3', '"count":9007199254740993')),
    Buffer.from(valid.replace('2026-10-17T22:30:00-07:00', '2026-02-30T22:30:00-07:00')),
    Buffer.from([0xff, 0xfe]), Buffer.from('{'), Buffer.from('null')
  ];
  for (const bytes of cases) assert.equal(prepareRouter({ bytes }).disposition, 'hold');
});

test('wrong Actions surface or repository never becomes an admitted dispatch', () => {
  const wrongAction = actionsEvent(producerPayload(), { overrides: { action: 'route_event' } });
  const wrongRepo = actionsEvent(producerPayload(), { overrides: { repository: { full_name: 'org/elsewhere' } } });
  const cases = [
    prepareRouter({ event: wrongAction }), prepareRouter({ event: wrongRepo }),
    prepareRouter({ obs: observation({ eventName: 'pull_request' }) }),
    prepareRouter({ obs: observation({ repository: 'org/elsewhere' }) }),
    prepareHandoff({ stage: 'unknown', eventBytes: Buffer.from('{}'), observation: observation(), policy: fixturePolicy() })
  ];
  for (const prepared of cases) assert.equal(prepared.disposition, 'hold');
});

test('final payload expansion is bounded before a claim may be acquired', async () => {
  const prepared = prepareRouter({ payload: producerPayload({ event: producerEvent({ payload: { content: 'x'.repeat(65536) } }) }) });
  assert.equal(prepared.disposition, 'hold');
  const service = new MemoryService(); await executeHandoff(prepared, service);
  assert.deepEqual(service.calls, []);
});

test('JSON nesting accepts the 64-container boundary and rejects the next level before recursion', () => {
  const atLimit = '['.repeat(64) + '0' + ']'.repeat(64);
  const overLimit = '['.repeat(65) + '0' + ']'.repeat(65);
  let parsed;
  assert.doesNotThrow(() => { parsed = strictJson(atLimit); });
  for (let index = 0; index < 64; index += 1) {
    assert.ok(Array.isArray(parsed)); parsed = parsed[0];
  }
  assert.equal(parsed, 0);
  assert.throws(() => strictJson(overLimit), error => error.code === 'json_nesting_limit');
});

test('a small but excessively nested Actions event returns a structured hold with zero service calls', async () => {
  const fragment = '{"nested":'.repeat(2800) + '0' + '}'.repeat(2800);
  const raw = JSON.stringify(actionsEvent(producerPayload())).replace('"preserved producer content"', fragment);
  const bytes = Buffer.from(raw);
  assert.ok(bytes.length < 60_000, 'regression exercises depth, not the overall size gate');
  let prepared;
  assert.doesNotThrow(() => { prepared = prepareRouter({ bytes }); });
  assert.equal(prepared.disposition, 'hold');
  assert.ok(prepared.issues.some(issue => issue.code === 'invalid_event_json'));
  const service = new MemoryService();
  const result = await executeHandoff(prepared, service);
  assert.equal(result.disposition, 'hold');
  assert.deepEqual(service.calls, []);
});

test('moderately nested producer data remains intact through preparation and Dispatcher handoff', () => {
  let nested = { leaf: 'preserve this value' };
  for (let index = 0; index < 16; index += 1) nested = { child: nested };
  const router = assertReady(prepareRouter({ payload: producerPayload({ event: producerEvent({ payload: nested }) }) }));
  const dispatcher = assertReady(prepareDispatcher(router));
  assert.deepEqual(router.request.body.client_payload.event.payload, nested);
  assert.deepEqual(dispatcher.request.body.client_payload.event.payload, nested);
});

test('deep and malformed policies return structured holds without reaching a service', async () => {
  let nested = { value: 'deep policy extension' };
  for (let index = 0; index < 2800; index += 1) nested = { child: nested };
  const deep = fixturePolicy(); deep.extension = nested;
  const circular = fixturePolicy(); circular.extension = circular;
  const bigInteger = fixturePolicy(); bigInteger.extension = 1n;
  const wrongBindingShape = fixturePolicy(); wrongBindingShape.producer_bindings = {};
  const wrongDispatchers = fixturePolicy(); wrongDispatchers.dispatcher_sender_ids = ['not-a-GitHub-ID'];
  const cases = [undefined, null, [], 'policy', deep, circular, bigInteger, wrongBindingShape, wrongDispatchers];
  for (const policy of cases) {
    let prepared;
    assert.doesNotThrow(() => {
      prepared = prepareHandoff({ stage: 'router', eventBytes: Buffer.from(JSON.stringify(actionsEvent(producerPayload()))), observation: observation(), policy });
    });
    assert.equal(prepared.disposition, 'hold');
    assert.ok(prepared.issues.length > 0);
    const service = new MemoryService();
    const result = await executeHandoff(prepared, service);
    assert.equal(result.disposition, 'hold');
    assert.deepEqual(service.calls, []);
  }
});

test('preserved wrapper metadata that exceeds the outgoing nesting limit holds before claiming', async () => {
  let nested = 'preserved wrapper leaf';
  for (let index = 0; index < 61; index += 1) nested = { child: nested };
  const payload = producerPayload({ note: nested });
  const raw = JSON.stringify(actionsEvent(payload));
  assert.doesNotThrow(() => strictJson(raw), 'the original Actions event fits the 64-level input limit');
  const prepared = prepareRouter({ bytes: Buffer.from(raw) });
  assert.equal(prepared.disposition, 'hold');
  assert.ok(prepared.issues.some(issue => issue.code === 'dispatch_json_limit'));
  const service = new MemoryService();
  const result = await executeHandoff(prepared, service);
  assert.equal(result.disposition, 'hold');
  assert.deepEqual(service.calls, []);
});
