"""Historical independent review probe; see adjacent README before running."""
import contextlib, copy, importlib.util, io, json, os, pathlib, subprocess, tempfile, unittest, zipfile
from unittest.mock import patch

ROOT = pathlib.Path(os.environ.get('GAIA_REVIEW_REPO', '.')).resolve()
spec=importlib.util.spec_from_file_location('recovery_candidate',ROOT / 'scripts/intake_recovery.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
REPO='gaia-research/gaia-skill-tree'

class Review2050(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='review2050-');self.addCleanup(self.tmp.cleanup)
        self.root=pathlib.Path(self.tmp.name)
        self.batch={'batchId':'independent-batch','proposedSkills':[]}
        self.batchpath=self.root/r.batchRelPath(self.batch['batchId'])
        self.batchpath.parent.mkdir(parents=True);self.batchpath.write_text(json.dumps(self.batch))
        self.p=json.loads(r.buildApprovalPayload(r.batchRelPath(self.batch['batchId']),2050,'maintainer',str(self.root),issueBody='approved-body',runId=123,runAttempt=2,headSha='a'*40))
        self.handoff={'approval':copy.deepcopy(self.p),'record':None}
        self.run={'id':123,'run_attempt':2,'workflow_id':77,'path':r.WORKFLOW_PATH,'repository':{'full_name':REPO},'head_repository':{'full_name':REPO},'head_sha':'a'*40,'event':'issues','status':'completed','conclusion':'success','actor':{'login':'maintainer'},'triggering_actor':{'login':'maintainer'}}
        self.artifact={'id':678,'name':r.handoffArtifactName(2050,123,2),'expired':False,'size_in_bytes':1000}
        self.permissions={}
    def api(self,url,binary=False):
        if url.endswith('/actions/workflows/intake-approval.yml'):return {'id':77,'path':r.WORKFLOW_PATH}
        if '/attempts/' in url:return copy.deepcopy(self.run)
        if '/collaborators/' in url:return {'permission':self.permissions.get(url.split('/collaborators/')[1].split('/')[0],'write')}
        if '/runs/' in url and '/artifacts?' in url:return {'artifacts':[copy.deepcopy(self.artifact)]}
        if url.endswith('/zip'):
            b=io.BytesIO()
            with zipfile.ZipFile(b,'w') as z:z.writestr('intake-handoff.json',json.dumps(self.handoff))
            return b.getvalue()
        raise AssertionError(url)
    def verify(self,p):return r.verifyHandoff(p,api=self.api,repository=REPO)
    def doc(self,p=None,body='approved-body',author='github-actions[bot]'):
        return {'body':body,'comments':[{'author':{'login':author},'body':r.APPROVAL_HEADER+'\n<!-- gaia-intake-approval '+json.dumps(p or self.p)+' -->'}]}
    def materialize(self,doc):return r.materialize(2050,doc,str(self.root),lambda _:b'unchanged',verifier=self.verify)
    def test_valid_authenticated_handoff(self):self.assertEqual(self.verify(self.p),self.handoff)
    def test_forged_pointer_differs_from_artifact(self):
        p=copy.deepcopy(self.p);p['topologyApprovedBy']='other-maintainer';self.run['actor']['login']='other-maintainer';self.run['triggering_actor']['login']='other-maintainer'
        with self.assertRaises(r.RecoveryError):self.verify(p)
    def test_wrong_actor(self):
        self.run['actor']['login']='attacker'
        with self.assertRaises(r.RecoveryError):self.verify(self.p)
    def test_unprivileged_rerunner(self):
        self.run['triggering_actor']['login']='attacker';self.permissions['attacker']='read'
        with self.assertRaises(r.RecoveryError):self.verify(self.p)
    def test_pull_request_event(self):
        self.run['event']='pull_request'
        with self.assertRaises(r.RecoveryError):self.verify(self.p)
    def test_fork_provenance(self):
        self.run['head_repository']['full_name']='attacker/fork'
        with self.assertRaises(r.RecoveryError):self.verify(self.p)
    def test_wrong_workflow(self):
        self.run['workflow_id']=999
        with self.assertRaises(r.RecoveryError):self.verify(self.p)
    def test_wrong_attempt(self):
        self.run['run_attempt']=1
        with self.assertRaises(r.RecoveryError):self.verify(self.p)
    def test_unfinished_event(self):
        self.run['status']='in_progress';self.run['conclusion']=None
        with self.assertRaises(r.RecoveryError):self.verify(self.p)
    def test_expired_artifact(self):
        self.artifact['expired']=True
        with self.assertRaises(r.RecoveryError):self.verify(self.p)
    def test_human_comment_is_not_authority(self):
        with self.assertRaises(r.RecoveryError):self.materialize(self.doc(author='attacker'))
    def test_stale_issue_body_rejected(self):
        with self.assertRaises(r.RecoveryError):self.materialize(self.doc(body='edited-after-artifact'))
    def test_stale_batch_rejected(self):
        self.batchpath.write_text(json.dumps({'batchId':'independent-batch','proposedSkills':[{'id':'injected'}]}))
        with self.assertRaises(r.RecoveryError):self.materialize(self.doc())
    def test_existing_batch_reruns_are_idempotent(self):
        self.assertEqual(self.materialize(self.doc()),{'status':'no-recovery','files':[]})
        self.assertEqual(self.materialize(self.doc()),{'status':'no-recovery','files':[]})
    def test_rerun_identity_changes_do_not_change_record(self):
        receipt={'authorization':{'recoveredBy':'first'},'issueBodySha256':'old','sources':[]}
        later=copy.deepcopy(receipt);later.update(authorization={'recoveredBy':'second'},issueBodySha256='new')
        self.assertEqual(r.recordIdentityDigest(self.batch,receipt),r.recordIdentityDigest(self.batch,later))
    def bind_recovery(self):
        receipt={'issue':2050,'reconstruction':True,'issueBodySha256':r.sha256Hex('approved-body'),'sources':[{'skillId':'synthetic','url':'https://github.com/example/fixture/blob/main/SKILL.md','sha256':r.sha256Hex(b'unchanged')}],'reconstructedBatch':{'sha256':r.sha256Hex(r.canonicalJson(self.batch))}}
        self.p=json.loads(r.buildApprovalPayload(r.batchRelPath(self.batch['batchId']),2050,'maintainer',str(self.root),receipt=receipt,issueBody='approved-body',runId=123,runAttempt=2,headSha='a'*40))
        self.handoff={'approval':copy.deepcopy(self.p),'record':{'batch':copy.deepcopy(self.batch),'receipt':receipt}}
    def test_recovery_materialize_rerun_is_idempotent(self):
        self.bind_recovery();self.batchpath.unlink()
        first=self.materialize(self.doc());self.assertEqual(first['status'],'materialized');self.assertEqual(len(first['files']),2)
        self.assertEqual(self.materialize(self.doc()),{'status':'recovery-already-present','files':[]})
    def test_upstream_stale_even_when_recovery_batch_present(self):
        self.bind_recovery()
        with self.assertRaises(r.RecoveryError):r.materialize(2050,self.doc(),str(self.root),lambda _:b'upstream changed',verifier=self.verify)
    def test_missing_receipt_is_restored_for_existing_batch(self):
        self.bind_recovery()
        result=self.materialize(self.doc());self.assertEqual(result['status'],'recovery-already-present')
        self.assertEqual(result['files'],[r.receiptRelPath(2050)])
    def test_issue_number_shell_injection_is_inert(self):
        import yaml
        workflow=yaml.safe_load((ROOT / '.github/workflows/intake-approval.yml').read_text())
        step=workflow['jobs']['topology-approved']['steps'][0]['run']
        for token,value in [('github.event_name','workflow_dispatch'),('github.actor','maintainer'),('github.event.issue.number','2050'),('github.event.sender.login','maintainer')]:
            step=step.replace('${{ '+token+' }}',value)
        marker=self.root/'shell-injected'
        env={**os.environ,'ISSUE_NUMBER_INPUT':'$(touch '+str(marker)+')','BASE_REF_INPUT':'main','GITHUB_OUTPUT':str(self.root/'output'),'GITHUB_REPOSITORY':REPO}
        result=subprocess.run(['bash','-c','gh() { return 0; }\n'+step],env=env,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertFalse(marker.exists())
    def test_label_event_race_refused_before_payload_creation(self):
        event=self.root/'event.json';event.write_text(json.dumps({'action':'labeled','label':{'name':'intake:topology-approved'},'issue':{'number':2050,'body':'human-approved-old-body'},'sender':{'login':'maintainer'}}))
        live=self.root/'live.json';live.write_text(json.dumps({'number':2050,'body':'attacker-edited-after-label'}))
        artifact=self.root/'intake-handoff.json'
        with patch.dict(os.environ,{'GITHUB_EVENT_PATH':str(event),'GITHUB_EVENT_NAME':'issues','GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'2','GITHUB_SHA':'a'*40}),contextlib.redirect_stderr(io.StringIO()):
            code=r.main(['check-revision','--issue-json',str(live),'--transition','topology'])
        self.assertEqual(code,r.EXIT_STALE);self.assertFalse(artifact.exists())
    def test_dispatch_exact_selected_digest_accepted(self):
        r.verifyIssueRevision({'number':2050,'body':'selected'},'workflow_dispatch',{},'topology',r.sha256Hex('selected'))
    def test_dispatch_author_edit_after_selection_refused(self):
        with self.assertRaises(r.RecoveryError):r.verifyIssueRevision({'number':2050,'body':'edited'},'workflow_dispatch',{},'topology',r.sha256Hex('selected'))
    def test_dispatch_missing_digest_refused(self):
        with self.assertRaises(r.RecoveryError):r.verifyIssueRevision({'number':2050,'body':'selected'},'workflow_dispatch',{},'topology')
    def test_wrong_label_transition_refused(self):
        with self.assertRaises(r.RecoveryError):r.verifyIssueRevision({'number':2050,'body':'selected'},'issues',{'action':'labeled','issue':{'number':2050,'body':'selected'},'label':{'name':'intake:topology-approved'}},'evidence')
    def test_evidence_old_body_restoration_refused(self):
        with self.assertRaises(r.RecoveryError):r.verifyIssueRevision({'number':2050,'body':'old'},'issues',{'action':'labeled','issue':{'number':2050,'body':'new-reviewed-body'},'label':{'name':'intake:evidence-approved'}},'evidence')

if __name__=='__main__':unittest.main(verbosity=2)
