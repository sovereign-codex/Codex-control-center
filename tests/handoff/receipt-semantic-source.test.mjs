import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

test('browser semantic source and generated ESM stay byte-aligned', () => {
  const raw = readFileSync(new URL('../../scripts/handoff/receipt-semantics.js', import.meta.url), 'utf8');
  const esm = readFileSync(new URL('../../scripts/handoff/receipt-semantics.mjs', import.meta.url), 'utf8');
  assert.equal(esm, raw + '\nexport {TymeReceiptSemantics};\n');
});
