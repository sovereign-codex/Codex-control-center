import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { createGithubService } from '../../scripts/handoff/github-service.mjs';
import { CONTROL_CENTER, recordBytes, gitBlobSha } from '../../scripts/handoff/contract.mjs';

const path = 'handoff-ledger/v1/router/' + 'a'.repeat(64) + '/claim.json';
const ledgerToken = 'fixture-ledger-token';
const dispatchToken = 'fixture-dispatch-token';
const record = { purpose: 'test-only', sequence: 1, nested: { intact: true } };
const bytes = recordBytes(record);
const sha = gitBlobSha(bytes);
const jsonResponse = (status, data) => new Response(data === null ? null : JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });

function harness(reply) {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url: String(url), init });
    if (reply instanceof Error) throw reply;
    return typeof reply === 'function' ? reply(calls.length, url, init) : reply;
  };
  return { calls, service: createGithubService({ ledgerToken, dispatchToken, fetchImpl }) };
}

function assertSingleFixedRequest(calls, method) {
  assert.equal(calls.length, 1);
  assert.equal(calls[0].init.method, method);
  assert.equal(calls[0].init.redirect, 'error');
  assert.ok(calls[0].init.signal instanceof AbortSignal);
  const url = new URL(calls[0].url);
  assert.equal(url.origin, 'https://api.github.com');
  assert.equal(url.username, '');
  assert.equal(url.password, '');
  assert.equal(calls[0].url.includes(ledgerToken), false);
  assert.equal(calls[0].url.includes(dispatchToken), false);
}

test('GitHub claim creation is one fixed Contents PUT with canonical bytes and no update SHA', async () => {
  const { service, calls } = harness(jsonResponse(201, { content: { sha }, commit: { sha: 'b'.repeat(40) } }));
  const result = await service.createRecord(path, record);
  assert.equal(result.status, 201);
  assert.equal(result.blobSha, sha);
  assert.equal(result.commitSha, 'b'.repeat(40));
  assertSingleFixedRequest(calls, 'PUT');
  assert.equal(new URL(calls[0].url).pathname, '/repos/' + CONTROL_CENTER + '/contents/' + path);
  const body = JSON.parse(calls[0].init.body);
  assert.equal(body.branch, 'main');
  assert.equal(Object.hasOwn(body, 'sha'), false);
  assert.deepEqual(Buffer.from(body.content, 'base64'), bytes);
  assert.equal(new Headers(calls[0].init.headers).get('Authorization'), 'Bearer ' + ledgerToken);
  const independentlyHashed = createHash('sha1').update('blob ' + bytes.length + '\0').update(bytes).digest('hex');
  assert.equal(result.blobSha, independentlyHashed);
});

test('GitHub non-created claim statuses are returned without retries or interpreting error bodies', async () => {
  for (const status of [200, 401, 403, 404, 409, 422, 500]) {
    const { service, calls } = harness(new Response('deliberately not JSON', { status }));
    const result = await service.createRecord(path, record);
    assert.deepEqual(result, { status, blobSha: null });
    assertSingleFixedRequest(calls, 'PUT');
  }
});

test('GitHub creation rejects an incorrect or malformed 201 blob identity', async () => {
  for (const data of [{ content: { sha: '0'.repeat(40) } }, { content: {} }, {}, null]) {
    const { service, calls } = harness(jsonResponse(201, data));
    await assert.rejects(() => service.createRecord(path, record));
    assertSingleFixedRequest(calls, 'PUT');
  }
});

test('GitHub record read verifies exact decoded bytes and canonical record serialization', async () => {
  const content = bytes.toString('base64').match(/.{1,40}/g).join('\n') + '\n';
  const { service, calls } = harness(jsonResponse(200, { type: 'file', path, encoding: 'base64', content, sha }));
  const result = await service.readRecord(path);
  assert.deepEqual(result, { status: 200, blobSha: sha, record });
  assertSingleFixedRequest(calls, 'GET');
  assert.equal(new URL(calls[0].url).searchParams.get('ref'), 'main');
  assert.equal(new Headers(calls[0].init.headers).get('Authorization'), 'Bearer ' + ledgerToken);
});

test('GitHub missing record is ordinary missing without guessed content', async () => {
  const { service, calls } = harness(new Response('not parsed as a record', { status: 404 }));
  const result = await service.readRecord(path);
  assert.equal(result.status, 404);
  assert.equal(result.record ?? null, null);
  assert.equal(result.blobSha ?? null, null);
  assertSingleFixedRequest(calls, 'GET');
});

test('GitHub record read rejects wrong blob SHA, malformed base64, noncanonical bytes, and duplicate keys', async () => {
  const noncanonical = Buffer.from(JSON.stringify(record, null, 2) + '\n');
  const duplicates = Buffer.from('{"key":"first","key":"second"}\n');
  const invalidUtf8 = Buffer.from([0xff, 0xfe]);
  for (const data of [
    { type: 'file', encoding: 'base64', content: bytes.toString('base64'), sha: '0'.repeat(40) },
    { type: 'file', encoding: 'base64', content: '!invalid!', sha },
    { type: 'file', encoding: 'base64', content: noncanonical.toString('base64'), sha: gitBlobSha(noncanonical) },
    { type: 'file', encoding: 'base64', content: duplicates.toString('base64'), sha: gitBlobSha(duplicates) },
    { type: 'file', encoding: 'base64', content: invalidUtf8.toString('base64'), sha: gitBlobSha(invalidUtf8) },
    { type: 'file', encoding: 'utf-8', content: bytes.toString('utf8'), sha }
  ]) {
    const { service, calls } = harness(jsonResponse(200, { path, ...data }));
    await assert.rejects(() => service.readRecord(path));
    assertSingleFixedRequest(calls, 'GET');
  }
});

test('GitHub ledger paths cannot select arbitrary repository files or branch parameters', async () => {
  for (const invalid of [
    '../config/control-center-handoff.json',
    path.replace('/router/', '/unreviewed/'),
    path.replace('a'.repeat(64), 'A'.repeat(64)),
    path + '?ref=attacker',
    path.replace('/claim.json', '/other.json'),
    'https://example.invalid/' + path
  ]) {
    const { service, calls } = harness(jsonResponse(200, {}));
    await assert.rejects(() => service.createRecord(invalid, record));
    await assert.rejects(() => service.readRecord(invalid));
    assert.deepEqual(calls, []);
  }
});

test('GitHub dispatch preserves complete body and uses only the dispatch credential', async () => {
  for (const [repository, eventType] of [[CONTROL_CENTER, 'engine_handoff'], ['sovereign-codex/AVOT-engine', 'avot_execution']]) {
    const request = { repository, body: { event_type: eventType, client_payload: { payload: { text: 'all fields intact' }, nested: [1, true] } } };
    const { service, calls } = harness(jsonResponse(204, null));
    assert.deepEqual(await service.dispatch(request), { status: 204 });
    assertSingleFixedRequest(calls, 'POST');
    assert.equal(new URL(calls[0].url).pathname, '/repos/' + repository + '/dispatches');
    assert.deepEqual(JSON.parse(calls[0].init.body), request.body);
    assert.equal(new Headers(calls[0].init.headers).get('Authorization'), 'Bearer ' + dispatchToken);
    assert.equal(JSON.stringify(request).includes(dispatchToken), false);
  }
});

test('GitHub dispatch rejects unreviewed repository and event pairs before fetch', async () => {
  for (const [repository, eventType] of [
    [CONTROL_CENTER, 'avot_execution'], ['sovereign-codex/AVOT-engine', 'engine_handoff'],
    ['sovereign-codex/Tyme-Lab', 'avot_execution'], ['https://example.invalid/path', 'engine_handoff'],
    ['sovereign-codex/AVOT-engine', 'workflow_dispatch']
  ]) {
    const { service, calls } = harness(jsonResponse(204, null));
    await assert.rejects(() => service.dispatch({ repository, body: { event_type: eventType, client_payload: {} } }));
    assert.deepEqual(calls, []);
  }
});

test('GitHub HTTP rejection and network failure do not cause automatic retries', async () => {
  const request = { repository: CONTROL_CENTER, body: { event_type: 'engine_handoff', client_payload: {} } };
  const rejected = harness(jsonResponse(503, { message: 'temporary failure' }));
  assert.deepEqual(await rejected.service.dispatch(request), { status: 503 });
  assertSingleFixedRequest(rejected.calls, 'POST');
  const uncertain = harness(new Error('fixture secret: ' + dispatchToken + ' ' + ledgerToken));
  await assert.rejects(() => uncertain.service.dispatch(request), error => {
    assert.equal(error.message.includes(dispatchToken), false);
    assert.equal(error.message.includes(ledgerToken), false);
    assert.equal(JSON.stringify(error).includes(dispatchToken), false);
    return true;
  });
  assertSingleFixedRequest(uncertain.calls, 'POST');
});

test('GitHub ledger fetch failures cannot leak credentials through returned errors', async () => {
  for (const operation of ['createRecord', 'readRecord']) {
    const { service, calls } = harness(new Error('raw fetch error contains ' + ledgerToken));
    await assert.rejects(() => operation === 'createRecord' ? service.createRecord(path, record) : service.readRecord(path), error => {
      assert.equal(String(error).includes(ledgerToken), false);
      assert.equal(String(error.cause).includes(ledgerToken), false);
      return true;
    });
    assert.equal(calls.length, 1);
  }
});
