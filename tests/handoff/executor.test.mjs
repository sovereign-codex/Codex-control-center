import test from 'node:test';
import assert from 'node:assert/strict';
import { executeHandoff } from '../../scripts/handoff/executor.mjs';
import { gitBlobSha, recordBytes } from '../../scripts/handoff/contract.mjs';
import {
  assertNoCompletion, assertReady, clone, MemoryService, observation,
  prepareDispatcher, prepareRouter, producerEvent, producerPayload
} from './helpers.mjs';

test('one verified claim admits one request and persists a separate outcome', async () => {
  const prepared = assertReady(prepareRouter());
  const service = new MemoryService();
  const result = await executeHandoff(prepared, service);
  assert.equal(result.disposition, 'transport_accepted');
  assert.equal(result.transport.status, 'accepted');
  assert.equal(result.transport.http_status, 204);
  assertNoCompletion(result);
  assert.equal(service.dispatches.length, 1);
  assert.deepEqual(service.dispatches[0].request, prepared.request);
  const creates = service.calls.filter(call => call.kind === 'createRecord');
  assert.equal(creates.length, 2);
  assert.match(creates[0].path, /^handoff-ledger\/v1\/router\/[0-9a-f]{64}\/claim\.json$/);
  assert.match(creates[1].path, /\/outcome\.json$/);
  assert.notEqual(creates[0].path, creates[1].path);
});

test('a fresh runner instance with the same caller binding is a duplicate after acceptance', async () => {
  const service = new MemoryService();
  const first = await executeHandoff(assertReady(prepareRouter()), service);
  const again = assertReady(prepareRouter({ obs: observation({ runId: '7002', runAttempt: '3', observedAt: '2026-10-18T06:31:00.000Z' }) }));
  const result = await executeHandoff(again, service);
  assert.equal(first.disposition, 'transport_accepted');
  assert.equal(result.disposition, 'duplicate');
  assert.equal(service.dispatches.length, 1);
  assertNoCompletion(result);
});

test('same caller identity with different data is a collision and does not overwrite prior records', async () => {
  const service = new MemoryService();
  await executeHandoff(assertReady(prepareRouter()), service);
  const before = clone([...service.records.entries()]);
  const changed = assertReady(prepareRouter({ payload: producerPayload({ event: producerEvent({ payload: { content: 'different' } }) }) }));
  const result = await executeHandoff(changed, service);
  assert.equal(result.disposition, 'identity_collision');
  assert.equal(service.dispatches.length, 1);
  assert.deepEqual([...service.records.entries()], before);
});

test('competing Actions runs race on create-only claim and yield at most one transport attempt', async () => {
  const service = new MemoryService({ raceClaims: 2 });
  const a = assertReady(prepareRouter());
  const b = assertReady(prepareRouter({ obs: observation({ runId: '7002' }) }));
  const results = await Promise.all([executeHandoff(a, service), executeHandoff(b, service)]);
  assert.deepEqual(results.map(result => result.disposition).sort(), ['duplicate', 'transport_accepted']);
  assert.equal(service.dispatches.length, 1);
  assert.equal([...service.records.keys()].filter(path => path.endsWith('/claim.json')).length, 1);
});

test('non-created claim statuses and an incorrect 201 blob SHA never authorize dispatch', async () => {
  for (const reply of [
    { status: 200, blobSha: null }, { status: 409, blobSha: null },
    { status: 422, blobSha: null }, { status: 500, blobSha: null },
    { status: 201, blobSha: '0'.repeat(40) }, { status: 201, blobSha: null }
  ]) {
    const service = new MemoryService({ claimReply: reply });
    const result = await executeHandoff(assertReady(prepareRouter()), service);
    // The deliberately incorrect 201 response still wrote the valid fake
    // claim. Readback may classify it as a duplicate, but cannot grant a send.
    assert.equal(result.disposition, reply.status === 201 ? 'duplicate' : 'hold', JSON.stringify(reply));
    assert.equal(service.dispatches.length, 0);
    assertNoCompletion(result);
  }
});

test('ambiguous claim creation does not dispatch even when a committed claim exists', async () => {
  const service = new MemoryService();
  const create = service.createRecord.bind(service);
  service.createRecord = async (path, record) => {
    const reply = await create(path, record);
    if (path.endsWith('/claim.json') && reply.status === 201) throw new Error('fixture: response lost after commit');
    return reply;
  };
  const first = await executeHandoff(assertReady(prepareRouter()), service);
  assert.equal(service.dispatches.length, 0);
  assert.ok(['hold', 'duplicate'].includes(first.disposition));
  service.createRecord = create;
  const second = await executeHandoff(assertReady(prepareRouter({ obs: observation({ runId: '7003' }) })), service);
  assert.equal(second.disposition, 'duplicate');
  assert.equal(service.dispatches.length, 0);
  assertNoCompletion(second);
});

test('an existing claim without outcome stays duplicate and cannot be resumed', async () => {
  const service = new MemoryService({ outcomeReply: new Error('fixture: outcome storage unavailable') });
  await executeHandoff(assertReady(prepareRouter()), service);
  assert.equal([...service.records.keys()].filter(path => path.endsWith('/outcome.json')).length, 0);
  const result = await executeHandoff(assertReady(prepareRouter({ obs: observation({ runId: '7004' }) })), service);
  assert.equal(result.disposition, 'duplicate');
  assert.equal(service.dispatches.length, 1);
  assertNoCompletion(result);
});

test('malformed or unreadable existing claims hold rather than being guessed duplicates', async () => {
  for (const corruption of ['malformed', 'bad-sha', 'read-error']) {
    const service = new MemoryService();
    await executeHandoff(assertReady(prepareRouter()), service);
    const path = [...service.records.keys()].find(key => key.endsWith('/claim.json'));
    if (corruption === 'malformed') {
      const record = { unrelated: true };
      service.records.set(path, { record, blobSha: gitBlobSha(recordBytes(record)) });
    } else if (corruption === 'bad-sha') service.records.get(path).blobSha = '0'.repeat(40);
    else service.readRecord = async () => { throw new Error('fixture: ledger unreadable'); };
    const result = await executeHandoff(assertReady(prepareRouter()), service);
    assert.equal(result.disposition, 'hold', corruption);
    assert.equal(service.dispatches.length, 1);
  }
});

test('only 204 is acceptance; rejected and uncertain requests are not retried', async () => {
  for (const [reply, disposition, status] of [
    [{ status: 200 }, 'transport_rejected', 'rejected'],
    [{ status: 202 }, 'transport_rejected', 'rejected'],
    [{ status: 403 }, 'transport_rejected', 'rejected'],
    [{ status: 503 }, 'transport_rejected', 'rejected'],
    [new Error('fixture: post response lost'), 'transport_uncertain', 'uncertain']
  ]) {
    const service = new MemoryService({ dispatchReply: reply });
    const first = await executeHandoff(assertReady(prepareRouter()), service);
    assert.equal(first.disposition, disposition);
    assert.equal(first.transport.status, status);
    assertNoCompletion(first);
    const repeat = await executeHandoff(assertReady(prepareRouter()), service);
    assert.equal(repeat.disposition, 'duplicate');
    assert.equal(service.dispatches.length, 1);
  }
});

test('accepted transport remains accepted when its outcome cannot be persisted', async () => {
  for (const outcomeReply of [{ status: 409, blobSha: null }, { status: 201, blobSha: '0'.repeat(40) }, new Error('fixture: storage failed')]) {
    const service = new MemoryService({ outcomeReply });
    const result = await executeHandoff(assertReady(prepareRouter()), service);
    assert.equal(result.disposition, 'transport_accepted');
    assert.equal(result.transport.status, 'accepted');
    assert.equal(service.dispatches.length, 1);
    assertNoCompletion(result);
    assert.equal(result.persistence.outcome.status, 'failed');
    assert.ok(result.issues.some(issue => issue.code === 'outcome_persistence_failed'));
  }
});

test('valid Router claim authorizes Dispatcher with the complete normalized event', async () => {
  const service = new MemoryService();
  const router = assertReady(prepareRouter());
  await executeHandoff(router, service);
  const dispatcher = assertReady(prepareDispatcher(router));
  const result = await executeHandoff(dispatcher, service);
  assert.equal(result.disposition, 'transport_accepted');
  assert.equal(service.dispatches.length, 2);
  const downstream = service.dispatches[1].request;
  assert.equal(downstream.repository, 'sovereign-codex/AVOT-engine');
  assert.equal(downstream.body.event_type, 'avot_execution');
  assert.deepEqual(downstream.body.client_payload.event, router.request.body.client_payload.event);
  assert.equal(downstream.body.client_payload.request_id, 'caller-request-001');
  assertNoCompletion(result);
});

test('Dispatcher requires a persisted Router claim, not just plausible metadata', async () => {
  const router = assertReady(prepareRouter());
  const dispatcher = assertReady(prepareDispatcher(router));
  const service = new MemoryService();
  const result = await executeHandoff(dispatcher, service);
  assert.equal(result.disposition, 'hold');
  assert.equal(service.dispatches.length, 0);
  assert.equal(service.calls.filter(call => call.kind === 'createRecord').length, 0);
});

test('Dispatcher holds altered event, metadata, or caller identity before any downstream attempt', async () => {
  const router = assertReady(prepareRouter());
  for (const mutate of [
    payload => { payload.event.payload.content = 'altered after Router'; },
    payload => { payload.request_id = 'another-caller-id'; },
    payload => { payload._ccc_handoff = {}; },
    payload => { payload._ccc_handoff.unreviewed_extra = true; },
    payload => { delete payload._ccc_handoff; }
  ]) {
    const service = new MemoryService(); await executeHandoff(router, service);
    const payload = clone(router.request.body.client_payload); mutate(payload);
    const dispatcher = prepareDispatcher(router, { payload });
    const result = await executeHandoff(dispatcher, service);
    assert.equal(result.disposition, 'hold');
    assert.equal(service.dispatches.length, 1);
  }
});

test('Dispatcher verifies Router claim content and blob integrity before creating its own claim', async () => {
  for (const corruption of ['request', 'blob']) {
    const service = new MemoryService();
    const router = assertReady(prepareRouter()); await executeHandoff(router, service);
    const path = [...service.records.keys()].find(key => key.includes('/router/') && key.endsWith('/claim.json'));
    const stored = service.records.get(path);
    if (corruption === 'blob') stored.blobSha = '0'.repeat(40);
    else {
      stored.record = { ...stored.record, binding: { fingerprint: '0'.repeat(64) } };
      stored.blobSha = gitBlobSha(recordBytes(stored.record));
    }
    const result = await executeHandoff(assertReady(prepareDispatcher(router)), service);
    assert.equal(result.disposition, 'hold');
    assert.equal(service.dispatches.length, 1);
    assert.equal([...service.records.keys()].filter(key => key.includes('/dispatcher/')).length, 0);
  }
});

test('Dispatcher can verify a valid Router claim before the Router outcome is recorded', async () => {
  const service = new MemoryService({ outcomeReply: new Error('fixture: Router outcome not recorded yet') });
  const router = assertReady(prepareRouter()); await executeHandoff(router, service);
  service.outcomeReply = undefined;
  const result = await executeHandoff(assertReady(prepareDispatcher(router)), service);
  assert.equal(result.disposition, 'transport_accepted');
  assert.equal(service.dispatches.length, 2);
  assertNoCompletion(result);
});

test('Dispatcher duplicate binding excludes the Dispatcher delivery run and attempt', async () => {
  const service = new MemoryService();
  const router = assertReady(prepareRouter()); await executeHandoff(router, service);
  const first = assertReady(prepareDispatcher(router)); await executeHandoff(first, service);
  const second = assertReady(prepareDispatcher(router, { obs: observation({ runId: '8002', runAttempt: '2', observedAt: '2026-10-18T07:00:00.000Z' }) }));
  assert.equal(first.identity.key, second.identity.key);
  assert.equal(first.binding.fingerprint, second.binding.fingerprint);
  const result = await executeHandoff(second, service);
  assert.equal(result.disposition, 'duplicate');
  assert.equal(service.dispatches.length, 2);
});

test('execution rejects fabricated or cloned ready records and preparation cannot be mutated', async () => {
  const prepared = assertReady(prepareRouter());
  assert.equal(Object.isFrozen(prepared), true);
  assert.equal(Object.isFrozen(prepared.request.body.client_payload.event), true);
  assert.throws(() => { prepared.request.repository = 'org/attacker'; }, TypeError);
  assert.throws(() => { prepared.request.body.client_payload.event.payload.content = 'changed'; }, TypeError);
  for (const forged of [clone(prepared), { disposition: 'ready' }, null]) {
    const service = new MemoryService();
    const result = await executeHandoff(forged, service);
    assert.equal(result.disposition, 'hold');
    assert.deepEqual(service.calls, []);
    assertNoCompletion(result);
  }
});

test('plausible Router observation edits cannot bypass the exact persisted request hash', async () => {
  const router = assertReady(prepareRouter());
  const service = new MemoryService(); await executeHandoff(router, service);
  const payload = clone(router.request.body.client_payload);
  payload._ccc_handoff.router_observation.run_id = '9999';
  payload._ccc_handoff.router_observation.actions_run_url = 'https://github.com/sovereign-codex/Codex-control-center/actions/runs/9999';
  const dispatcher = assertReady(prepareDispatcher(router, { payload }));
  const result = await executeHandoff(dispatcher, service);
  assert.equal(result.disposition, 'hold');
  assert.ok(result.issues.some(issue => issue.code === 'router_claim_unverified'));
  assert.equal(service.dispatches.length, 1);
  assert.equal([...service.records.keys()].filter(key => key.includes('/dispatcher/')).length, 0);
});

test('a duplicate rejects forged prior outcomes without inventing completion or reattempting', async () => {
  for (const mutate of [
    record => { record.execution = { status: 'completed', completion_claim: true }; },
    record => { record.claimant.run_id = '9999'; },
    record => { record.claim_blob_sha = '0'.repeat(40); },
    record => { record.transport = { status: 'accepted', http_status: 202 }; }
  ]) {
    const service = new MemoryService(); await executeHandoff(assertReady(prepareRouter()), service);
    const path = [...service.records.keys()].find(key => key.endsWith('/outcome.json'));
    const stored = service.records.get(path); mutate(stored.record);
    stored.blobSha = gitBlobSha(recordBytes(stored.record));
    const result = await executeHandoff(assertReady(prepareRouter()), service);
    assert.equal(result.disposition, 'duplicate');
    assert.equal(result.prior_outcome.status, 'unverified');
    assert.equal(result.prior_outcome.outcome, null);
    assert.equal(service.dispatches.length, 1);
    assertNoCompletion(result);
  }
});
