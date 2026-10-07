from pathlib import Path
import json,hashlib,importlib.util,subprocess
O=Path(__file__).resolve().parent;B=O.parent;E=B/'m63-grading-public1e-diagnosis-evidence-oct05';S=E/'seal-original1e';P=S/'publication-candidates'
def sha(b):return hashlib.sha256(b).hexdigest()
assert sha((S/'SAFE_CANDIDATES.json').read_bytes())=='be750d4823e7a711a4b62126a004b50f78d0ae56b28f8bf0f753a04e8242d471'
assert sha((S/'READBACK.json').read_bytes())=='dc69453eb29be8f76d6a046fb8c82f10b8362c3064a0f11974b5d38e1c7831b5'
m=json.loads((S/'SAFE_CANDIDATES.json').read_bytes());rows=[]
for e in m['entries']:
 b=(P/e['candidate_path']).read_bytes();assert len(b)==e['size'] and sha(b)==e['sha256']
 if 'source_alias' in e['origin']:
  origin=e['origin'];rawroot=Path(m['raw_source_aliases'][origin['source_alias']].replace('~','$HOME',1));raw=(rawroot/origin['source_path']).read_bytes()
  assert len(raw)==e['original']['size'] and sha(raw)==e['original']['sha256']
  assert b==raw if e['transformation']=='identity' else b==raw.replace(b'$HOME',b'~')
 else:
  assert e['transformation']=='identity' and e['origin']['kind'].startswith('new_')
  assert len(b)==e['original']['size'] and sha(b)==e['original']['sha256']
 rows.append(e)
assert len(rows)==23 and sum(e['size'] for e in rows)==4389562
basefile=B/'m63-turn-protocol-catalog-evidence-oct05/seal-27f/publication-candidates/FULL_GIT_INPUTS.json'
base=next(x for x in json.loads(basefile.read_bytes())['maps'] if x['head']=='27f549ff5a8fd67b0a601b67a5ba51ef35f6765f')
old={e['path']:(e['mode'],e['type'],e['blob'],e['size'],e['sha256']) for e in base['entries']};assert len(old)==1541
maps=[]
for n in ['ORIGINAL_GIT_INPUTS.json']+[s+'/'+x+'.json' for s in ['setup-01','original-list-01','original-three-cases-01'] for x in ['before','after']]:
 d=json.loads((P/n).read_bytes());assert d['head']=='1e7ad7a8656c0dc8373d4181fa3002f385ed1847' and d['count']==1541 and d['all_live_equals_fixed_git']
 actual={e['path']:(e['git_mode'],e['git_type'],e['git_blob'],e['size'],e['sha256']) for e in d['files']}
 assert actual==old and all(e['live_git_blob']==e['git_blob'] and e['live_equals_fixed_git'] for e in d['files'])
 maps.append({'name':n,'count':len(actual),'sha256':sha((P/n).read_bytes())})
T=B/'m63-grading-public1e-diagnosis-oct05'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=T).decode().strip()=='1e7ad7a8656c0dc8373d4181fa3002f385ed1847' and not subprocess.check_output(['git','status','--porcelain'],cwd=T)
for p,e in old.items():
 b=(T/p).read_bytes();assert len(b)==e[3] and sha(b)==e[4]
runner=(E/'run_grading_original.py').read_bytes();stages=[]
for s in ['setup-01','original-list-01','original-three-cases-01']:
 c=json.loads((P/s/'command.json').read_bytes());r=json.loads((P/s/'receipt.json').read_bytes());l=(E/s/'run.log').read_bytes()
 assert r['exit_code']==0 and r['head_before']==r['head_after']==c['fixed_source_head']=='1e7ad7a8656c0dc8373d4181fa3002f385ed1847'
 assert r['complete_before_after_files_exact'] and r['after_live_equals_fixed_git'] and not r['changed_tracked_inputs']
 assert r['run_log_size']==len(l) and r['run_log_sha256']==sha(l) and c['runner_sha256']==sha(runner)
 assert (c['original_timeout_ms'],c['original_retry'],c['original_workers'])==(30000,0,1)
 stages.append({'stage':s,'command':c,'receipt':r})
assert b'3 passed (40.8s)' in (P/'original-three-cases-01/run.log').read_bytes()
assert sha((E/'PUBLICATION_VERIFICATION_NOTE.json').read_bytes())=='834bc3876358b38a4cf5840390a9bb80cacf799683568c13308ed372e0604d03'
(O/'GRADING_ROOT_ADMISSION.json').write_text(json.dumps({'role':'root independent fixed immutable source/map continuity, live1541bytes, original3stage/finite23copy qualification; no rerun or product repair',
 'candidate_count':23,'raw_copy_entries':20,'new_authored_metadata_entries':3,'root_verifier_v1':'KeyError source_alias before mutations; failed script/error preserved; v2 treats three authored metadata as authored, not external originals','source_maps':maps,'stages':stages,'source':'1e7ad7a8656c0dc8373d4181fa3002f385ed1847',
 'baseline':'Previously root-qualified immutable27f1541engineering; mode/type/blob/size/SHA identical to public1e; oldpayload notrecatted',
 'actual_result':'oneoriginal3gradingcases3PASS40.8s; sourceinputs unchanged; doesnotreproduce/repair oldCI',
 'root_manually_confirmed':'gradehelper202returns0; GradingService.result latestnotcompleted returnspendingstatus inclfailed/cancelled; productionuseGradingResult distinguishes Jobstatus; this is testdiagnosticgap notproved causalbug',
 'metadata':'Only source-defined688B actual-grading-form and fixedsafe status/signaturecounts; privateotherpayload excluded',
 'tool_error_preserved':'postseal finalprintwrongREADBACKpathFileNotFoundError; correctedactual23/20copy check in separatelyadmittednote; notproductFAIL',
 'limits':['No product/testsource edit/REDGREEN/secondbusinessrun or oldCIcauseclosure','Fullnative/Web/Python/current1561qualification NOT_RUN','0model/remote/probe/unknownprocesslookup/DB/PNG/profilepayload access']},ensure_ascii=False,indent=2)+'\n')
sp=importlib.util.spec_from_file_location('packet_helper',B/'m63-412abe-progress-checkpoint-oct05/package-helper-archived.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
path=h.package('M6.3-original-public1e-grading-three-cases-once-PASS-unresolved-CI-and-status-observation-gap',[
 ('original-owner-qualified','m63-grading-public1e-diagnosis-evidence-oct05/seal-original1e/publication-candidates',[e['candidate_path'] for e in m['entries']]),
 ('seal','m63-grading-public1e-diagnosis-evidence-oct05/seal-original1e',['SAFE_CANDIDATES.json','READBACK.json']),
 ('owner-tool-error-correction','m63-grading-public1e-diagnosis-evidence-oct05',['PUBLICATION_VERIFICATION_NOTE.json']),
 ('root-independent','m63-broker6f-progress-checkpoint-oct05',['install-grading.py','GRADING_ROOT_ADMISSION.json','install-grading-v1-failed.py','GRADING_ADMISSION_TOOL_V1_FAILURE.json'])],
 {'scope':'One unchangedpublic1e actual3case grading regression PASS and bounded diagnostic review; no sourcefix or originalCI rerun',
 'source':'1e7ad7a8656c0dc8373d4181fa3002f385ed1847','actual_passed':3,'PW_seconds':40.8,'actual_inputs':1541,
 'root_qualification':'23finitecopies/7maps10787bindings/3stagebeforeafter9246entries; immutableGitcontinuity+live1541exact;selfrunner commands/logs/receipts exact',
 'original_failure':'pushCI grade expected3 observed0 sentinel remainsFAIL/causeUNKNOWN; not numericalscore0 or actualworkerstate',
 'confirmed_gap':'gradehelper discards202pendingstatus; no concrete productdefect proven; narrowpayload-freefutureobserverNOT_IMPLEMENTED',
 'metadata':'Only synthetic688B source-defined firstcase grading formstatus/counts admitted; no private solutions/signaturevalues',
 'tooling':'originalsealverificationwrongprintpathFileNotFoundError retained in separatecorrection; no productrerun',
 'current1561_acceptance':'NOT_PROVIDED_BY_OLD1E_SUBSET','M6_3_AC21_M7':'NOT_ACCEPTED','model_calls':0,'remote_write':False})
(O/'GRADING_INSTALL_READBACK.json').write_text(json.dumps({'grading_evidence':path,'actual_original3case':'3PASS40.8s','prod_or_testsource_changed':False,'oldCI':'FAIL_UNRESOLVED_UNKNOWN','current1561whole':'NOT_RUN'},ensure_ascii=False,indent=2)+'\n')
print('Qualified and archived one original grading regression; oldCI not reclassified.')
