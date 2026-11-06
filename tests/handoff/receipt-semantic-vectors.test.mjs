import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateReceipt} from '../../scripts/handoff/roundtrip-receipt.mjs';
const fixtures=JSON.parse(readFileSync(new URL('../fixtures/receipt-semantic-vectors.json',import.meta.url),'utf8'));
for(const f of fixtures)test('shared semantic vector: '+f.name,()=>assert.equal(validateReceipt(f.receipt).valid,f.expected_valid));
