// Run from repo root. Pure contract call: no run.mjs, credentials or network.
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
const modulePath = process.argv[2] || 'scripts/handoff/contract.mjs';
const { prepareHandoff } = await import(pathToFileURL(resolve(modulePath)));
const code = "import sys;sys.path.insert(0,'review/router-diagnostic-adapter-001');from adapter import template;sys.stdout.buffer.write(template({'diagnostic_id':'ccc-thread-diag-v1-offline01'}))";
const body = JSON.parse(execFileSync('python', ['-c', code], {encoding:'utf8'}));
const policy = JSON.parse(readFileSync(process.argv[3] || 'config/control-center-handoff.json','utf8'));
const result = prepareHandoff({stage:'router',policy,
  eventBytes:Buffer.from(JSON.stringify({action:body.event_type,client_payload:body.client_payload,
    repository:{full_name:'sovereign-codex/Codex-control-center'},sender:{id:123}})),
  observation:{eventName:'repository_dispatch',repository:'sovereign-codex/Codex-control-center',
    runId:'1',runAttempt:'1',observedAt:'2026-10-29T00:00:00Z'}});
const codes = result.issues.map(i=>i.code).sort();
const expected=['policy_disabled','receiver_unverified','sender_not_allowed'].sort();
if(result.disposition!=='hold'||result.request!==null||JSON.stringify(codes)!==JSON.stringify(expected)) {
  console.error(JSON.stringify(codes));
  throw new Error('Synthetic template did not produce only the expected disabled/admission holds');
}
console.log(JSON.stringify({kind:'offline_contract_check',disposition:result.disposition,issues:codes,
  live_dispatch:false,downstream_execution:'not_tested'},null,2));
