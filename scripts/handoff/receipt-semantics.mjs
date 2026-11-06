// Shared semantic profile. No hashing, storage, network, or authority side effects.
const TymeReceiptSemantics = (() => {
  const profile='tyme-receipt-semantics/1';
  const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
  const text=x=>typeof x==='string'&&x.length>0&&x.length<=1024&&x.trim()===x&&!/[\u0000-\u001f\u007f]/.test(x);
  const hex=(x,n)=>typeof x==='string'&&new RegExp('^[a-f0-9]{'+n+'}$').test(x);
  const stages=['accepted','runtime_started','runtime_completed','result_returned','evidence_stored'];
  const ceilings=['persistence_is_not_authority','transport_acceptance_is_not_completion','runtime_completion_is_not_review','review_is_not_canon'];
  function validate(r){
    const issues=[];const add=c=>issues.push(c);
    const shape=(v,keys,code)=>{if(!object(v)||Object.keys(v).some(k=>!keys.includes(k)))add(code);};
    if(!object(r))return ['receipt_missing'];
    shape(r,['receipt_version','receipt_id','content_sha256','request_id','trace_id','correlation_sha256','origin_office_role','executor','task','transport','result','review','standing','proof_ceiling','repository_receipt','notion_readback'],'unknown_receipt_field');
    if(r.receipt_version!=='office-codex-receipt/1')add('unsupported_receipt_version');
    if(!text(r.request_id)||!text(r.trace_id)||!hex(r.correlation_sha256,64)||!text(r.origin_office_role))add('identity_inputs_invalid');
    shape(r.executor,['runtime_class','endpoint_id','session_or_run_id'],'executor_shape_invalid');
    if(!['codex_agent','workspace_agent'].includes(r.executor?.runtime_class)||!text(r.executor?.endpoint_id)||!text(r.executor?.session_or_run_id))add('executor_identity_missing');
    shape(r.task,['repository','sha','authority_ceiling'],'task_shape_invalid');
    if(r.task?.authority_ceiling!=='READ_ONLY')add('invalid_authority_ceiling');
    if(r.task?.repository!=null||r.task?.sha!=null){if(!text(r.task?.repository)||!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(r.task.repository)||!hex(r.task.sha,40))add('task_repository_invalid');}
    shape(r.transport,stages,'transport_shape_invalid');
    if(!stages.every(k=>typeof r.transport?.[k]==='boolean'))add('transport_shape_invalid');
    if(stages.some((k,i)=>r.transport?.[k]===true&&stages.slice(0,i).some(p=>r.transport?.[p]!==true)))add('incomplete_lifecycle');
    shape(r.result,['summary','evidence_refs','assumptions','uncertainty'],'result_shape_invalid');
    if(!text(r.result?.summary)||!['evidence_refs','assumptions','uncertainty'].every(k=>Array.isArray(r.result?.[k])&&r.result[k].every(text)))add('result_shape_invalid');
    if(!Array.isArray(r.result?.evidence_refs)||r.result.evidence_refs.length===0)add('missing_evidence');
    shape(r.review,['reviewing_office_role','completed','verdict'],'review_shape_invalid');
    if(!text(r.review?.reviewing_office_role)||typeof r.review?.completed!=='boolean'||!['PASS','PARTIAL','FAIL','HOLD','UNREVIEWED'].includes(r.review?.verdict))add('review_shape_invalid');
    if(r.review?.completed===true&&(!stages.every(k=>r.transport?.[k]===true)||r.review.verdict==='UNREVIEWED'))add('false_completion_claim');
    if(r.review?.completed!==true&&r.review?.verdict==='PASS')add('false_completion_claim');
    shape(r.standing,['claimed_by_executor','institutional_effect','hall_receipt_claimed','canon_claimed'],'standing_shape_invalid');
    if(r.standing?.claimed_by_executor!=='none'||r.standing?.institutional_effect!=='none'||r.standing?.hall_receipt_claimed!==false||r.standing?.canon_claimed!==false)add('false_authority_claim');
    shape(r.proof_ceiling,ceilings,'proof_ceiling_invalid');
    if(!ceilings.every(k=>r.proof_ceiling?.[k]===true))add('proof_ceiling_invalid');
    // This profile binds later custody observations externally. Legacy non-null fields require explicit review.
    if(r.repository_receipt!==null||r.notion_readback!==null)add('embedded_custody_forbidden');
    return [...new Set(issues)];
  }
  return Object.freeze({profile,validate});
})();

export {TymeReceiptSemantics};
