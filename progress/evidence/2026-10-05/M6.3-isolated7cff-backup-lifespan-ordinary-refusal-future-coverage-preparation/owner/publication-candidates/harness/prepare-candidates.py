"""Explicit reviewed text candidates; private fixture runtimes are never copied."""
from pathlib import Path
import hashlib,json,os,datetime,subprocess
os.umask(0o077)
e=Path(__file__).resolve().parent;s=e/'seal-7cff';dest=s/'publication-candidates';dest.mkdir(mode=0o700)
r=e.parent/'m63-codex-restore-lifespan-oct05'
sha=lambda b:hashlib.sha256(b).hexdigest()
binding=json.loads((s/'SOURCE_BINDINGS.json').read_text())
stages=['focused-01','static-01','diff-01','focused-02','static-02','diff-02','related-01']
(s/'expectation-correction.patch').write_bytes(subprocess.check_output(['git','diff','816cb38b7285d14fdbf5d00fcdecdced5e1b517d',binding['head'],'--','tests/integration/test_backup_codex_lifespan.py'],cwd=r))
choices=[]
def add(path,label=None):choices.append((path,label or str(path.relative_to(e))))
for name in ['REPORT.md','SOURCE_BINDINGS.json','STAGE_HISTORY.json','ORIGINAL_FAILURE_SUMMARY.json','owned.patch','expectation-correction.patch']:add(s/name,name)
for h in binding['git_heads']:add(s/'git'/f'{h}.json','git/'+h+'.json')
for p in binding['changed_paths']:add(s/'source'/p,'source/'+p)
add(e/'focused-01/test_backup_codex_lifespan.py','original-source/816-test_backup_codex_lifespan.py')
for name in ['run.py','seal-evidence.py','prepare-candidates.py']:add(e/name,'harness/'+name)
for stage in stages:
 for name in ['command.json','receipt.json','source-before.json','source-after.json']:add(e/stage/name,'stages/'+stage+'/'+name)
for stage in ['focused-02','related-01','static-02','diff-02']:add(e/stage/'run.log','logs/'+stage+'.log')
add(e/'READONLY_FAILURE_PROJECTION.json','observations/readonly-first-failure-projection.json')
for stage in ['focused-02','related-01']:
 for index in [0,1]:
  path=e/(stage+'-private')/f'codex-lifespan-copy{index}'/'lifespan-observation.json'
  value=json.loads(path.read_text())
  assert value['forbidden_calls']=={'codex_model':0,'ordinary_provider':0,'tool':0,'process':0,'bootstrap':0}
  assert value['entered_lifespan'] and value['contract_assertions_completed'] and value['alive_before_shutdown'] and not value['alive_after_context']
  assert len(value['worker_observations'])>=2
  add(path,f'observations/{stage}-{index}.json')
assert len({label for _,label in choices})==len(choices)
records=[]
for path,label in choices:
 raw=path.read_bytes();raw.decode('utf-8');public=raw.replace(b'${HOME}',b'${HOME}')
 out=dest/label;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(public)
 records.append(dict(raw_path=str(path),candidate_path=label,raw_bytes=len(raw),candidate_bytes=len(public),raw_sha256=sha(raw),candidate_sha256=sha(public),transformation='literal home-prefix-only' if public!=raw else 'identity UTF-8'))
manifest=dict(source_sha=binding['head'],count=len(records),candidate_base=str(dest),created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),allowed_transforms=['identity','literal ${HOME} -> ${HOME}'],exclusions=['raw fixture-repr failure log','all unlisted private runtime files','DB','ZIP','key storage','cache'],files=records)
(s/'SAFE_CANDIDATES.json').write_text(json.dumps(manifest,indent=2)+'\n')
for item in records:
 raw=Path(item['raw_path']).read_bytes();public=(dest/item['candidate_path']).read_bytes()
 assert sha(raw)==item['raw_sha256'] and sha(public)==item['candidate_sha256'] and public==raw.replace(b'${HOME}',b'${HOME}')
assert {str(p.relative_to(dest)) for p in dest.rglob('*') if p.is_file()}=={x['candidate_path'] for x in records}
for receipt in json.loads((s/'STAGE_HISTORY.json').read_text()):assert receipt['runner_sha256']==sha((e/'run.py').read_bytes())
readback=dict(source_sha=binding['head'],candidate_count=len(records),all_candidates_read_back=True,all_raw_sources_read_back=True,runner_hash_matches_all_seven_receipts=True,extra_candidates=[],source_bindings_sha256=sha((s/'SOURCE_BINDINGS.json').read_bytes()),report_sha256=sha((s/'REPORT.md').read_bytes()),safe_manifest_sha256=sha((s/'SAFE_CANDIDATES.json').read_bytes()),boundary='Bounded corrected test oracle. Original 2 FAIL retained. No production fix, full restoration/convergence or M7 acceptance; independent review pending.')
(s/'READBACK.json').write_text(json.dumps(readback,indent=2)+'\n')
print(json.dumps(readback,indent=2))
