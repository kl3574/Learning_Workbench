from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,subprocess
base=Path(__file__).resolve().parent
bare=base.parent/'m62-import-publication-ui-main-history-bare.git'
public=base.parent/'m62-import-publication-ui-public-v1/public'
main='4a5c6de3b74fdc1659389326c746e05ef19ff00b'
private='fa71351e7d6b9358d4b0ef2f46184999f84e5e08'
started=datetime.now(timezone.utc).isoformat();commands=[]
original=(base/'run.log').read_bytes()
assert original.count(b'COMMAND ')==3 and original.endswith(b'EXIT 1\n')
(base/'FIRST_ATTEMPT.json').write_text(json.dumps({'status':'FAIL','scope':'Packaging driver only; no product tests.','reason':'Initial driver expected cat-file -e missing-object exit128; actual Git returned1. The original init/fetch/log/script are retained, no second fetch or object mutation. Stable batch-check protocol is used next.','actual_missing_probe_exit':1,'incorrect_expected_exit':128,'original_log_sha256':hashlib.sha256(original).hexdigest()},indent=2)+'\n')
with (base/'finish.log').open('wb') as stream:
 def run(args,data=None):
  stream.write(('COMMAND '+json.dumps(args)+'\n').encode());stream.flush()
  result=subprocess.run(args,input=data,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  stream.write(result.stdout);stream.write(('EXIT '+str(result.returncode)+'\n').encode());stream.flush()
  commands.append({'argv':args,'stdin_sha256':hashlib.sha256(data).hexdigest() if data else None,'exit_code':result.returncode,'output_sha256':hashlib.sha256(result.stdout).hexdigest()})
  assert result.returncode==0,(args,result.returncode)
  return result.stdout
 probe=run(['git','-C',str(bare),'cat-file','--batch-check'],(private+'\n').encode())
 assert probe==(private+' missing\n').encode()
 refs=run(['git','-C',str(bare),'show-ref']).decode().splitlines();assert refs==[main+' refs/heads/main']
 output=run(['python',str(public/'verify.py'),'--source-repo',str(bare),'--public-main',main])
 verification=json.loads(output);assert verification['status']=='PASS' and verification['public_main_verified']==main
 (base/'VERIFIER_OUTPUT.json').write_bytes(output)
plan=json.loads((public/'source-reconstruction-plan.json').read_bytes())
ids=sorted({r['git_blob'] for r in plan['inputs']})
result=subprocess.run(['git','-C',str(bare),'cat-file','--batch'],input=('\n'.join(ids)+'\n').encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
body=result.stdout;cursor=0;blobs={}
for oid in ids:
 end=body.index(b'\n',cursor);header=body[cursor:end].decode().split();size=int(header[2]);data=body[end+1:end+1+size];cursor=end+2+size
 assert header[0]==oid and header[1]=='blob' and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+data).hexdigest()==oid
 blobs[oid]=data
assert cursor==len(body)
for row in plan['inputs']:
 data=blobs[row['git_blob']];assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
receipt={'scope':'Same initially empty bare; only exact local main history fetched once. Private fa713 Git object absent by exact batch-check response. Local main-only portability, not remote publication proof.','started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'main':main,'private_candidate':private,'private_object_absent':True,'refs':refs,'commands':commands,'public_manifest_sha256':hashlib.sha256((public/'manifest.json').read_bytes()).hexdigest(),'verifier_sha256':hashlib.sha256((public/'verify.py').read_bytes()).hexdigest(),'log_sha256':hashlib.sha256((base/'finish.log').read_bytes()).hexdigest(),'full_git_blob_check':{'input_records':len(plan['inputs']),'unique_actual_git_blobs':len(ids),'bytes_and_sha256_all_matched':True,'batch_output_sha256':hashlib.sha256(body).hexdigest(),'source_plan_sha256':hashlib.sha256((public/'source-reconstruction-plan.json').read_bytes()).hexdigest()},'first_attempt':'FAIL retained in FIRST_ATTEMPT.json/run.log/run.py; only missing-object exit assumption corrected','result':'PASS','network_remote_access':False,'product_tests_run':False}
(base/'TASK_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
(base/'REPORT.md').write_text('An initially empty bare repository fetched only local integrated main 4a5c6de3b74fdc1659389326c746e05ef19ff00b once with no tags. Its only ref is main. Exact git batch-check proves private fa71351e7d6b9358d4b0ef2f46184999f84e5e08 object missing. Public verifier --public-main validates all22 stage declarations; actual cat-file bytes/size/SHA256 additionally match all847 final inputs (843 main,4 ce42 ancestor). Stage15–18 is846 excluding later ADR. No remote access or product test was executed. Initial packaging driver FAIL is retained: missing-object cat-file -e returned1 instead of assumed128; this was a harness exit-code assumption, not a source mismatch. Continued in the same unchanged bare using explicit missing protocol, no refetch. The verified public package manifest is recorded in the receipt; this is localmain-only portability, not remote publication.\n')
rows=[]
for p in sorted(base.rglob('*')):
 if p.is_file() and p.name!='MANIFEST.json':
  data=p.read_bytes();rows.append({'path':str(p.relative_to(base)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(base/'MANIFEST.json').write_text(json.dumps({'members':rows},indent=2)+'\n')
print(json.dumps({'status':'PASS','main':main,'private_object_absent':True,'refs':refs,'all_input_sha256_checked':847,'stages':len(verification['stage_coverage']),'members':len(rows),'manifest_sha256':hashlib.sha256((base/'MANIFEST.json').read_bytes()).hexdigest()}))
