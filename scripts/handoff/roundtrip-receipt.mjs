import {createHash} from 'node:crypto';
import {TymeReceiptSemantics as S} from './receipt-semantics.mjs';
export const ROUNDTRIP_RECEIPT_VERSION='office-codex-receipt/1';
export const RECEIPT_SEMANTIC_PROFILE=S.profile;
const obj=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const bounded=x=>typeof x==='string'&&x.length>0&&x.length<=1024&&x.trim()===x&&!/[\u0000-\u001f\u007f]/.test(x);
const canon=x=>Array.isArray(x)?'['+x.map(canon).join(',')+']':obj(x)?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canon(x[k])).join(',')+'}':JSON.stringify(x);
const hash=x=>createHash('sha256').update(canon(x),'utf8').digest('hex');
export function receiptId({request_id,trace_id,correlation_sha256}){if(!bounded(request_id)||!bounded(trace_id)||!(/^[a-f0-9]{64}$/).test(correlation_sha256))throw TypeError('Invalid receipt identity inputs.');return 'ocr1-'+hash(['office-codex-roundtrip-receipt-v1',request_id,trace_id,correlation_sha256]).slice(0,32);}
export function receiptPath(id){if(typeof id!=='string'||!/^ocr1-[a-f0-9]{32}$/.test(id))throw TypeError('Invalid receipt id.');return `roundtrip-ledger/v1/${id}/receipt.json`;}
export function validateReceipt(receipt){
  const issues=S.validate(receipt);
  if(!obj(receipt))return {valid:false,issues:issues.map(code=>({code}))};
  try{if(receipt.receipt_id!==receiptId(receipt))issues.push('receipt_identity_mismatch');}catch{issues.push('receipt_identity_mismatch');}
  let reconstructed;
  try{const {content_sha256,...core}=receipt;reconstructed=hash(core);if(typeof content_sha256!=='string'||!/^[a-f0-9]{64}$/.test(content_sha256)||reconstructed!==content_sha256)issues.push('digest_mismatch');}catch{issues.push('digest_mismatch');}
  return {valid:issues.length===0,issues:[...new Set(issues)].map(code=>({code})),reconstructed_content_sha256:reconstructed,expected_content_sha256:receipt.content_sha256};
}
export function buildReceipt(input={}){
  if(!obj(input))return {valid:false,issues:[{code:'receipt_missing'}],receipt:null};
  const {institutional_effect='none',content_sha256,receipt_id,...rest}=input;
  if(institutional_effect!=='none')return {valid:false,issues:[{code:'institutional_effect_forbidden'}],receipt:null};
  const core={...rest,receipt_version:ROUNDTRIP_RECEIPT_VERSION,
    standing:input.standing??{claimed_by_executor:'none',institutional_effect:'none',hall_receipt_claimed:false,canon_claimed:false},
    proof_ceiling:input.proof_ceiling??{persistence_is_not_authority:true,transport_acceptance_is_not_completion:true,runtime_completion_is_not_review:true,review_is_not_canon:true},
    repository_receipt:input.repository_receipt??null,notion_readback:input.notion_readback??null};
  const issues=S.validate(core);if(issues.length)return {valid:false,issues:issues.map(code=>({code})),receipt:null};
  core.receipt_id=receiptId(core);
  const receipt=JSON.parse(JSON.stringify({...core,content_sha256:hash(core)}));
  return {valid:true,issues:[],receipt};
}
// Readback now requires both semantic validity and content/identity integrity.
export const verifyReadback=validateReceipt;
