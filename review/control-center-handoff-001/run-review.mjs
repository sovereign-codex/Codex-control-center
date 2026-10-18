/** Reproduce the local specimen and write machine-readable evidence. */
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, readdirSync, existsSync, mkdirSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { run } from 'node:test';
import { tap as tapReporter } from 'node:test/reporters';
import { runDemo } from './demo.mjs';

const root = dirname(fileURLToPath(import.meta.url));
const startedAt = new Date().toISOString();
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const writeJson = (name, value) => writeFileSync(join(root, 'evidence', name), `${JSON.stringify(value, null, 2)}\n`);
const walk = dir => readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
  if (['evidence', 'SHA256SUMS', '.git'].includes(entry.name)) return [];
  const path = join(dir, entry.name);
  return entry.isDirectory() ? walk(path) : entry.isFile() ? [path] : [];
});
const inputs = walk(root).sort().map(path => ({ path: relative(root, path), sha256: digest(readFileSync(path)), bytes: readFileSync(path).length }));
const baseline = JSON.parse(readFileSync(join(root, 'BASELINE.json'), 'utf8'));
const sourceRoot = resolve(root, '..', '..');
const baselineFiles = baseline.source_files.map(source => {
  const path = join(sourceRoot, source.path);
  if (!existsSync(path)) return { path: source.path, status: 'not_available' };
  const sha256 = digest(readFileSync(path));
  const status = sha256 === source.local_snapshot_sha256 ? 'preserved_local_snapshot' : sha256 === source.source_sha256 ? 'exact_pinned_source' : 'mismatch';
  return { path: source.path, status, sha256 };
});
const baselineCheck = {
  expected_files: baselineFiles.length,
  available_files: baselineFiles.filter(file => file.status !== 'not_available').length,
  mismatches: baselineFiles.filter(file => file.status === 'mismatch').length,
  preserved_local_snapshots: baselineFiles.filter(file => file.status === 'preserved_local_snapshot').length,
  note: 'Standalone archives contain candidate files, not repository source copies. Unavailable sources are not claimed as verified.',
  files: baselineFiles
};
const tests = readdirSync(join(root, 'tests')).filter(name => name.endsWith('.test.mjs')).sort().map(name => `tests/${name}`);
if (tests.length === 0) throw new Error('No local test files found.');
const args = ['--test', '--test-isolation=none', '--test-reporter=tap', ...tests];
let tap = '';
let runnerError = null;
try {
  const stream = run({ cwd: root, files: tests.map(name => join(root, name)), isolation: 'none' });
  for await (const chunk of stream.compose(tapReporter)) tap += String(chunk);
} catch (error) {
  runnerError = error.message;
}
const count = key => Number(new RegExp(`^# ${key} (\\d+)$`, 'm').exec(tap)?.[1] ?? NaN);
const counts = Object.fromEntries(['tests', 'pass', 'fail', 'cancelled', 'skipped', 'todo'].map(key => [key, count(key)]));
const names = [...tap.matchAll(/^ok \d+ - (.+)$/gm)].map(match => match[1]);
const requiredCategories = ['legacy_shapes', 'internal_event', 'conflicting_target', 'missing_provenance', 'failure_status', 'non_success', 'identity_collision', 'duplicate', 'transport_only', 'missing_receiver'];
const categories = Object.fromEntries(requiredCategories.map(category => [category, names.filter(name => name.startsWith(`[${category}]`)).length]));
const demo = runDemo();
const demoChecksPass = Object.values(demo.equality_checks).every(value => value === true);
const passed = runnerError === null && counts.tests > 0 && counts.pass === counts.tests && counts.fail === 0 && counts.cancelled === 0 && counts.skipped === 0 && counts.todo === 0 && Object.values(categories).every(n => n > 0) && names.length === counts.tests && baselineCheck.mismatches === 0 && demoChecksPass;
const report = {
  schema_version: '1.0',
  candidate_id: 'CONTROL-CENTER-HANDOFF-001',
  standing: 'noncanonical_local_test_evidence',
  started_at_utc: startedAt,
  completed_at_utc: new Date().toISOString(),
  baseline_commit: baseline.baseline_commit,
  node_version: process.version,
  command: ['node', 'run-review.mjs'],
  test_api: { module: 'node:test', method: 'run', isolation: 'none', files: tests },
  equivalent_test_cli: ['node', ...args],
  runner_exit_code: passed ? 0 : 1,
  result: passed ? 'passed' : 'failed',
  counts,
  acceptance_category_counts: categories,
  review_regression_tests: names.filter(name => /^R\d+:/.test(name)).length,
  passing_test_names: names,
  baseline_check: baselineCheck,
  inputs,
  demo_checks: demo.equality_checks,
  runner_error: runnerError,
  limitations: [
    'Tests exercise the isolated local candidate, not the unchanged GitHub workflows.',
    'All transport responses are built-in in-memory simulations; no live dispatch is performed.',
    'Producer identity is declared, not authenticated; credentials and App ID binding are unverified.',
    'Destination metadata does not establish a live AVOT-engine or Tyme-Lab receiver.',
    'The ledger is per harness instance, with no durable, cross-instance or remote exactly-once guarantee.',
    'No receiver run, returned artifact, institutional receipt or promotion is established.'
  ]
};
mkdirSync(join(root, 'evidence'), { recursive: true });
writeFileSync(join(root, 'evidence', 'tests.tap'), tap);
writeJson('demo-results.json', demo);
writeJson('test-results.json', report);
process.stdout.write(`${JSON.stringify({ result: report.result, counts, acceptance_categories: requiredCategories.length, review_regressions: report.review_regression_tests, baseline_available: baselineCheck.available_files, baseline_mismatches: baselineCheck.mismatches, evidence_directory: 'evidence' }, null, 2)}\n`);
if (!passed) process.exitCode = 1;
