"""Pure verifier for evidence collected independently through read-only GitHub.

This checks consistency, NOT the authenticity of caller-supplied files. Never
expose evidence arguments as an MCP tool. See README for independent acquisition.
No sender-supplied booleans such as `verified` can establish a live result.
"""
from adapter import CCC, Stop, check_snapshot, digest, strict, template


def verify(data, approval, run, jobs, artifact_name, files, after_snapshot):
    try:
        if (data['diagnostic_id'] != approval.diagnostic_id or
                data['expected_source_revision'] != approval.source_revision or
                digest(template(data)) != approval.request_sha256):
            raise Stop('request_approval_mismatch')
        check_snapshot(after_snapshot, approval)
        if (run['repository']['full_name'] != CCC or
                run['head_sha'] != approval.source_revision or
                run['path'] != '.github/workflows/control-center-router.yml' or
                run['event'] != 'repository_dispatch' or run['status'] != 'completed' or
                run['run_attempt'] != 1 or type(run['id']) is not int):
            raise Stop('wrong_run')
        rid = str(run['id'])
        if artifact_name != 'control-center-router-' + rid + '-1':
            raise Stop('wrong_artifact')
        if any(name.startswith('execute-') for name in files):
            raise Stop('execution_evidence_present')
        event_raw = files['observation-event.json']
        event = strict(event_raw, 262144)
        prepared = strict(files['prepare-prepared.json'], 262144)
        result = strict(files['prepare-result.json'], 262144)
        observation = strict(files['prepare-observation.json'])
        if (event['action'] != 'route-event' or event['repository']['full_name'] != CCC or
                type(event['sender']['id']) is not int or event['sender']['id'] != approval.sender_id or
                event['client_payload'] != strict(template(data))['client_payload']):
            raise Stop('event_correlation_failed')
        if (observation['eventName'] != 'repository_dispatch' or observation['repository'] != CCC or
                observation['runId'] != rid or observation['runAttempt'] != '1'):
            raise Stop('observation_mismatch')
        expected_url = 'https://github.com/' + CCC + '/actions/runs/' + rid
        for value in (prepared, result):
            if (value['contract_version'] != 'ccc-handoff/1' or value['stage'] != 'router' or
                    value['disposition'] != 'hold' or value['request'] is not None or
                    'policy_disabled' not in [i['code'] for i in value['issues']] or
                    value['evidence']['actions_event_file_sha256'] != digest(event_raw) or
                    value['observation']['run_id'] != rid or value['observation']['run_attempt'] != '1' or
                    value['observation']['actions_run_url'] != expected_url or
                    value['provenance']['github_sender_id'] != str(approval.sender_id) or
                    value['execution'] != {'status': 'unverified', 'completion_claim': False}):
                raise Stop('hold_not_proven')
        if len(jobs) != 1 or jobs[0]['run_id'] != run['id'] or jobs[0]['name'] != 'route':
            raise Stop('wrong_jobs')
        steps = jobs[0]['steps']
        for name, conclusion in [('Prepare and validate handoff policy', 'failure'),
                                 ('Create scoped dispatch token', 'skipped'),
                                 ('Revalidate, claim, and dispatch once', 'skipped'),
                                 ('Preserve handoff observations', 'success')]:
            matched = [s for s in steps if s['name'] == name]
            if len(matched) != 1 or matched[0]['status'] != 'completed' or matched[0]['conclusion'] != conclusion:
                raise Stop('step_boundary_unverified')
        return {'evidence_consistency': 'expected_disabled_hold',
                'evidence_authenticity': 'requires_independent_acquisition',
                'github_sender_id': str(approval.sender_id),
                'actions_event_sha256': digest(event_raw),
                'initiating_request_sha256': digest(template(data)),
                'custom_app_authentication': 'not_tested', 'downstream_execution': 'not_tested',
                'authority_effect': 'none', 'no_effect_inventory': 'requires_bounded_readback'}
    except Stop:
        raise
    except Exception:
        raise Stop('evidence_missing_or_malformed') from None
