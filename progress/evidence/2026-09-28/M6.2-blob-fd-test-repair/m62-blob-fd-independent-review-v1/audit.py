from pathlib import Path
import datetime,hashlib,json,subprocess
base=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance');tree=base/'m62-blob-fd-diagnosis-active';out=Path(__file__).resolve().parent
sha=lambda x:hashlib.sha256(x).hexdigest();head='d1bc330611bc5a315957c07f8d3cee266a5a13e8';parent='72e4e64ce0e97b444146fe237efee9f199da16dc'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=tree).decode().strip()==head
assert subprocess.check_output(['git','rev-parse','HEAD^'],cwd=tree).decode().strip()==parent
assert subprocess.check_output(['git','status','--porcelain'],cwd=tree)==b''
changed=subprocess.check_output(['git','diff-tree','--no-commit-id','--name-only','-r',head],cwd=tree).decode().splitlines();assert set(changed)=={'tests/unit/test_content_store.py','tests/blob_fd_probe.py'}
sourcepaths=['tests/unit/test_content_store.py','tests/blob_fd_probe.py','services/api/app/infrastructure/blobs.py','services/api/app/application/errors.py','pyproject.toml','AGENTS.md']
sources=[]
for name in sourcepaths:
 data=subprocess.check_output(['git','show',head+':'+name],cwd=tree);assert data==(tree/name).read_bytes();p=out/'source'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 sources.append({'path':name,'bytes':len(data),'sha256':sha(data),'git_blob':subprocess.check_output(['git','rev-parse',head+':'+name],cwd=tree).decode().strip()})
for name in ['services/api/app/infrastructure/blobs.py','services/api/app/application/errors.py']:
 assert subprocess.check_output(['git','show',parent+':'+name],cwd=tree)==(tree/name).read_bytes()
orig=subprocess.check_output(['git','show',parent+':tests/unit/test_content_store.py'],cwd=tree);(out/'original-test_content_store.py').write_bytes(orig)
(out/'changes.patch').write_bytes(subprocess.check_output(['git','diff',parent,head],cwd=tree))
pins=[];runs=[]
for name,folder,count,commit in [('original-full',base/'m62-review-storage-final-gates-v1/python',964,parent),('controlled-red',base/'m62-blob-fd-diagnosis-v1/controlled-red',964,parent),('final-focused',base/'m62-blob-fd-diagnosis-v1/python',965,head),('ruff',base/'m62-blob-fd-diagnosis-v1/ruff',965,head)]:
 receipt=json.loads((folder/'receipt.json').read_text());log=(folder/'test.log').read_bytes();before=json.loads((folder/'inputs-before.json').read_text());after=json.loads((folder/'inputs-after.json').read_text())
 assert sha(log)==receipt['log_sha256'] and len(log)==receipt['log_bytes'] and receipt['code_commit']==commit
 assert before==after and len(before)==count and receipt['source_unchanged'] and all(x['git_matches'] for x in before)
 for row in before:
  data=subprocess.check_output(['git','cat-file','blob',row['git_blob_sha1']],cwd=tree)
  assert sha(data)==row['sha256'] and len(data)==row['bytes']
  assert subprocess.check_output(['git','rev-parse',commit+':'+row['path']],cwd=tree).decode().strip()==row['git_blob_sha1']
 for f in ['receipt.json','test.log','inputs-before.json','inputs-after.json']:
  path=folder/f;b=path.read_bytes();pins.append({'path':str(path.relative_to(base)),'bytes':len(b),'sha256':sha(b)})
 runs.append({'name':name,'commit':commit,'source_count':count,'git_bindings_checked':count,'exit_code':receipt['exit_code'],'log_sha256':sha(log),'last_line':log.decode().splitlines()[-1]})
for file in ['fd_probe.py','run-probe.py','run-final.py']:
 p=base/'m62-blob-fd-diagnosis-v1'/file;b=p.read_bytes();pins.append({'path':str(p.relative_to(base)),'bytes':len(b),'sha256':sha(b)})
(out/'source-pins.json').write_text(json.dumps({'head':head,'base':parent,'changed_files':changed,'files':sources,'original_test_sha256':sha(orig),'spec_sha256':sha((tree/'PRODUCT_DESIGN.md').read_bytes())},indent=2)+'\n')
(out/'raw-pins.json').write_text(json.dumps({'files':pins},indent=2)+'\n')
(out/'evidence-audit.json').write_text(json.dumps({'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runs':runs,'production_changes':0,'additional_test_runs':'NOT_RUN','external_injector_boundary':'controlled-red tracked input list excludes the cache fd_probe.py and run-probe.py; their current original bytes are separately pinned, not claimed as in-run snapshots.','source_clean':True},indent=2)+'\n')
print(json.dumps({'raw_pins':len(pins),'source_pins':len(sources),'runs':runs},indent=2))
