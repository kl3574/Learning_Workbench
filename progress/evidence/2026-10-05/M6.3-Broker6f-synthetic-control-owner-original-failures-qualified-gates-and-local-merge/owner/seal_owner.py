"""Bounded owner publication projection; not independent review or a product run."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT=Path(__file__).resolve().parent
TREE=Path('~/.cache/learning-workbench-acceptance/m63-broker-control-owner-oct06')
BASE='68a280b9cf251bbf79c2ca188ac8b4aefe7562e0'
FINAL='6f5de88935c6ff7a79a87cf5440cc47f86fb0d10'
SEAL=ROOT/'seal-6f5'
assert not SEAL.exists()
CAND=SEAL/'publication-candidates'
CAND.mkdir(parents=True)
SPOOL=ROOT/'selected-originals-6f5'
SPOOL.mkdir(exist_ok=False)
def sha(raw): return hashlib.sha256(raw).hexdigest()
def git(*args): return subprocess.check_output(['git','-C',str(TREE),*args])
def dump(data): return (json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode()
def saved(path, data):
 path.parent.mkdir(parents=True,exist_ok=True); assert not path.exists(); path.write_bytes(data)
def selected(name,rawpath,raw):
 assert not (CAND/name).exists()
 candidate=raw.replace(b'~',b'~')
 saved(CAND/name,candidate)
 entries.append({'candidate_path':name,'raw_path':str(rawpath),'raw_size':len(raw),'raw_sha256':sha(raw),
 'candidate_size':len(candidate),'candidate_sha256':sha(candidate),
 'transformation':'literal_home_prefix_to_tilde' if raw!=candidate else 'identity'})
 assert raw==candidate or candidate==raw.replace(b'~',b'~')
 text=candidate.decode('utf-8')
 assert not re.search(r'sk-[A-Za-z0-9]{20,}',text)
 assert '~' not in text

def own(name,data):
 rawpath=SPOOL/name;saved(rawpath,data);selected(name,rawpath,data)
entries=[]
assert git('rev-parse','HEAD').decode().strip()==FINAL
assert not git('status','--porcelain','--untracked-files=all')
heads=[BASE]+git('rev-list','--reverse',BASE+'..'+FINAL).decode().splitlines()
paths=git('diff','--name-only',BASE,FINAL).decode().splitlines()
assert len(paths)==8
maps={};content={};source_bindings=0
for head in heads:
 rows=[]
 for line in git('ls-tree','-r','-z',head).split(b'\0'):
  if not line: continue
  header,pathraw=line.split(b'\t',1);path=pathraw.decode()
  if path.startswith('progress/'): continue
  mode,kind,blob=header.decode().split()
  assert kind=='blob'
  raw=content.setdefault(blob,git('cat-file','blob',blob)) if blob not in content else content[blob]
  if head==FINAL:
   actual=(TREE/path).read_bytes() if mode!='120000' else __import__('os').readlink(TREE/path).encode()
   assert actual==raw
  rows.append({'path':path,'mode':mode,'type':kind,'blob':blob,'size':len(raw),'sha256':sha(raw)})
 maps[head]={'head':head,'tree':git('rev-parse',head+'^{tree}').decode().strip(),'count':len(rows),'entries':rows}
 source_bindings+=len(rows)
 own('git-inputs/'+head+'.json',dump(maps[head]))
assert maps[FINAL]['count']==1558
base={r['path']:r for r in maps[BASE]['entries']};final={r['path']:r for r in maps[FINAL]['entries']}
changed=[path for path in base if path not in final or base[path]!=final[path]]
added=[path for path in final if path not in base]
assert set(changed+added)==set(paths)
progress=lambda head:{line.split(b'\t',1)[1]:line.split(b'\t',1)[0] for line in git('ls-tree','-r','-z',head).split(b'\0') if line and line.split(b'\t',1)[1].startswith(b'progress/')}
assert progress(BASE)==progress(FINAL)
for path in paths:
 own('source/'+path,git('show',FINAL+':'+path))
source_copy_bindings=[{'path':path,'candidate':'source/'+path,**final[path]} for path in paths]
redtest=git('show','938c91ee02d65862a82fff3134398c023c5e1602:tests/integration/test_codex_broker_control_owner.py')
greentest=git('show','7873f9cbc9b4b421cdf0f210c93eee4d22f0fe46:tests/integration/test_codex_broker_control_owner.py')
assert redtest==greentest
own('RED_GREEN_TEST_BINDING.json',dump({'scope':'Exact complete 51-line test file at final test-only RED and first implementation GREEN',
 'red_head':'938c91ee02d65862a82fff3134398c023c5e1602','green_head':'7873f9cbc9b4b421cdf0f210c93eee4d22f0fe46',
 'size':len(redtest),'sha256':sha(redtest),'whole_test_exact':True,
 'prior_unreached_author_corrections':['read_control identity was a string, changed to actual SessionIdentity','Wrong pure-codec observation property names corrected before first GREEN'],
 'first_two_original_failed_runs_preserved':True}))

stages=[];run_bindings=0
for stage in sorted(p.name for p in ROOT.iterdir() if p.is_dir() and (p/'receipt.json').is_file()):
 p=ROOT/stage;receipt=json.loads((p/'receipt.json').read_text());command=json.loads((p/'command.json').read_text())
 before=json.loads((p/'before.json').read_text());after=json.loads((p/'after.json').read_text());log=(p/'run.log').read_bytes()
 assert receipt['head'] in maps and before==after==maps[receipt['head']]
 assert receipt['before_after_complete_exact'] and command['source_head']==receipt['head']
 assert receipt['log_size']==len(log) and receipt['log_sha256']==sha(log)
 run_bindings+=before['count']+after['count']
 for name in ('command.json','receipt.json','before.json','after.json'):
  selected(stage+'/'+name,p/name,(p/name).read_bytes())
 if receipt['command_exit_code']==0:
  selected(stage+'/run.log',p/'run.log',log)
 else:
  assert stage in ('owner-rpc-red-01','owner-rpc-red-02','owner-rpc-red-03')
  lines=log.decode().splitlines()
  chosen=[{'line':i+1,'text':line} for i,line in enumerate(lines) if line.startswith('E ') or line.startswith('FAILED ') or re.match(r'^1 failed,',line)]
  assert any('has no attribute' in row['text'] and 'bind_control_peer' in row['text'] for row in chosen)
  own(stage+'/BOUNDED_FAILURE.json',dump({'original_log_size':len(log),'original_log_sha256':sha(log),
   'scope':'Exact selected error lines only; complete failed log/auth fixture representation remains private and is not admitted',
   'selected_lines':chosen,'actual_business_tests_failed':1}))
 stages.append({'stage':stage,'receipt':receipt,'command':command,'admitted_log':'run.log' if receipt['command_exit_code']==0 else 'BOUNDED_FAILURE.json'})
assert len(stages)==15
final_stages={'expanded-focused-02','related-final-01','ruff-final-01','mypy-final-01','generated-final-01','spec-final-01','diff-final-01'}
assert all(s['receipt']['head']==FINAL and s['receipt']['wrapper_exit_code']==0 for s in stages if s['stage'] in final_stages)
assert sum(s['stage'] in final_stages for s in stages)==7
own('STAGE_HISTORY.json',dump(stages))
own('SOURCE_BINDINGS.json',dump({'fixed_base':BASE,'fixed_final':FINAL,'heads':heads,'git_map_count':len(heads),
 'immutable_git_bindings':source_bindings,'distinct_blob_count':len(content),'original_run_map_pairs':len(stages),
 'original_run_before_after_bindings':run_bindings,'final_live_complete_exact':True,
 'old_nonprogress_entries':len(base),'preserved_old_nonprogress_entries':len(base)-len(changed),'changed_prior_paths':changed,'new_paths':added,
 'all_old_progress_git_entries_exact':True,'source_copies':source_copy_bindings,'no_canonical_or_remote_mutation':True}))
selected('SCOPE.md',ROOT/'SCOPE.md',(ROOT/'SCOPE.md').read_bytes())
selected('run_stage.py',ROOT/'run_stage.py',(ROOT/'run_stage.py').read_bytes())
selected('seal_owner.py',ROOT/'seal_owner.py',(ROOT/'seal_owner.py').read_bytes())
report="""# Broker control owner slice — fixed 6f5

Owner implementation/evidence readback; **not independent review**. Sole normative product document: v3.0.15, SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec. Fixed base 68a280b9cf251bbf79c2ca188ac8b4aefe7562e0; fixed clean final 6f5de88935c6ff7a79a87cf5440cc47f86fb0d10, 1558 complete engineering Git inputs. Eight paths, 902 additions / 5 removals. All old v1–v6 decoders, original ACKs, profiles/default registry, production executor=None, public DTO/routes/HTTP/SSE, original schema catalogs, 54 core, 0001, dependencies and CI remain unchanged except explicit private v7 handling in the existing turn owner. SOURCE_BINDINGS identifies the three touched prior source paths; all other 1550 base engineering inputs and every old progress Git entry remain exact. Canonical and remote were not changed by this owner.

Existing HTTP Jobs cancel and session interrupt now share one caller-transaction Broker request. It only prepares an exact request from durable stop plus a checked live association; no transport in HTTP/SQLite. Only the exact trusted synthetic executor's actual current callback can bind its explicit synthetic turn ID to the checked original Bootstrap thread, original Provider start and Jobs lease. The generated SessionAnchor thread is retained only as a local owner cross-check and never sent upstream. This mapping is **synthetic_peer_only / production_qualified=false**; it has no actual native turn/start original, process/IPC or production turn runtime qualification. Typed schemas and caller strings are not production authorization.

Forward migration 0036 owns immutable records/members and a guarded head. Each original is independently bound into the complete existing turn chain by strict private v7 ordinal/hash. Whole owner reads recheck all records, members, head, versions, hashes, original bootstrap/provider/turn/lease relationships and original stop. Tail, member, head, entire-family and raw damage reject GET and command replay without repair. Broker records do not change Job/Run control, session CAS or public SSE event sequence. Started commits before a possible single pure control request; repeated routes/keys do not send again. Exact bounded arbitrary-byte raw frames use hex, preserving invalid UTF-8/rejections and prior accepted ACKs. An empty reply and a paired terminal frame remain separate facts; neither creates a local Job terminal, manifest, cleanup or usage proof. At most 64 complete batch frames are supported; invalid/overbound batches retain conservative started/unknown facts and do not retry.

The adapter callback explicitly pumps interrupt_once; **automatic background control pumping while an adapter blocks is NOT_RUN / not implemented here**. No production mapping/transport is installed. A new app cannot take over an active original owner/lease. Same callback loss or existing worker inactive-owner + lease-expiry recovery closes private control facts and preserves the existing real Job unknown outcome without resending. Default no mapping creates no Broker dispatch/RPC. Peer tests use real local HTTP handlers/SQLite and a process-free callback, not a real CLI, socket/model/tool operation or host capability probe. TestClient is not used as a lifespan/background convergence proof in these new tests.

Actual evidence (all seven final stages have complete 1558 before/after inputs exact):

| Gate | Actual fixed result | Scope |
| --- | --- | --- |
| expanded-focused-02 | 22 PASS, 2 existing warnings, pytest 68.06s; wrapper 69.551436s | new HTTP/SQLite/owned pure control tests |
| related-final-01 | 473 PASS, 3 existing warnings, pytest 261.35s; wrapper 262.583649s | ten exact protocol/DTO/provider/prepare/dispatch/interrupt/events/operation-coexistence files, original command lists them |
| ruff-final-01 | exit0 | whole project: ruff check . |
| mypy-final-01 | exit0, 295 sources | configured no-argument mypy |
| generated-final-01 | exit0, checked82 | original generated-contract drift check |
| spec-final-01 | exit0, 54 models/147 routes | M0 structure/integrity only, no learning effectiveness |
| diff-final-01 | exit0 | base68a..fixed6f5 whitespace |

The first actual pre-implementation REDs are all preserved: b5/e39/938 each failed at missing worker.bind_control_peer after real prepare/start/worker/peer setup. Two initially unreached author test mistakes (identity string and property names) were corrected before final test-only938. The complete test file at938 and787 first GREEN is byte-identical; first GREEN actual1 PASS. cdd changed callback ownership/lock scheduling and same test passed again. Expanded efd20 PASS / Ruff+mypy PASS remain separate historical subsets; they are not borrowed for the final seven gates. No prior FAIL was overwritten.

The explicit new control phase fenced six named seams (Bootstrap.execute, ProofRegistry.freeze/prepare, SecretStore.read, model transport, operation dispatch) with actual counters all0. Synthetic fixture bootstrap/proof/consent/claim setup is separate and did perform its documented pure setup actions; this is not a claim of zero calls over the entire setup or physical interception. Tests also preserve complete original bootstrap/start/control ACK bytes. Full backend/Web/native/CI for this owner head, real AppServer/model, a production final-input proof/runtime, reliable physical process cleanup and complete M6.3/M7 acceptance are **NOT_RUN**. Production registry/executor remain closed. Missing actual request/model-proof/deployment/IPC inputs are implementation/input gaps, not a new observed environment blocker.

Publication is the exact SAFE_CANDIDATES list only. Three complete failed logs containing fixture/auth representation remain private and excluded; bounded error-line selections plus original whole-log hashes are admitted. Successful original logs, original commands/receipts/full maps, selected immutable source copies, source/version/test bindings, scope and these documentary helpers are admitted. The only transformation is literal local-home prefix normalization, with per-entry original path/size/SHA and candidate size/SHA. No raw runtime/DB/ZIP/browser/profile/secret files or historical offline raw source receipt are admitted. Historical 68a seal and its report/correction remain immutable and separate.
"""
own('REPORT.md',report.encode())
manifest={'version':'owner-explicit-safe-candidates-v1','fixed_head':FINAL,'scope':'Only exact listed candidate files; no private raw failures/runtime/DB/secret data',
 'candidate_base':'publication-candidates','count':len(entries),'total_bytes':sum(e['candidate_size'] for e in entries),
 'entries':entries,'manual_content_review':'All selected source, success logs, bounded failure lines and metadata reviewed by owner; not independent admission',
 'bounded_publication_scan':'UTF-8 plus no literal private home prefix and no sk-like key; not a security audit'}
saved(SEAL/'SAFE_CANDIDATES.json',dump(manifest))
saved(SEAL/'READBACK.json',dump({'fixed_head':FINAL,'safe_manifest_sha256':sha((SEAL/'SAFE_CANDIDATES.json').read_bytes()),
 'candidate_count':len(entries),'candidate_bytes':manifest['total_bytes'],'all_candidate_hashes_recomputed':True,'raw_to_candidate_exact':True,
 'git_maps':len(heads),'git_bindings':source_bindings,'distinct_blobs':len(content),'run_map_pairs':len(stages),'run_before_after_bindings':run_bindings,
 'fixed_final_complete_live_exact':True,'no_product_rerun_by_sealer':True,'independent_review':'PENDING_ROOT'}))
print(json.dumps({'seal':str(SEAL),'candidate_count':len(entries),'candidate_bytes':manifest['total_bytes'],
 'safe_sha256':sha((SEAL/'SAFE_CANDIDATES.json').read_bytes()),'readback_sha256':sha((SEAL/'READBACK.json').read_bytes()),
 'report_sha256':sha((CAND/'REPORT.md').read_bytes()),'git_bindings':source_bindings,'run_bindings':run_bindings}))
