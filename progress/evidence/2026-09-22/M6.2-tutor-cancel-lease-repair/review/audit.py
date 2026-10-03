from pathlib import Path
import json,hashlib,subprocess,datetime
base=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance'); tree=base/'m62-tutor-cancel-lease-active'; raw=base/'m62-tutor-cancel-lease-diagnosis-v1'; out=Path(__file__).resolve().parent
BASE_COMMIT='acb9e220deeaf1da7ee89ec6fda8bae9c21ca918'
def sha(b):return hashlib.sha256(b).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def pin(p):
 b=p.read_bytes();return {'path':str(p.relative_to(base)),'bytes':len(b),'sha256':sha(b)}
def git(*args):return subprocess.check_output(['git',*args],cwd=tree)
status=git('status','--porcelain').decode();assert status==''
head=git('rev-parse','HEAD').decode().strip();assert head=='7442033e4952645bd26332b25b70c23fa94af89b'
assert git('rev-parse','HEAD^').decode().strip()==BASE_COMMIT
patch=git('diff',BASE_COMMIT,head,'--','tests/integration/test_tutor_runs.py');(out/'reviewed.patch').write_bytes(patch)
assert git('diff','--numstat',BASE_COMMIT,head).decode()=='45\t1\ttests/integration/test_tutor_runs.py\n'
initial=json.loads((raw/'initial-pins.json').read_bytes());binding=json.loads((raw/'checkout-source-comparison.json').read_bytes()); assert binding['same_scoped_sources']
checks=[];paths={x['path'] for x in initial['source']}
for entry in initial['source']:
 p=entry['path'];old=git('show',BASE_COMMIT+':'+p);ci=git('show',binding['ci_actual_checkout']+':'+p)
 assert old==ci and sha(old)==entry['sha256'] and len(old)==entry['bytes']
 assert (raw/'source'/p).read_bytes()==old
 checks.append({'path':p,'acb_sha256':sha(old),'ci_sha256':sha(ci),'exact_git_equal':True})
receipts=[];rawpins=[];maps=[]
for folder in sorted(raw.glob('0*')):
 if not folder.is_dir():continue
 receipt=json.loads((folder/'receipt.json').read_bytes()); log=(folder/'test.log').read_bytes(); before=json.loads((folder/'inputs-before.json').read_bytes()); after=json.loads((folder/'inputs-after.json').read_bytes())
 assert len(before)==954 and before==after and receipt['source_count']==954 and receipt['source_unchanged']
 assert sha(log)==receipt['log_sha256'] and len(log)==receipt['log_bytes'] and receipt['head']==BASE_COMMIT and not receipt['timeout']
 assert sha((folder/'runner.py').read_bytes())==receipt['runner_sha256']
 assert sha((folder/'lease_probe.py').read_bytes())==receipt['probe_sha256']
 bm={x['path']:x for x in before}; snapshots=[]
 for p in sorted((folder/'source').rglob('*')):
  if not p.is_file():continue
  relative=str(p.relative_to(folder/'source')); data=p.read_bytes(); assert sha(data)==bm[relative]['sha256'] and len(data)==bm[relative]['bytes']
  paths.add(relative);snapshots.append(relative);rawpins.append(pin(p))
 for name in ['receipt.json','test.log','inputs-before.json','inputs-after.json','runner.py','lease_probe.py','probe-facts.json']:
  p=folder/name
  if p.exists():rawpins.append(pin(p))
 receipts.append({'stage':folder.name,'exit_code':receipt['exit_code'],'terminal_summary':log.decode().splitlines()[-1],'log_sha256':sha(log),'log_bytes':len(log),'source_count':954,'before_after_equal':True,'snapshots_verified':snapshots,'uses_probe_plugin':'-p' in receipt['command']})
 maps.append(bm)
assert maps[0]==maps[1]
assert all(m==maps[2] for m in maps[3:])
changed=[p for p in maps[0] if maps[0][p]!=maps[2][p]];assert changed==['tests/integration/test_tutor_runs.py']
for p in maps[2]:
 b=(tree/p).read_bytes();assert sha(b)==maps[2][p]['sha256'] and len(b)==maps[2][p]['bytes']
sourcepins=[]
for relative in sorted(paths):
 p=tree/relative;b=p.read_bytes();target=out/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
 assert b==git('show',head+':'+relative)
 sourcepins.append({'path':relative,'bytes':len(b),'sha256':sha(b),'same_as_base_git':b==git('show',BASE_COMMIT+':'+relative),'same_as_final_git':True})
for name in ['initial-pins.json','checkout-source-comparison.json','original-failure-facts.json','lease_probe.py','toolchain-link-receipt.json']:
 rawpins.append(pin(raw/name))
for kind in ['ci','local']:
 for name in ['receipt.json','test.log']:rawpins.append(pin(raw/'originals'/kind/name))
 oldlog=(raw/'originals'/kind/'test.log').read_bytes(); original=next(x for x in initial['logs'] if x['kind']==kind);assert sha(oldlog)==original['sha256'] and len(oldlog)==original['bytes'];assert sha((raw/'originals'/kind/'receipt.json').read_bytes())==original['receipt_sha256']
ci=(raw/'originals/ci/test.log').read_text();assert '[command]/usr/bin/git log -1 --format=%H' in ci and binding['ci_actual_checkout'] in ci
for stage in ['02-controlled-renew-red','03-controlled-renew-green']:
 v=json.loads((raw/stage/'probe-facts.json').read_bytes());assert v['actual_watch_called'] and not v['cancel_requested_before'] and v['same_owner'] and v['same_job_revision'] and v['scheduled_before_service_cancel_transaction'] and v['lease_until_after_watch']>v['lease_until_before']
assert git('status','--porcelain').decode()==status
assert all(sha((tree/v['path']).read_bytes())==v['sha256'] for v in sourcepins)
dump(out/'source-pins.json',{'base':BASE_COMMIT,'head':head,'status':status,'patch_sha256':sha(patch),'files':sourcepins,'before_after_stable':True})
dump(out/'evidence-audit.json',{'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base':BASE_COMMIT,'final_head':head,'actual_ci_checkout':binding['ci_actual_checkout'],'production_diff_files':0,'test_diff_files':1,'changed_lines':{'added':45,'removed':1},'scoped_git_comparisons':checks,'run_receipts':receipts,'old_to_new_source_difference':changed,'final_current_source_checks':954,'final_maps_identical_stages':'03 through 07','scope':'Independent stdlib read-only artifact/source review; no product tests, network or archived runner execution.'})
dump(out/'raw-input-pins.json',{'files':rawpins,'count':len(rawpins),'exclusions':['private-pytest-tmp','runtime database','profiles','secret store','user keys']})
print(json.dumps({'cache':str(out),'source_files':len(sourcepins),'raw_aliases_pinned':len(rawpins),'runs':len(receipts),'production_diff':0,'status':'PASS'}))
