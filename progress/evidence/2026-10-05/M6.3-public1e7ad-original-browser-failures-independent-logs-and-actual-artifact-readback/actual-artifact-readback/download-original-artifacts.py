from pathlib import Path
import json,hashlib,datetime,subprocess,zipfile,io,stat
O=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
records=[]
for rid in [37241154917,37241158099]:
 d=json.loads((O/('run-'+str(rid)+'-artifacts-01.stdout')).read_bytes())
 for a in d['artifacts']:
  aid=a['id'];stem='artifact-'+str(aid)+'-zip-01';argv=['gh','api','repos/kl3574/Learning_Workbench/actions/artifacts/'+str(aid)+'/zip']
  assert not (O/(stem+'-command.json')).exists()
  (O/(stem+'-command.json')).write_text(json.dumps({'argv':argv,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'run_id':rid,'artifact_id':aid,'scope':'Private original fixed CI artifact readback only; ZIP not admitted for public upload'},indent=2)+'\n')
  x=subprocess.run(argv,capture_output=True);(O/(stem+'.zip')).write_bytes(x.stdout);(O/(stem+'.stderr')).write_bytes(x.stderr)
  (O/(stem+'-receipt.json')).write_text(json.dumps({'exit_code':x.returncode,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stdout_size':len(x.stdout),'stdout_sha256':sha(x.stdout),'stderr_sha256':sha(x.stderr)},indent=2)+'\n')
  assert x.returncode==0 and not a['expired'] and len(x.stdout)==a['size_in_bytes'] and 'sha256:'+sha(x.stdout)==a['digest']
  z=zipfile.ZipFile(io.BytesIO(x.stdout));members=z.infolist();assert len(members)<=100 and len({e.filename for e in members})==len(members)
  rows=[];total=0
  for e in members:
   p=Path(e.filename);assert not p.is_absolute() and '..' not in p.parts and not stat.S_ISLNK(e.external_attr>>16)
   assert e.file_size<=20000000;total+=e.file_size;assert total<=50000000
   if e.is_dir():continue
   raw=z.read(e);assert len(raw)==e.file_size
   rows.append({'path':e.filename,'size':len(raw),'sha256':sha(raw)})
  record={'run_id':rid,'artifact_id':aid,'artifact_name':a['name'],'original_zip_size':len(x.stdout),'original_zip_sha256':sha(x.stdout),'actual_API_digest_exact':True,'members':rows,'ZIP_publication':'NOT_ADMITTED','member_content_readback':'AllbytesSHA/inventory only at thisstage; numeric DTO/timing/UI content qualification separate','original_CI_beforeafter_source_maps':'NOT_CAPTURED'}
  (O/(stem+'-READBACK.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');records.append(record)
  print(json.dumps({'run':rid,'artifact':aid,'name':a['name'],'size':len(x.stdout),'members':[(r['path'],r['size']) for r in rows]}))
(O/'ORIGINAL_ARTIFACT_INVENTORY.json').write_text(json.dumps({'records':records,'original_artifact_count':len(records),'actual_models':0,'public_zip_admission':False},ensure_ascii=False,indent=2)+'\n')
