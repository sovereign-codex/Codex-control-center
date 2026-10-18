/** Pure, non-dispatching dependency request preparation for the October 17 handoff regression. */
import { createHash } from 'node:crypto';

export const CONTRACT_VERSION = 'tyme-dependency/1';
/** The current installed role is v4; the tracker keeps its legacy select option. */
export const CARRIER = Object.freeze({
  role: 'Institutional Intake Bridge',
  instructions_version: 'v4',
  legacy_tracker_agent: 'Notion Bridge',
  review_parent: 'https://app.notion.com/p/3f4c51d54b7581d5a977ed5a23e769ff',
  runtime_tracker: 'collection://74409f4d-3622-4ecc-82dc-2a52f9bde7e4'
});
export const NEEDS = Object.freeze({
  daily_staging_review: Object.freeze({ owner_role: CARRIER.role, artifact_kind: 'daily_staging_review', expected_parent: CARRIER.review_parent }),
  notion_bridge_packet: Object.freeze({ owner_role: CARRIER.role, artifact_kind: 'notion_bridge_packet', expected_parent: CARRIER.runtime_tracker })
});

const preparedRequests = new WeakSet();
const token = value => typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value);
const notionRef = value => typeof value === 'string' && /^https:\/\/app\.notion\.com\/p\/[a-fA-F0-9]{32}(?:\?pvs=[0-9]+)?$/.test(value);
const timestamp = value => {
  if (typeof value !== 'string' || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(value)) return false;
  const datePart = value.slice(0, 10);
  const localMidnight = new Date(datePart + 'T00:00:00.000Z');
  return Number.isFinite(Date.parse(value)) && Number.isFinite(localMidnight.getTime()) && localMidnight.toISOString().slice(0, 10) === datePart;
};
const arizonaDate = timestampValue => new Date(Date.parse(timestampValue) - 7 * 3600_000).toISOString().slice(0, 10);
const lineageValid = value => {
  if (typeof value !== 'string') return false;
  const match = /^daily-staging-review-(\d{4}-\d\d-\d\d)$/.exec(value);
  if (!match) return false;
  const date = new Date(match[1] + 'T00:00:00.000Z');
  return Number.isFinite(date.getTime()) && date.toISOString().startsWith(match[1]);
};
const sha256 = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const emptyEffect = () => ({ dispatch_sent: false, persistence_attempted: false, authority_changed: false, resume_authorized: false });

export function prepareDependencyRequest({ source_packet, need } = {}) {
  const result = { contract_version: CONTRACT_VERSION, disposition: 'hold', issues: [], request: null, effect: emptyEffect() };
  if (!Object.hasOwn(NEEDS, need)) result.issues.push('unregistered_dependency');
  if (!source_packet || typeof source_packet !== 'object' || Array.isArray(source_packet)) result.issues.push('missing_source_packet');
  else {
    if (!token(source_packet.packet_id)) result.issues.push('invalid_packet_id');
    if (!lineageValid(source_packet.lineage_id)) result.issues.push('invalid_cycle_lineage');
    if (source_packet.agent_name !== 'Repo Cartographer' || source_packet.execution_state !== 'skipped' || ![false, 'false'].includes(source_packet.handoff_ready)) {
      result.issues.push('not_an_observed_cartographer_skip');
    }
    if (!notionRef(source_packet.evidence_ref)) result.issues.push('missing_source_evidence_ref');
  }
  if (result.issues.length) return result;
  const requirement = NEEDS[need];
  const request_id = sha256([CONTRACT_VERSION, source_packet.lineage_id, source_packet.packet_id, need]);
  result.request = {
    request_id,
    request_type: 'DEPENDENCY_REQUEST',
    originating_packet_id: source_packet.packet_id,
    originating_evidence_ref: source_packet.evidence_ref,
    originating_execution_state: 'skipped',
    expected_lineage_id: source_packet.lineage_id,
    dependency_kind: need,
    requested_owner_role: requirement.owner_role,
    owner_instructions_version: CARRIER.instructions_version,
    legacy_tracker_agent: CARRIER.legacy_tracker_agent,
    expected_artifact_kind: requirement.artifact_kind,
    expected_parent_ref: requirement.expected_parent,
    mode: 'assisted_manual',
    scheduler_state: 'unverified',
    current_objective_and_source_set: 'must_be_separately_authorized_for_any_new_staging',
    requested_action: 'Read-only reconcile whether attributable same-cycle source evidence already exists under the approved destination. If absent, return a blocked report; do not backdate, manufacture old-cycle records, or change destinations. A new current-cycle review requires a separately authorized objective and source set.',
    required_return_fields: ['request_id', 'lineage_id', 'artifact_kind', 'artifact_ref', 'parent_ref', 'producer_role', 'producer_packet_id', 'actual_executed_at', 'evidence_refs'],
    downstream_trigger_authorized: false,
    credential_access_authorized: false,
    institutional_effect: 'none'
  };
  result.disposition = 'proposal_only';
  preparedRequests.add(result);
  return result;
}

/** Structural assessment only; independently reading the source is an external obligation. */
export function assessDependencyReturn(prepared, candidate, readback) {
  const result = { contract_version: CONTRACT_VERSION, disposition: 'hold', issues: [], effect: emptyEffect() };
  if (!preparedRequests.has(prepared) || prepared.disposition !== 'proposal_only') {
    result.issues.push('unrecognized_preparation'); return result;
  }
  if (candidate == null) { result.disposition = 'awaiting_provider_return'; return result; }
  const req = prepared.request;
  // A carrier may correctly refuse when current-cycle authority or historic evidence is absent.
  // This is a self-reported blocker, NOT proof of source absence or permission to resume.
  if (candidate && typeof candidate === 'object' && !Array.isArray(candidate) && candidate.outcome === 'blocked') {
    const reasons = new Set(['historical_evidence_not_found', 'current_objective_unavailable', 'authorized_sources_unavailable', 'source_access_unavailable', 'schedule_state_unverified']);
    if (candidate.request_id === req.request_id && candidate.lineage_id === req.expected_lineage_id &&
        candidate.producer_role === req.requested_owner_role && reasons.has(candidate.blocker) &&
        !Object.hasOwn(candidate, 'artifact_ref')) {
      result.disposition = 'provider_blocked_unattested';
      result.issues.push('source_absence_or_authority_block_not_independently_verified');
    } else result.issues.push('invalid_provider_blocker_claim');
    return result;
  }
  if (!candidate || typeof candidate !== 'object' || Array.isArray(candidate) ||
      candidate.request_id !== req.request_id || candidate.lineage_id !== req.expected_lineage_id ||
      candidate.artifact_kind !== req.expected_artifact_kind || candidate.producer_role !== req.requested_owner_role ||
      candidate.parent_ref !== req.expected_parent_ref ||
      !token(candidate.producer_packet_id) || !notionRef(candidate.artifact_ref) ||
      !timestamp(candidate.actual_executed_at) || (timestamp(candidate.actual_executed_at) && arizonaDate(candidate.actual_executed_at) !== req.expected_lineage_id.slice(-10)) || !Array.isArray(candidate.evidence_refs) ||
      candidate.evidence_refs.length === 0 || !candidate.evidence_refs.every(notionRef)) {
    result.issues.push('invalid_or_cross_cycle_provider_claim'); return result;
  }
  if (readback == null) { result.disposition = 'needs_independent_readback'; return result; }
  if (!readback || typeof readback !== 'object' || Array.isArray(readback) ||
      readback.request_id !== req.request_id || readback.lineage_id !== candidate.lineage_id ||
      readback.artifact_kind !== candidate.artifact_kind || readback.artifact_ref !== candidate.artifact_ref ||
      readback.parent_ref !== req.expected_parent_ref ||
      readback.producer_packet_id !== candidate.producer_packet_id ||
      !timestamp(readback.observed_at) || !notionRef(readback.observation_ref) ||
      readback.observation_ref === candidate.artifact_ref) {
    result.issues.push('independent_readback_missing_or_mismatched'); return result;
  }
  // The inputs may still be self-reported. This is NOT execution proof or approval.
  result.disposition = 'structurally_consistent_unattested';
  result.issues.push('external_source_attestation_and_human_review_required');
  return result;
}
