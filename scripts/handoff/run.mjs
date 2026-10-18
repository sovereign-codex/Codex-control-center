/** Actions entry point. Event data is read as bytes, never interpolated into shell. */
import { appendFile, mkdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { CONTRACT_VERSION, prepareHandoff, recordBytes } from './contract.mjs';
import { strictJson } from './normalization.mjs';
import { executeHandoff } from './executor.mjs';
import { createGithubService } from './github-service.mjs';

const root = fileURLToPath(new URL('../../', import.meta.url));
const [command, stage, ...extra] = process.argv.slice(2);
if (!['prepare', 'execute'].includes(command) || !['router', 'dispatcher'].includes(stage) || extra.length) {
  console.error('Usage: node scripts/handoff/run.mjs prepare|execute router|dispatcher');
  process.exitCode = 1;
} else {
  const stateDir = join(root, '.handoff-state', stage);
  const observation = {
    eventName: process.env.GITHUB_EVENT_NAME ?? '',
    repository: process.env.GITHUB_REPOSITORY ?? '',
    runId: process.env.GITHUB_RUN_ID ?? '',
    runAttempt: process.env.GITHUB_RUN_ATTEMPT ?? '',
    observedAt: new Date().toISOString()
  };
  let prepared;
  let result;
  let ready = false;
  let executionStarted = false;
  const report = async (name, value) => writeFile(join(stateDir, name), recordBytes(value), { mode: 0o600 });

  try {
    await mkdir(stateDir, { recursive: true, mode: 0o700 });
    await report(`${command}-observation.json`, observation);
    const eventPath = process.env.GITHUB_EVENT_PATH;
    if (typeof eventPath !== 'string' || !eventPath) throw new Error('Event path unavailable.');
    const eventBytes = await readFile(eventPath);
    await writeFile(join(stateDir, 'observation-event.json'), eventBytes, { mode: 0o600 });
    const policyBytes = await readFile(join(root, 'config', 'control-center-handoff.json'));
    const policy = strictJson(new TextDecoder('utf-8', { fatal: true }).decode(policyBytes));
    prepared = prepareHandoff({ stage, eventBytes, observation, policy });
    ready = prepared.disposition === 'ready';
    await report(`${command}-prepared.json`, prepared);
    result = prepared;

    if (command === 'execute' && ready) {
      // Read credentials only after a fresh evaluation of the event and policy.
      // The earlier prepare report is evidence, never authority to execute.
      const service = createGithubService({
        ledgerToken: process.env.GITHUB_TOKEN,
        dispatchToken: process.env.HANDOFF_DISPATCH_TOKEN
      });
      executionStarted = true;
      result = await executeHandoff(prepared, service);
    }
  } catch {
    result = {
      ...(prepared ?? {
        contract_version: CONTRACT_VERSION,
        stage,
        identity: null,
        binding: null,
        request: null,
        evidence: {},
        observation,
        execution: { status: 'unverified', completion_claim: false }
      }),
      disposition: executionStarted ? 'transport_uncertain' : 'hold',
      issues: [...(prepared?.issues ?? []), {
        code: executionStarted ? 'execution_unverified_error' : 'preparation_or_credentials_unavailable',
        message: executionStarted
          ? 'Execution stopped without a verifiable result; no automatic retry is allowed.'
          : 'The event, policy, local evidence, or required credentials could not be validated.'
      }],
      transport: { status: executionStarted ? 'uncertain' : 'not_attempted', http_status: null }
    };
    ready = false;
  }

  try {
    await report(`${command}-result.json`, result);
    if (process.env.GITHUB_OUTPUT) {
      // This is the only step output; no producer-controlled strings reach it.
      await appendFile(process.env.GITHUB_OUTPUT, `ready=${ready ? 'true' : 'false'}\n`);
    }
  } catch {
    console.error('Control Center handoff evidence could not be persisted.');
    process.exitCode = 1;
  }
  console.log(`Control Center handoff ${stage}: ${result.disposition}; execution unverified.`);
  const succeeded = command === 'prepare' ? ready
    : result.disposition === 'transport_accepted' && result.persistence?.outcome?.status === 'recorded';
  if (!succeeded) process.exitCode = 1;
}
