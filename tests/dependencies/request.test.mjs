import test from 'node:test';
import assert from 'node:assert/strict';
import { CARRIER, NEEDS, prepareDependencyRequest, assessDependencyReturn } from '../../scripts/dependencies/request.mjs';

const sourcePacket = () => ({
  packet_id: 'repo-cartographer-daily-topology-review-20261017-0715',
  lineage_id: 'daily-staging-review-2026-10-17',
  agent_name: 'Repo Cartographer',
  execution_state: 'skipped',
  handoff_ready: false,
  evidence_ref: 'https://app.notion.com/p/3fcc51d54b7581afb7e0da05ee93f78a'
});
const providerClaim = prepared => ({
  request_id: prepared.request.request_id,
  lineage_id: prepared.request.expected_lineage_id,
  artifact_kind: prepared.request.expected_artifact_kind,
  artifact_ref: 'https://app.notion.com/p/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
  parent_ref: prepared.request.expected_parent_ref,
  producer_role: 'Institutional Intake Bridge',
  producer_packet_id: 'fixture-notion-bridge-20261017',
  actual_executed_at: '2026-10-17T14:12:00Z',
  evidence_refs: ['https://app.notion.com/p/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb']
});
const separateReadback = claim => ({
  request_id: claim.request_id,
  lineage_id: claim.lineage_id,
  artifact_kind: claim.artifact_kind,
  artifact_ref: claim.artifact_ref,
  parent_ref: claim.parent_ref,
  producer_packet_id: claim.producer_packet_id,
  observed_at: '2026-10-17T15:00:00Z',
  observation_ref: 'https://app.notion.com/p/cccccccccccccccccccccccccccccccc'
});

test('October 17 missing source yields two distinct non-dispatching requests', () => {
  const a = prepareDependencyRequest({ source_packet: sourcePacket(), need: 'daily_staging_review' });
  const b = prepareDependencyRequest({ source_packet: sourcePacket(), need: 'notion_bridge_packet' });
  for (const result of [a, b]) {
    assert.equal(result.disposition, 'proposal_only');
    assert.equal(result.request.requested_owner_role, 'Institutional Intake Bridge');
    assert.equal(result.request.legacy_tracker_agent, 'Notion Bridge');
    assert.equal(result.request.scheduler_state, 'unverified');
    assert.equal(result.request.owner_instructions_version, 'v4');
    assert.match(result.request.requested_action, /do not backdate/);
    assert.equal(result.request.expected_lineage_id, 'daily-staging-review-2026-10-17');
    assert.deepEqual(result.effect, { dispatch_sent: false, persistence_attempted: false, authority_changed: false, resume_authorized: false });
    assert.equal(result.request.downstream_trigger_authorized, false);
  }
  assert.equal(Object.keys(NEEDS).length, 2);
  assert.notEqual(a.request.request_id, b.request.request_id);
});

test('v4 resolves renamed owner and two approved destinations without treating tracker alias as authority', () => {
  const review = prepareDependencyRequest({ source_packet: sourcePacket(), need: 'daily_staging_review' });
  const packet = prepareDependencyRequest({ source_packet: sourcePacket(), need: 'notion_bridge_packet' });
  assert.equal(review.request.expected_parent_ref, CARRIER.review_parent);
  assert.equal(packet.request.expected_parent_ref, CARRIER.runtime_tracker);
  assert.equal(review.request.legacy_tracker_agent, 'Notion Bridge');
  assert.equal(review.request.requested_owner_role, 'Institutional Intake Bridge');
  assert.equal(review.request.current_objective_and_source_set, 'must_be_separately_authorized_for_any_new_staging');
});

test('v4 blocked report does not create work, imply missing-source proof, or allow resume', () => {
  const p = prepareDependencyRequest({ source_packet: sourcePacket(), need: 'daily_staging_review' });
  for (const blocker of ['historical_evidence_not_found', 'current_objective_unavailable', 'authorized_sources_unavailable', 'source_access_unavailable', 'schedule_state_unverified']) {
    const disposition = assessDependencyReturn(p, { outcome: 'blocked', request_id: p.request.request_id, lineage_id: p.request.expected_lineage_id, producer_role: CARRIER.role, blocker });
    assert.equal(disposition.disposition, 'provider_blocked_unattested');
    assert.equal(disposition.effect.resume_authorized, false);
    assert.equal(disposition.effect.persistence_attempted, false);
    assert.equal(disposition.effect.dispatch_sent, false);
  }
  for (const bad of [
    { outcome: 'blocked', request_id: p.request.request_id, lineage_id: p.request.expected_lineage_id, producer_role: 'Notion Bridge', blocker: 'historical_evidence_not_found' },
    { outcome: 'blocked', request_id: p.request.request_id, lineage_id: p.request.expected_lineage_id, producer_role: CARRIER.role, blocker: 'success' },
    { outcome: 'blocked', request_id: p.request.request_id, lineage_id: p.request.expected_lineage_id, producer_role: CARRIER.role, blocker: 'historical_evidence_not_found', artifact_ref: 'https://app.notion.com/p/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' }
  ]) assert.equal(assessDependencyReturn(p, bad).disposition, 'hold');
});

test('replays are deterministic and do not create an execution receipt', () => {
  const a = prepareDependencyRequest({ source_packet: sourcePacket(), need: 'daily_staging_review' });
  const b = prepareDependencyRequest({ source_packet: sourcePacket(), need: 'daily_staging_review' });
  assert.equal(a.request.request_id, b.request.request_id);
  assert.equal(a.effect.persistence_attempted, false);
  assert.equal(b.effect.dispatch_sent, false);
});

test('Notion database Execution State Done cannot substitute for runtime_packet skipped', () => {
  for (const state of ['Done', 'completed', 'blocked', undefined]) {
    const result = prepareDependencyRequest({ source_packet: { ...sourcePacket(), execution_state: state }, need: 'daily_staging_review' });
    assert.equal(result.disposition, 'hold');
    assert.ok(result.issues.includes('not_an_observed_cartographer_skip'));
  }
});

test('quoted false in the original Notion runtime packet is accepted without truthy coercion', () => {
  assert.equal(prepareDependencyRequest({ source_packet: { ...sourcePacket(), handoff_ready: 'false' }, need: 'daily_staging_review' }).disposition, 'proposal_only');
  for (const value of ['true', true, 'False', '0', null]) {
    assert.equal(prepareDependencyRequest({ source_packet: { ...sourcePacket(), handoff_ready: value }, need: 'daily_staging_review' }).disposition, 'hold');
  }
});

test('only an explicit skipped Cartographer packet with source reference qualifies', () => {
  const mutations = [
    p => { p.agent_name = 'Promotion Reviewer'; },
    p => { p.handoff_ready = true; },
    p => { p.evidence_ref = ''; },
    p => { p.packet_id = '../unsafe'; },
    p => { p.lineage_id = 'daily-staging-review-2026-02-30'; }
  ];
  for (const mutate of mutations) {
    const packet = sourcePacket(); mutate(packet);
    assert.equal(prepareDependencyRequest({ source_packet: packet, need: 'daily_staging_review' }).disposition, 'hold');
  }
  assert.equal(prepareDependencyRequest({ source_packet: sourcePacket(), need: 'unregistered_provider' }).disposition, 'hold');
});

test('a missing provider response remains waiting, not completed', () => {
  const p = prepareDependencyRequest({ source_packet: sourcePacket(), need: 'notion_bridge_packet' });
  assert.equal(assessDependencyReturn(p).disposition, 'awaiting_provider_return');
  assert.equal(assessDependencyReturn(p).effect.resume_authorized, false);
});

test('a structurally complete provider claim still needs independent source readback', () => {
  const p = prepareDependencyRequest({ source_packet: sourcePacket(), need: 'daily_staging_review' });
  const claim = providerClaim(p);
  assert.equal(assessDependencyReturn(p, claim).disposition, 'needs_independent_readback');
  const b = assessDependencyReturn(p, claim, separateReadback(claim));
  assert.equal(b.disposition, 'structurally_consistent_unattested');
  assert.equal(b.effect.resume_authorized, false);
  assert.equal(b.effect.authority_changed, false);
});

test('old or mismatched lineage, wrong producer, and forged request identity hold', () => {
  const p = prepareDependencyRequest({ source_packet: sourcePacket(), need: 'daily_staging_review' });
  for (const mutate of [
    c => { c.lineage_id = 'daily-staging-review-2026-10-09'; },
    c => { c.producer_role = 'AVOT Fabricator'; },
    c => { c.request_id = 'fake-request'; },
    c => { c.artifact_kind = 'completion_receipt'; },
    c => { c.parent_ref = 'https://app.notion.com/p/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'; },
    c => { c.producer_role = 'Notion Bridge'; },
    c => { c.actual_executed_at = '2026-10-09T14:12:00Z'; },
    c => { c.actual_executed_at = '2026-02-30T14:12:00Z'; },
    c => { c.evidence_refs = []; }
  ]) {
    const claim = providerClaim(p); mutate(claim);
    assert.equal(assessDependencyReturn(p, claim).disposition, 'hold');
  }
});

test('readback cannot be the artifact itself or have a different lineage/identity', () => {
  const p = prepareDependencyRequest({ source_packet: sourcePacket(), need: 'daily_staging_review' });
  const claim = providerClaim(p);
  for (const mutate of [
    r => { r.observation_ref = claim.artifact_ref; },
    r => { r.lineage_id = 'daily-staging-review-2026-10-09'; },
    r => { r.request_id = 'not-this-request'; },
    r => { r.producer_packet_id = 'wrong'; },
    r => { r.parent_ref = 'https://app.notion.com/p/dddddddddddddddddddddddddddddddd'; }
  ]) {
    const readback = separateReadback(claim); mutate(readback);
    assert.equal(assessDependencyReturn(p, claim, readback).disposition, 'hold');
  }
});

test('invented preparation input cannot request or approve resumption', () => {
  const fake = { disposition: 'proposal_only', request: { request_id: 'x' } };
  assert.equal(assessDependencyReturn(fake, {}).disposition, 'hold');
});
