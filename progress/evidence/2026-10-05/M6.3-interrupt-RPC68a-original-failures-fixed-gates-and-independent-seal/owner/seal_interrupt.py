"""Owner fixed-source/gate qualification and finite safe-candidate seal; no product execution."""
from collections import Counter
from io import BytesIO
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parent
TREE=ROOT.parent/'m63-interrupt-rpc-pairing-oct06'
SEAL=ROOT/'seal-68a'
BASE='27f549ff5a8fd67b0a601b67a5ba51ef35f6765f'
FINAL='68a280b9cf251bbf79c2ca188ac8b4aefe7562e0'
SPEC='b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def js(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
def git(*args):return subprocess.check_output(['git','-C',str(TREE),*args])
def load(path):return json.loads(path.read_bytes())
assert not SEAL.exists()
assert git('rev-parse','HEAD').decode().strip()==FINAL
assert git('status','--porcelain','--untracked-files=all')==b''
heads=[BASE,*git('rev-list','--reverse',BASE+'..'+FINAL).decode().splitlines()]
assert len(heads)==14
raw_trees={}
blobs=set()
for head in heads:
 entries=[]
 for row in git('ls-tree','-r','-z',head).split(b'\0'):
  if not row:continue
  meta,path=row.split(b'\t',1);path=path.decode();mode,kind,blob=meta.decode().split()
  assert kind=='blob'
  entries.append({'path':path,'mode':mode,'type':kind,'blob':blob})
  if not path.startswith('progress/'):blobs.add(blob)
 raw_trees[head]=entries
ordered=sorted(blobs)
output=subprocess.check_output(['git','-C',str(TREE),'cat-file','--batch'],input=('\n'.join(ordered)+'\n').encode())
stream=BytesIO(output);cache={}
for expected in ordered:
 actual,kind,size=stream.readline().decode().split();assert actual==expected and kind=='blob'
 raw=stream.read(int(size));assert len(raw)==int(size) and stream.read(1)==b'\n';cache[actual]=raw
assert not stream.read()
maps=[]
for head in heads:
 entries=[]
 for e in raw_trees[head]:
  if e['path'].startswith('progress/'):continue
  raw=cache[e['blob']];entries.append({**e,'size':len(raw),'sha256':sha(raw)})
 maps.append({'head':head,'tree':git('rev-parse',head+'^{tree}').decode().strip(),'count':len(entries),'entries':entries})
by_head={m['head']:m for m in maps}
old={e['path']:e for e in maps[0]['entries']};new={e['path']:e for e in maps[-1]['entries']}
delta=sorted(p for p in set(old)|set(new) if old.get(p)!=new.get(p))
assert len(old)==1541 and len(new)==1553 and len(delta)==12 and all(p not in old for p in delta)
assert all(old[p]==new[p] for p in old)
old_progress=[e for e in raw_trees[BASE] if e['path'].startswith('progress/')]
new_progress=[e for e in raw_trees[FINAL] if e['path'].startswith('progress/')]
assert old_progress==new_progress
for entry in new.values():assert (TREE/entry['path']).read_bytes()==cache[entry['blob']]
assert new['PRODUCT_DESIGN.md']['sha256']==SPEC
TEST='tests/unit/test_codex_interrupt_rpc_pairing.py'
def entry(head,path=TEST):return next(e for e in by_head[head]['entries'] if e['path']==path)
pairs=[('initial_33_lines','ce06496082d71026b4c12b0a9c8fc5e122fc8352','ef04831ce59939e78700880c3951cf9dd34de7f7'),
 ('member_deletion_48_lines','afcd4dd229206c43989a2e7fd9c749dc45da7955','e8fd902230e976d4dbe71fc93ea5e6a9897135a6'),
 ('frame_type_same_407_lines','797fa2a0e7af502e9046ef2c81ab8c74a8b78868','046f854a6b237142d6a16c9ae3806a15b60db299'),
 ('decoder_depth_502_lines','f134f0831bda107309e604d0826137b855cbc115',FINAL)]
pair_rows=[]
for name,red,green in pairs:
 assert entry(red)==entry(green)
 e=entry(red);pair_rows.append({'name':name,'red':red,'green':green,'whole_test_original_bytes_equal':True,'binding':e,
  'actual_line_count':len(cache[e['blob']].splitlines()),'qualification':'Exact test bytes only; see stage classifications for aggregate failures/oracle limits'})
assert git('diff','--numstat','f134f0831bda107309e604d0826137b855cbc115',FINAL).decode().strip()==('1\t1\tservices/api/app/infrastructure/codex_interrupt_protocol.py')
runner_sha=sha((ROOT/'run_stage.py').read_bytes())
stages=sorted(p.name for p in ROOT.iterdir() if p.is_dir() and (p/'receipt.json').is_file())
assert len(stages)==27
failures={'interrupt-pair-red-01','interrupt-pair-green-01','membership-red-01','membership-red-02',
 'expanded-focused-01','expanded-focused-02','expanded-focused-03','mypy-final-01','decoder-depth-red-01'}
stage_rows=[]
for stage in stages:
 p=ROOT/stage;receipt=load(p/'receipt.json');command=load(p/'command.json');before=load(p/'before.json');after=load(p/'after.json');raw=(p/'run.log').read_bytes()
 assert before==after==by_head[receipt['head']]
 assert receipt['before_after_complete_exact'] and receipt['input_count']==before['count']
 assert command['source_head']==receipt['head'] and command['cwd']==str(TREE)
 assert receipt['runner_sha256']==command['runner_sha256']==runner_sha
 assert sha(raw)==receipt['log_sha256'] and len(raw)==receipt['log_size']
 assert receipt['command_exit_code']==receipt['wrapper_exit_code']
 assert (receipt['command_exit_code']!=0)==(stage in failures)
 match=re.search(r'^\d+ (?:failed, \d+ passed|failed|passed)[^\n]*$',raw.decode(),re.M)
 stage_rows.append({**receipt,'summary':match[0] if match else raw.decode().strip(),
  'command_sha256':sha((p/'command.json').read_bytes()),'before_sha256':sha((p/'before.json').read_bytes()),'after_sha256':sha((p/'after.json').read_bytes())})
source_root=ROOT.parent/'m63-app-server-protocol-recon-oct03'
raw_receipt=(source_root/'receipt.json').read_bytes()
assert len(raw_receipt)==55893 and sha(raw_receipt)=='b64f43cd1b5a7024bcdcb421292cef93b61721ba76a4f325e7663be93931cd9c'
original_receipt=json.loads(raw_receipt);receipt_members={e['path'].removeprefix('schemas/'):e for e in original_receipt['files']}
prefix='services/api/app/infrastructure/codex_interrupt_protocol/'
projection_entry=new[prefix+'source-summary.json'];projection_raw=cache[projection_entry['blob']];projection=json.loads(projection_raw)
assert len(projection_raw)==1833 and sha(projection_raw)=='9bbb226ad6cf51c1d5fee39beb389ba37d5438d0722cd308c642bdc0fd0cf9c9'
assert b'/home/' not in projection_raw and 'command' not in projection and 'argv' not in projection
for field,orig in [('historical_cli_version','version'),('historical_binary_sha256','binary_sha256'),('historical_generated_files','generated_files'),('historical_exit_code','exit'),('historical_generated_at','at')]:assert projection[field]==original_receipt[orig]
# A documentary local JSON-pointer verification; no library/schema/network execution.
def internal_refs(schema):
 pending=[schema];refs=0
 while pending:
  node=pending.pop()
  if isinstance(node,dict):
   if '$ref' in node:
    ref=node['$ref'];assert ref.startswith('#/');target=schema
    for component in ref[2:].split('/'):
     assert re.search(r'~(?![01])',component) is None
     key=component.replace('~1','/').replace('~0','~')
     target=target[int(key)] if isinstance(target,list) else target[key]
    assert isinstance(target,(dict,bool));refs+=1
   pending.extend(node.values())
  elif isinstance(node,list):pending.extend(node)
 return refs
schema_bindings=[]
for member in projection['selected_files']:
 original=(source_root/'schemas'/member['path']).read_bytes();e=new[prefix+member['path']]
 assert original==cache[e['blob']]
 assert len(original)==member['size']==receipt_members[member['path']]['bytes']
 assert sha(original)==member['sha256']==receipt_members[member['path']]['sha256']
 schema_bindings.append({**member,'git_blob':e['blob'],'receipt_entry_exact':True,'original_bytes_exact':True,'internal_refs':internal_refs(json.loads(original))})
assert sum(e['size'] for e in schema_bindings)==473257 and sum(e['internal_refs'] for e in schema_bindings)==655
source_binding={'role':'Implementation owner documentary readback, not independent review','base':BASE,'final':FINAL,
 'owned_paths':delta,'all_owned_paths_new':True,'final_input_count':1553,'unchanged_old_engineering_inputs':1541,
 'unchanged_old_progress_git_entries':len(old_progress),'progress_proof':'mode/type/blob entries equal; no progress payload reads required',
 'source_map_count':len(maps),'source_bindings':sum(m['count'] for m in maps),'distinct_blobs':len(cache),
 'same_test_pairs':pair_rows,'original_selected8_bindings':schema_bindings,'public_projection_binding':projection_entry,
 'private_original_receipt':{'size':len(raw_receipt),'sha256':sha(raw_receipt),'contents_admission':'EXCLUDED'},
 'source_claim':'Manually checked historical nonexperimental selected8 source summary, full internal refs; not current CLI/binary/runtime/full RPC admission',
 'sole_spec_sha256':SPEC,'final_live_git_all_exact_clean':True}
classifications={
 'interrupt-pair-red-01':'1F: actual missing packaged protocol source; initial complete33 line test',
 'interrupt-pair-green-01':'1F: nested strict typed alias revalidation defect, original first implementation kept',
 'interrupt-pair-green-02':'1P same33 line test: typed models rechecked using wire aliases; raw dict keys remain closed',
 'membership-red-01':'1F1P: AttributeError for assumed observation_count; author also misplaced first-test remainder; not qualifying completed-membership behavior',
 'membership-red-02':'1F1P after author test repair: DID NOT RAISE on actual removed member; whole48 line same-test behavior RED',
 'membership-green-01':'2P same48 line whole-test: complete ordered count/hash supplied-head binding; not authoritative DB history',
 'expanded-focused-01':'3F109P: 2 nonbytes TypeError are implementation deficiencies; valid nested root-array already safely rejected with unsupported_shape, invalid_json oracle was wrong',
 'expanded-focused-02':'3F109P: depth increased but root-array still valid and safely rejected; author incorrect depth-oracle attempt preserved; same2 type deficiencies',
 'expanded-focused-03':'1F111P same whole407 line test: both type deficiencies fixed; aggregate still FAIL because incorrect root-array invalid_json oracle remains',
 'focused-final-01':'118P after correcting only root-array oracle and adding bounded ordinary cases/8-named-seam case; production unchanged from expanded-focused-03',
 'mypy-final-01':'1 import-untyped diagnostic for jsonschema.exceptions; preserved, precise existing-repo import ignore added without dependency/config change',
 'decoder-depth-red-01':'2F118P: root reviewer static candidate confirmed by parser-accepted bounded reply and terminal objects; decoder alias recursion leaked RecursionError without private receipt',
 'decoder-depth-green-01':'120P same whole502 line test; one-line catch adds RecursionError to unsupported_shape; original raw frame/prior exchange preserved, unknown fields remain forbidden',
}
owner={'role':'Implementation owner, not independent review or product rerun','base':BASE,'final':FINAL,
 'source':source_binding,'stage_count':len(stages),'stage_map_count':2*len(stages),'stage_source_bindings':sum(2*r['input_count'] for r in stage_rows),
 'stage_rows':stage_rows,'classifications':classifications,'historical_f81':'118+290 and5static qualified subsets remain original; root depth finding OPEN at f81, not zero-source-finding claim',
 'qualification':{'focused':'120 PASS','related':'290 PASS across six exact files','five_static':'PASS','production':'unregistered/unavailable; main Registry empty/executorNone unchanged',
  'real_cli_model_tool_transport':'NOT_RUN','whole_backend_web_native':'NOT_RUN in this slice','current_environment':'NOT_EXAMINED','whole_M63':'NOT_ACCEPTED','canonical_remote_changes':'NONE'},
 'zero_named_seams':{'scope':'one actual local codec case only, not all gates/fixtures or physical monitor','names':['process','freeze','validity','bootstrap','probe','model_transport','secret_read','sqlite'],
  'counts':[0]*8,'evidence':'named test strict assertions and actual final120PASS'},
 'author_inventory_tool_error':{'classification':'First source-copy tool snippet used RequestId.json instead of schemas/RequestId.json in receipt index, KeyError before any file writes',
  'original_record':'tool stdout only, no fabricated original command/log file; corrected documentary read checked exact prefixed receipt members',
  'not_product_red_or_environment_fact':True}}
summary_by_name={r['stage']:r for r in stage_rows}
assert summary_by_name['decoder-depth-green-01']['summary']=='120 passed in 3.91s'
assert summary_by_name['related-fixed-final-01']['summary'].startswith('290 passed')
report=f'''# M6.3 local interrupt RPC/event pairing — owner candidate

Fixed HEAD `{FINAL}`, base `{BASE}`. Sole PRODUCT_DESIGN v3.0.15 SHA `{SPEC}`. Twelve new paths: two private modules (277/141 lines), 502-line unit test, eight byte-exact schema originals and a nonsecret reviewed projection. All1,541 prior engineering inputs preserve mode/type/blob/size/SHA; final1,553. All prior progress Git entries also match. No canonical/remote changes. This is implementation-owner readback; root independent review is separate.

## Implemented local behavior

`read_interrupt_source/verify_interrupt_source` bind original selected9 plus eight additional historical nonexperimental originals (473,257 bytes/655 complete internalrefs). Full ClientRequest/ServerNotification closures contain the actual turn/interrupt and turn/completed method-to-params branches. Source-summary is a1,833-byte versioned manually checked historical source projection, SHA9bbb226ad6cf51c1d5fee39beb389ba37d5438d0722cd308c642bdc0fd0cf9c9. The original55,893-byte receipt, physical paths/argv, stays private and excluded. Runtime reads verify these selected bytes/summary, not the entire original receipt/current CLI or all314 historical files.

`prepare_interrupt` checks a complete locally supplied id/method/params request. `observe_interrupt` preserves original raw request and bounded1..16,384-byte incoming raw frames, each with exact SHA. Integer IDs require actual int64 literals, bool/float/coercion rejected; string and integer IDs never compare equal by convenience. Empty result ACK pairs only to the original request ID. Terminal notification pairs exact thread and turn; known terminal status is kept separately from the ACK. Either order is admitted without inventing upstream timing guarantees. Received order is preserved. A count/hash binds the complete locally supplied observation membership so a deleted/reordered member is detected relative to that original in-memory head; it is not an authoritative persistent owner head.

This finite decoder supports only empty items and absent/null error, the actual three terminal statuses and optional int64 timing/actual itemsView enum. Nonempty items, TurnError objects, inProgress, unknown/nested fields, methods, RPC errors, mismatched binding and duplicate observations are rejected. There is no trace/jsonrpc-version compatibility guessing. Optional missing facts are not fabricated real receipts; empty/notLoaded items never proves no persisted files or items. A rejected bounded frame returns a private safe-reason receipt and unchanged prior exchange. Empty/nonbytes/overbound inputs are not admitted as complete frames and are not truncated. Bad packaged source/state reads failclosed without repair.

All models retain strictfalse/unregistered and scope locally_supplied_frames_only. An ACK proves only a local checked control reply; a terminal notification is only an observed upstream shape. Neither proves actual dispatch, owned live process, process/child shutdown, stable files, unique local Job terminal, charges or a usable manifest. Module has no SessionIdentity/owner SQL/Job/Run/Provider registration or send action. Main ProofRegistry empty and executorNone, HTTP/routes/54core/0001/bootstrap/v4/oldACK/oldcatalog/schema/dependency/CI bytes remain unchanged. §20.17.5/.7/.8/.9 authorizes this internal representation; no new normative or HTTP contract.

## Original failures and precise qualification

Initialce064 complete33-line test1FAIL at missing package; first723 implementation still1FAIL on typed nested aliases. ef048 uses typed wire-alias conversion and the same complete33-line test1PASS, raw JSON dict Python aliases stay forbidden. Original240 membership test assumed a field and was incorrectly placed in the first function:1F1P AttributeError, not proof that actual deletion was rejected. The author repaired the test without changing production; afcd whole48-line test then truly1F1P DID NOT RAISE after removing a member. e8fd same48-line test2P after complete count/hash binding.

Expandedfec1 and797 each3F109P: two nonbytes inputs leaked TypeError; the third is an author oracle mistake, because a valid deep root array was already rejected as unsupported_shape. Increasing its depth did not establish a parser defect. 046 same complete407-line test fixes the two TypeErrors, but remains aggregate1F111P due that oracle. 589 changes the oracle to either supported safe classification and adds source/named-seam cases;118P. RecursionError parser handling is defensive, not established by those array cases. mypy589 original1 import-untyped diagnostic is preserved; precise existing-pattern ignore added, no package/config relaxation.

Root review off81 found a different gap: parser-accepted bounded root object could overflow recursive typed-alias conversion before rejection. This is not closed by the root-array test. f134 new test-only keeps actual parsed reply/terminal object inputs bounded (<16,384 bytes), no globalrecursionlimit changes; actual2FAIL118PASS RecursionError leaked from decoder. Fixed68a changes only one production except line to include RecursionError. The same full502-line test now120PASS; exact raw offending bytes/hash and old ACK/membership remain preserved, all unknown fields still forbidden. f81 original7gates remain immutable historical qualified subsets with the depth finding OPEN there; no retrospective zero-finding statement. Root independent closure for68a is pending.

Fixed68a actual seven gates (full1,553 Git before/after exact each):

| gate | actual terminal | scope |
|---|---|---|
| decoder-depth-green-01 |120PASS, pytest3.91s/wrapper4.1076s | full new unit, same502-line red/green file |
| related-fixed-final-01 |{summary_by_name['related-fixed-final-01']['summary']} | six exact files: selected9catalog, v4 HTTP/SQLite preparation, Provider synthetic profile, CodexDTO, old interrupt boundaries and HTTP |
| ruff-fixed-final-01 |exit/wrapper0 | ruff check . whole project invocation |
| mypy-fixed-final-01 |exit/wrapper0 | configured noarg mypy,292 sourcefiles |
| spec-fixed-final-01 |exit/wrapper0 | M0 structural checker only, not product acceptance |
| generated-fixed-final-01 |exit/wrapper0 | checked82 artifacts, existing generated bytes unchanged |
| diff-fixed-final-01 |exit/wrapper0 | base27f→HEAD diff --check |

One explicit unit actually fences/asserts8named seams zero: process, bootstrap freeze/validity/execute, capabilityprobe, model-transport, FileSecretStore.read and SQLite.connect. It only qualifies that local source/read/pair/reject case; not a host monitor, all fixtures or related synthetic setup. Root-object recursion counters are also pure memory, no subprocess/secret/SQLite/bootstrap/model/network. UV frozenoffline local37 dependencies were installed as tooling setup, not a product or environment gate. No complete backend/Web/native/realCLI/model/tool run is borrowed.

## Evidence and remaining gaps

{len(maps)} complete fixed Git source maps/{sum(m['count'] for m in maps)} bindings/{len(cache)} distinct blobs; {len(stages)} actual stages/{2*len(stages)} original before/after maps/{sum(2*r['input_count'] for r in stage_rows)} bindings. All original command/runner/receipt/log size/SHA/Git inputs checked. Four exact whole-test pairs are explicit; the frame-type pair closes only the two real defects while the old aggregate remains FAIL. Initial inventory KeyError was author receipt-path indexing error, only tool stdout recorded, no fake original file.

Safe sharing admits only exact listed text candidates plus two outermetadata. Transformations are identity or literal~→~ prefix only, with both raw/candidate size/SHA. All ordinary original logs are preserved; the292,734-byte recursion trace has5,879 lines/53 distinct lines, all distinct content reviewed plus full-byte bounded scan, only repeated static source frames omitted from review display, not from the admitted original. No DB/profile/runtime/secret/private original receipt admission. Owner sealing is not independent review.

Complete ThreadItem/TurnError/RPC-error/callback/approval decoding, live owner/transport mapping, initialization/resume, framing/timing, full hidden-request InputProof and real runtime/resource qualification remain unimplemented or NOT_RUN. This offline slice is not a production turn profile. Current environment capability is NOT_EXAMINED; no aborted historical host probe implies any ENV conclusion. Production stays unavailable, wholeM6.3 NOT_ACCEPTED. Root must independently review the fixed source/evidence before any normal integration; owner did not merge/push.
'''
SEAL.mkdir();CAND=SEAL/'publication-candidates';CAND.mkdir();entries=[]
def put(name,raw,origin):
 text=raw.decode('utf-8');candidate=text.replace('~','~').encode()
 transformation='identity' if candidate==raw else 'literal_homeprefix_only'
 p=CAND/name;p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_bytes(candidate)
 assert p.read_bytes()==candidate
 entries.append({'candidate_path':name,'raw_size':len(raw),'raw_sha256':sha(raw),'candidate_size':len(candidate),'candidate_sha256':sha(candidate),
  'transformation':transformation,'origin':origin})
for stage in stages:
 for name in ['command.json','receipt.json','before.json','after.json','run.log']:
  put(stage+'/'+name,(ROOT/stage/name).read_bytes(),{'type':'original_actual_fixed_gate','raw_relative_path':stage+'/'+name})
for path in delta:put('source/'+path,cache[new[path]['blob']],{'type':'immutable_Git_blob','head':FINAL,**new[path]})
for row in pair_rows:put('source-original-tests/'+row['name']+'.py',cache[row['binding']['blob']],{'type':'exact_whole_test_pair',**row})
put('REPORT.md',report.encode(),{'type':'new_owner_documentary_report'})
put('SCOPE_REPORT.md',(ROOT/'SCOPE_REPORT.md').read_bytes(),{'type':'original_preliminary_scope_not_final_qualification'})
put('SOURCE_BINDING.json',js(source_binding),{'type':'new_documentary_fullGit_source_origin_readback'})
put('FULL_GIT_INPUTS.json',js({'maps':maps,'total_bindings':sum(m['count'] for m in maps),'distinct_blobs':len(cache)}),{'type':'new_full_fixed_Git_maps'})
put('OWNER_GATE_READBACK.json',js(owner),{'type':'new_owner_actual_gates_readback'})
put('run_stage.py',(ROOT/'run_stage.py').read_bytes(),{'type':'original_actual_fixed_gate_runner','sha256':runner_sha})
put('seal_interrupt.py',Path(__file__).read_bytes(),{'type':'new_owner_documentary_seal_script'})
patterns={'provider_key_shape':rb'\bsk-[A-Za-z0-9_-]{16,}','private_key':rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----','actual_cookie_line':rb'(?im)^(?:set-cookie|cookie):\s*\S+'}
hits=[]
for e in entries:
 raw=(CAND/e['candidate_path']).read_bytes()
 for label,pattern in patterns.items():
  if re.search(pattern,raw):hits.append({'path':e['candidate_path'],'label':label})
assert not hits,hits
log_lines=(ROOT/'decoder-depth-red-01/run.log').read_text().splitlines()
assert len(log_lines)==5879 and len(set(log_lines))==53
content={'role':'Owner finite content assessment, root independent admission pending','all_original_logs':'Ordinary source assertions/revalidation diagnostics/summaries, static synthetic IDs only. All complete short logs read; depth-red repeated292734B traceback has5879lines/53distinct lines all read after lossless set-of-lines display; full original remains admitted except homeprefix replacement',
 'source':'two internal pure codecs/models, synthetic unit and eight offline originals; no actual runtime/business JSON or original receipt argv',
 'docs_maps_scripts':'finite source metadata, documentary claims and helpers only','bounded_scanner_patterns':list(patterns),'hits':hits,
 'transformations':['identity','literal_homeprefix_only'],'limits':'Not blanket DLP/host security assurance or permission to read excluded runtime'}
put('CANDIDATE_CONTENT_REVIEW.json',js(content),{'type':'new_owner_content_assessment'})
manifest={'scope':'Only listed publication-candidates and2outermetadata are allowed, no recursive private runtime','base':BASE,'final':FINAL,'candidate_base':str(CAND),
 'candidate_count':len(entries),'entries':entries,'outer_metadata':['SAFE_CANDIDATES.json','READBACK.json'],
 'excluded':'all unlisted files; private historical receipt raw contents/CLI argv; DB/ZIP/profile/secret/runtime/temp; no real CLI/model/tool execution'}
(SEAL/'SAFE_CANDIDATES.json').write_bytes(js(manifest))
readback={'role':'Implementation owner exact seal/source/gate verification, not independent review/rerun','base':BASE,'final':FINAL,'candidate_count':len(entries),
 'candidate_total_bytes':sum(e['candidate_size'] for e in entries),'all_size_sha_transformations_exact':True,'transformation_counts':dict(Counter(e['transformation'] for e in entries)),
 'manifest_sha256':sha((SEAL/'SAFE_CANDIDATES.json').read_bytes()),'report_sha256':sha((CAND/'REPORT.md').read_bytes()),
 'source_maps':len(maps),'source_bindings':sum(m['count'] for m in maps),'distinct_blobs':len(cache),'stage_maps':len(stages)*2,'stage_bindings':sum(2*r['input_count'] for r in stage_rows),
 'old_engineering_inputs_preserved':1541,'final_live_Git_exact_clean':True,'raw_receipt_admission':'EXCLUDED, manually reviewed projection only',
 'production':'unregistered/unavailable','real_cli_model':'NOT_RUN','whole_M63':'NOT_ACCEPTED','canonical_remote':'NONE','root_independent_review':'pending'}
(SEAL/'READBACK.json').write_bytes(js(readback))
for e in entries:
 raw=(CAND/e['candidate_path']).read_bytes();assert len(raw)==e['candidate_size'] and sha(raw)==e['candidate_sha256']
assert git('rev-parse','HEAD').decode().strip()==FINAL and git('status','--porcelain','--untracked-files=all')==b''
print(json.dumps({'seal':str(SEAL),'candidate_count':len(entries),'manifest_sha256':sha((SEAL/'SAFE_CANDIDATES.json').read_bytes()),
 'readback_sha256':sha((SEAL/'READBACK.json').read_bytes()),'report_sha256':sha((CAND/'REPORT.md').read_bytes()),'source_maps':len(maps),'source_bindings':sum(m['count'] for m in maps),
 'stage_maps':len(stages)*2,'stage_bindings':sum(2*r['input_count'] for r in stage_rows),'distinct_blobs':len(cache)}))
