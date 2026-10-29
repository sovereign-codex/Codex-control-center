import copy
import dataclasses
import pathlib
import sys
import tempfile
import time
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from adapter import *
from readback import verify

class FakeGithub:
    def __init__(self, approval):
        self.calls = []
        self.response = 204
        self.state = {repo: {'revision': rev, 'policy_blob': PINS[repo][1]}
                      for repo, rev in [(CCC, approval.source_revision), (AVOT, approval.receiver_revision)]}
    def snapshot(self):
        return self.state
    def post_once(self, body):
        self.calls.append(body)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = self.temp.name + '/attempt.sqlite'
        self.data = {'diagnostic_id': 'ccc-thread-diag-v1-test0001', 'expected_source_revision': 'a'*40}
        self.raw = canonical(self.data)
        self.approval = Approval(self.data['diagnostic_id'], 'a'*40, 'b'*40, 'operator', 123,
                                 digest(template(self.data)), 'auth-001', 'review-001', 'freeze-001', int(time.time())+300)
        self.principal = Principal('operator', frozenset({'router.diagnostic.invoke'}))
        self.gh = FakeGithub(self.approval)
        self.adapter = Adapter(self.path, self.gh, self.approval)
    def tearDown(self):
        self.adapter.db.close()
        self.temp.cleanup()
    def invoke(self):
        return self.adapter.invoke(self.raw, self.principal)
    def test_acceptance_is_not_arrival(self):
        r = self.invoke()
        self.assertEqual(r['dispatch_transport'], 'accepted_204')
        self.assertEqual(r['router_arrival'], 'not_observed')
        self.assertEqual(len(self.gh.calls), 1)
    def test_unauthorized_destinations_and_credentials(self):
        for key in ['host','url','method','repository','event_type','command','token','authorization','client_payload']:
            with self.subTest(key=key), self.assertRaises(Stop):
                self.adapter.invoke(canonical({**self.data, key: 'secret-canary'}), self.principal)
        self.assertEqual(self.gh.calls, [])
    def test_malformed(self):
        for raw in [b'[]', b'null', b'{', b'x'*8193, b'\xff', b'{"diagnostic_id":1,"diagnostic_id":2}',
                    canonical({**self.data,'diagnostic_id':'ccc-avot-receipt-probe-20261018-001'}),
                    canonical({**self.data,'expected_source_revision':'main'})]:
            with self.subTest(raw=raw[:50]), self.assertRaises(Stop):
                self.adapter.invoke(raw, self.principal)
    def test_missing_or_forged_authorization(self):
        for p in [None, {'subject':'operator'}, Principal('other', self.principal.scopes), Principal('operator', frozenset())]:
            with self.assertRaises(Stop):
                self.adapter.invoke(self.raw, p)
        self.adapter.approval = None
        with self.assertRaises(Stop): self.invoke()
        self.assertEqual(self.gh.calls, [])
    def test_invalid_grants(self):
        for changes in [{'expires_at':0}, {'expires_at':int(time.time())+7200}, {'review_ref':''},
                        {'freeze_ref':''}, {'authorization_ref':''}, {'request_sha256':'0'*64}]:
            self.adapter.approval = dataclasses.replace(self.approval, **changes)
            with self.assertRaises(Stop): self.invoke()
        self.assertEqual(self.gh.calls, [])
    def test_changed_source_or_policy(self):
        for repo in PINS:
            for field in ['revision','policy_blob']:
                old = self.gh.state[repo][field]
                self.gh.state[repo][field] = '0'*40
                with self.assertRaises(Stop): self.invoke()
                self.gh.state[repo][field] = old
        self.assertEqual(self.gh.calls, [])
    def test_duplicate_survives_restart(self):
        self.invoke()
        other = Adapter(self.path, self.gh, self.approval)
        try:
            with self.assertRaises(Stop): other.invoke(self.raw,self.principal)
        finally: other.db.close()
        self.assertEqual(len(self.gh.calls),1)
    def test_concurrent_reservations(self):
        import concurrent.futures
        import threading
        barrier = threading.Barrier(2)
        original = self.gh.snapshot
        def snapshot():
            barrier.wait(timeout=5)
            return original()
        self.gh.snapshot = snapshot
        def call():
            adapter = Adapter(self.path,self.gh,self.approval)
            try:
                return adapter.invoke(self.raw,self.principal)['dispatch_transport']
            except Stop as e:
                return str(e)
            finally:
                adapter.db.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _:call(),range(2)))
        self.assertCountEqual(outcomes,['accepted_204','experiment_already_reserved'])
        self.assertEqual(len(self.gh.calls),1)
    def test_ambiguous_locks_other_ids(self):
        self.gh.response = TimeoutError('Bearer secret-canary')
        result = self.invoke()
        self.assertEqual(result['dispatch_transport'],'uncertain')
        self.data['diagnostic_id'] = 'ccc-thread-diag-v1-test0002'
        self.raw = canonical(self.data)
        self.adapter.approval = dataclasses.replace(self.approval, diagnostic_id=self.data['diagnostic_id'], request_sha256=digest(template(self.data)))
        with self.assertRaises(Stop): self.invoke()
        self.assertNotIn('secret-canary', str(result))
        stored = repr(self.adapter.db.execute('SELECT * FROM attempt').fetchall())
        self.assertNotIn('secret-canary', stored)
        self.assertEqual(len(self.gh.calls),1)
    def test_reservation_precedes_transport(self):
        def post(body):
            with sqlite3.connect(self.path) as db:
                self.assertEqual(db.execute('SELECT status FROM attempt').fetchone()[0], 'uncertain')
            raise SystemExit('simulated_crash')
        self.gh.post_once = post
        with self.assertRaises(SystemExit): self.invoke()
        with self.assertRaises(Stop): self.invoke()
    def test_status_classification_and_no_retry(self):
        for status, expected in [(302,'uncertain'),(500,'uncertain'),(200,'uncertain'),(403,'rejected'),(429,'rejected')]:
            db = Adapter(self.temp.name+'/'+str(status), self.gh,self.approval)
            self.gh.response = status
            try:
                result = db.invoke(self.raw,self.principal)
                self.assertEqual(result['dispatch_transport'], expected)
                with self.assertRaises(Stop): db.invoke(self.raw,self.principal)
            finally: db.db.close()
        self.assertEqual(len(self.gh.calls),5)
    def test_transport_rejects_downstream_or_modified_template(self):
        transport = Github(lambda:'unused',lambda:'unused')
        for patch in [{'event_type':'avot_execution'}, {'event_type':'engine_handoff'}, {'command':'run'}]:
            body = {**strict(template(self.data)), **patch}
            with self.assertRaises(Stop): transport.post_once(canonical(body))
    def evidence(self):
        run = {'id':12,'run_attempt':1,'repository':{'full_name':CCC},'head_sha':'a'*40,
               'path':'.github/workflows/control-center-router.yml','event':'repository_dispatch','status':'completed'}
        event = canonical({'action':'route-event','repository':{'full_name':CCC},'sender':{'id':123},
                           'client_payload':strict(template(self.data))['client_payload']})
        result = {'contract_version':'ccc-handoff/1','stage':'router','disposition':'hold','request':None,
                  'issues':[{'code':'policy_disabled'}], 'evidence':{'actions_event_file_sha256':digest(event)},
                  'observation':{'run_id':'12','run_attempt':'1','actions_run_url':'https://github.com/'+CCC+'/actions/runs/12'},
                  'provenance':{'github_sender_id':'123'},'execution':{'status':'unverified','completion_claim':False}}
        files = {'observation-event.json':event,'prepare-prepared.json':canonical(result),'prepare-result.json':canonical(result),
                 'prepare-observation.json':canonical({'runId':'12','runAttempt':'1','eventName':'repository_dispatch','repository':CCC})}
        names = [('Prepare and validate handoff policy','failure'),('Create scoped dispatch token','skipped'),
                 ('Revalidate, claim, and dispatch once','skipped'),('Preserve handoff observations','success')]
        jobs = [{'run_id':12,'name':'route','steps':[{'name':n,'status':'completed','conclusion':c} for n,c in names]}]
        return [self.data,self.approval,run,jobs,'control-center-router-12-1',files,self.gh.state]
    def test_fixture_is_not_live_proof(self):
        r = verify(*self.evidence())
        self.assertEqual(r['evidence_authenticity'],'requires_independent_acquisition')
        self.assertEqual(r['no_effect_inventory'],'requires_bounded_readback')
    def test_bundle_loader_and_archive_rejection(self):
        import zipfile
        from verify_bundle import check
        e = self.evidence()
        root = pathlib.Path(self.temp.name)
        values = {'request-input.json':self.data,'approval.json':dataclasses.asdict(self.approval),
                  'run.json':e[2],'artifact.json':{'expired':False,'workflow_run':{'id':12},'name':e[4]},
                  'after-snapshot.json':e[6]}
        for name,value in values.items(): (root/name).write_bytes(canonical(value))
        (root/'jobs.jsonl').write_bytes(b'\n'.join(canonical(job) for job in e[3]))
        def archive(files):
            with zipfile.ZipFile(root/'observations.zip','w') as z:
                for name,raw in files.items(): z.writestr(name,raw)
        archive(e[5])
        self.assertEqual(check(root)['evidence_consistency'],'expected_disabled_hold')
        for files in [{**e[5],'../escape':b'{}'}, {**e[5],'execute-result.json':b'{}'},
                      {**e[5],'prepare-result.json':b' '*262145}]:
            archive(files)
            with self.assertRaises(Stop): check(root)
    def test_fabricated_or_missing_readback(self):
        for mutation in ['revision','sender','payload','digest','hold','missing','execute','skipped','attempt','artifact','policy']:
            e = self.evidence()
            if mutation=='revision': e[2]['head_sha']='c'*40
            if mutation=='sender':
                v=strict(e[5]['observation-event.json']); v['sender']['id']=999; e[5]['observation-event.json']=canonical(v)
            if mutation=='payload':
                v=strict(e[5]['observation-event.json']); v['client_payload']['payload']['synthetic']=False; e[5]['observation-event.json']=canonical(v)
            if mutation in ['digest','hold']:
                v=strict(e[5]['prepare-result.json'])
                if mutation=='digest': v['evidence']['actions_event_file_sha256']='0'*64
                else: v['issues']=[]
                e[5]['prepare-result.json']=canonical(v)
            if mutation=='missing': del e[5]['prepare-result.json']
            if mutation=='execute': e[5]['execute-result.json']=b'{}'
            if mutation=='skipped': e[3][0]['steps'][1]['conclusion']='success'
            if mutation=='attempt': e[2]['run_attempt']=2
            if mutation=='artifact': e[4]='other'
            if mutation=='policy': e[6]=copy.deepcopy(e[6]);e[6][AVOT]['policy_blob']='0'*40
            with self.subTest(mutation=mutation), self.assertRaises(Stop): verify(*e)

if __name__ == '__main__': unittest.main()
