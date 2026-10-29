"""Offline consistency check of separately acquired evidence, never live proof.

Usage: python verify_bundle.py DIRECTORY
Directory contains request-input.json, approval.json, run.json, jobs.jsonl,
artifact.json (selected artifact metadata), observations.zip, after-snapshot.json.
approval.json is sanitized operator data, not credentials or live authorization.
"""
import json
from pathlib import Path
import sys
import zipfile
from adapter import Approval, Stop, request, strict
from readback import verify


def check(directory):
    root = Path(directory)
    def load(name):
        return strict((root/name).read_bytes(), 1048576)
    data = request((root/'request-input.json').read_bytes())
    approval = Approval(**load('approval.json'))
    if data['diagnostic_id'] != approval.diagnostic_id or data['expected_source_revision'] != approval.source_revision:
        raise Stop('approval_mismatch')
    run, artifact = load('run.json'), load('artifact.json')
    if artifact.get('expired') is not False or artifact.get('workflow_run',{}).get('id') != run['id']:
        raise Stop('artifact_run_mismatch')
    archive = root/'observations.zip'
    if archive.stat().st_size > 2097152:
        raise Stop('archive_too_large')
    files = {}
    expected = {'observation-event.json','prepare-result.json','prepare-prepared.json','prepare-observation.json'}
    with zipfile.ZipFile(archive) as z:
        entries = z.infolist()
        if len(entries) != 4 or {i.filename for i in entries} != expected:
            raise Stop('unexpected_archive_entries')
        for item in entries:
            if item.file_size > 262144 or item.is_dir():
                raise Stop('archive_entry_too_large')
            files[item.filename] = z.read(item)
    raw = (root/'jobs.jsonl').read_bytes()
    if len(raw) > 1048576:
        raise Stop('jobs_too_large')
    jobs = [strict(line,1048576) for line in raw.splitlines() if line.strip()]
    return verify(data,approval,run,jobs,artifact['name'],files,load('after-snapshot.json'))


if __name__ == '__main__':
    try:
        if len(sys.argv)!=2: raise Stop('expected_evidence_directory')
        print(json.dumps(check(sys.argv[1]),indent=2))
    except Exception:
        print('{"evidence_consistency":"unverified","reason":"evidence_invalid_or_unavailable"}')
        sys.exit(1)
