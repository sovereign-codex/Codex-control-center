/** Fixed GitHub I/O boundary. No retry, overwrite, redirect, or error-body logging. */
import { CONTROL_CENTER, ENGINE_REPO, canonical, recordBytes, gitBlobSha } from './contract.mjs';
import { strictJson } from './normalization.mjs';

const API = 'https://api.github.com';
const LEDGER_PATH = /^handoff-ledger\/v1\/(router|dispatcher)\/[a-f0-9]{64}\/(claim|outcome)\.json$/;
const BLOB_SHA = /^[a-f0-9]{40}$/;
const TIMEOUT_MS = 15_000;
const MAX_RECORD_BYTES = 1_000_000;
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const fail = message => { throw new Error(message); };

function tokenValid(token) {
  return typeof token === 'string' && /^[\x21-\x7e]{1,8192}$/.test(token);
}

function ledgerUrl(path) {
  if (typeof path !== 'string' || !LEDGER_PATH.test(path)) fail('Invalid handoff ledger path.');
  return `${API}/repos/${CONTROL_CENTER}/contents/${path}`;
}

function strictUtf8(bytes) {
  return new TextDecoder('utf-8', { fatal: true }).decode(bytes);
}

function decodeBase64(content) {
  if (typeof content !== 'string') fail('Invalid ledger content encoding.');
  // GitHub wraps base64 with line feeds. All other non-base64 bytes are rejected.
  const compact = content.replace(/\r?\n/g, '');
  if (!/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(compact)) {
    fail('Invalid ledger content encoding.');
  }
  const bytes = Buffer.from(compact, 'base64');
  if (bytes.length > MAX_RECORD_BYTES || bytes.toString('base64') !== compact) {
    fail('Invalid ledger content encoding.');
  }
  return bytes;
}

export function createGithubService({ ledgerToken, dispatchToken, fetchImpl = globalThis.fetch } = {}) {
  if (!tokenValid(ledgerToken) || !tokenValid(dispatchToken) || typeof fetchImpl !== 'function') {
    fail('GitHub handoff credentials or transport are unavailable.');
  }

  async function call(url, method, token, body, inspect) {
    const controller = new AbortController();
    let timer;
    const deadline = new Promise((_, reject) => {
      timer = setTimeout(() => {
        controller.abort();
        reject(new Error('GitHub request deadline exceeded.'));
      }, TIMEOUT_MS);
    });
    try {
      const operation = (async () => {
        const response = await fetchImpl(url, {
          method,
          headers: {
            Accept: 'application/vnd.github+json',
            Authorization: `Bearer ${token}`,
            'X-GitHub-Api-Version': '2026-03-10',
            'Content-Type': 'application/json',
            'User-Agent': 'control-center-handoff/1'
          },
          ...(body === undefined ? {} : { body }),
          redirect: 'error',
          signal: controller.signal
        });
        if (!response || !Number.isInteger(response.status) || response.status < 100 || response.status > 599 ||
            response.redirected || (response.status >= 300 && response.status < 400)) {
          fail('Invalid or redirected GitHub response.');
        }
        try {
          return await inspect(response);
        } finally {
          if (response.body && !response.bodyUsed) await response.body.cancel();
        }
      })();
      return await Promise.race([operation, deadline]);
    } catch {
      // Fetch/parse errors can contain headers, request bodies, or response text.
      // Never retain the original message, stack, or cause across this boundary.
      fail('GitHub handoff request could not be verified.');
    } finally {
      clearTimeout(timer);
    }
  }

  async function json(response) {
    if (!response.body) fail('GitHub returned no record content.');
    const reader = response.body.getReader();
    const chunks = [];
    let length = 0;
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        length += value.byteLength;
        if (length > 2_000_000) {
          await reader.cancel();
          fail('GitHub response exceeded the record limit.');
        }
        chunks.push(value);
      }
    } finally {
      reader.releaseLock();
    }
    const bytes = Buffer.concat(chunks, length);
    return strictJson(strictUtf8(bytes));
  }

  return Object.freeze({
    async createRecord(path, record) {
      const url = ledgerUrl(path);
      let bytes;
      try {
        bytes = Buffer.from(recordBytes(record));
        if (!object(record) || bytes.length > MAX_RECORD_BYTES) fail('Invalid handoff record.');
        strictJson(strictUtf8(bytes));
      } catch {
        fail('Invalid handoff record.');
      }
      const expectedSha = gitBlobSha(bytes);
      const body = JSON.stringify({
        message: 'Record Control Center handoff evidence',
        branch: 'main',
        content: bytes.toString('base64')
        // Deliberately omit sha: this operation may create, never replace.
      });
      return call(url, 'PUT', ledgerToken, body, async response => {
        if (response.status !== 201) return { status: response.status, blobSha: null };
        const result = await json(response);
        if (!BLOB_SHA.test(result?.content?.sha ?? '') || result.content.sha !== expectedSha) {
          fail('Unverifiable ledger creation response.');
        }
        return {
          status: 201,
          blobSha: expectedSha,
          ...(BLOB_SHA.test(result?.commit?.sha ?? '') ? { commitSha: result.commit.sha } : {})
        };
      });
    },

    async readRecord(path) {
      const url = `${ledgerUrl(path)}?ref=main`;
      return call(url, 'GET', ledgerToken, undefined, async response => {
        if (response.status !== 200) return { status: response.status, blobSha: null, record: null };
        const result = await json(response);
        if (result?.type !== 'file' || result.encoding !== 'base64' || result.path !== path ||
            !BLOB_SHA.test(result.sha ?? '')) fail('Unverifiable ledger read response.');
        const bytes = decodeBase64(result.content);
        if (gitBlobSha(bytes) !== result.sha) fail('Ledger blob identity mismatch.');
        const record = strictJson(strictUtf8(bytes));
        if (!object(record) || !Buffer.from(recordBytes(record)).equals(bytes)) {
          fail('Ledger record is not canonical.');
        }
        return { status: 200, blobSha: result.sha, record };
      });
    },

    async dispatch(request) {
      const repository = request?.repository;
      const body = request?.body;
      const internal = repository === CONTROL_CENTER && body?.event_type === 'engine_handoff';
      const engine = repository === ENGINE_REPO && body?.event_type === 'avot_execution';
      if ((!internal && !engine) || !object(body) || !object(body.client_payload) ||
          Object.keys(body).sort().join(',') !== 'client_payload,event_type' ||
          Object.keys(body.client_payload).length > 10) fail('Dispatch route or payload is not allowed.');
      let serialized;
      try {
        serialized = canonical(body);
        strictJson(serialized);
        if (Buffer.byteLength(serialized, 'utf8') >= 65_536) fail('Dispatch payload exceeds its limit.');
      } catch {
        fail('Dispatch payload is not valid bounded JSON.');
      }
      const destination = internal ? CONTROL_CENTER : ENGINE_REPO;
      return call(`${API}/repos/${destination}/dispatches`, 'POST', dispatchToken, serialized,
        async response => ({ status: response.status }));
    }
  });
}
