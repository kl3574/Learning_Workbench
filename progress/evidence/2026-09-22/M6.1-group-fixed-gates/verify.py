"""Verify captured fixed-gate evidence only. No archived drivers/tests execute."""
from pathlib import Path, PurePosixPath
import argparse, hashlib, json, re, runpy, subprocess

def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def safe(base,relative):
 p=PurePosixPath(relative);assert not p.is_absolute() and '..' not in p.parts and str(p)==relative
 target=base.joinpath(*p.parts);assert not target.is_symlink() and target.resolve().is_relative_to(base.resolve());return target
def apply(raw,operations,home):
 cursor=0;out=bytearray()
 # Match the original header/field AND the entire captured value span. A kind
 # label, value-like bytes, or a substring of a valid token is insufficient.
 rules={
  'temporary_session':(rb"\blearning_session=([A-Za-z0-9_-]{20,})(?=$|[\s;\"'])",1,rb'[A-Za-z0-9_-]{20,}','<REDACTED_TEMPORARY_SESSION>'),
  'temporary_csrf':(rb"\bx-csrf-token:\s*([0-9a-f]{64})(?=$|[\s;\"'])",1,rb'[0-9a-f]{64}','<REDACTED_TEMPORARY_CSRF>'),
  'temporary_bearer':(rb"\bBearer\s+([A-Za-z0-9._-]{20,})(?=$|[\s;\"'])",1,rb'[A-Za-z0-9._-]{20,}','<REDACTED_TEMPORARY_BEARER>'),
  'explicit_secret_field':(rb"(?:(?P<key_quote>[\"'])(?:csrf_token|session_token|access_token|secret)(?P=key_quote)|\b(?:csrf_token|session_token|access_token|secret))\s*:\s*(?P<value_quote>[\"'])(?P<value>[^\"'\r\n]+)(?P=value_quote)",'value',rb"[^\"'\r\n]+",'<REDACTED_EXPLICIT_SECRET_FIELD>'),
 }
 for op in operations:
  start,end=op['raw_start'],op['raw_end'];assert cursor<=start<end<=len(raw)
  if op['kind']=='fixed_home_prefix':assert home is not None and raw[start:end]==home and op['replacement']=='<HOME>/'
  else:
   assert op['kind'] in rules
   pattern,group,value_format,replacement=rules[op['kind']]
   assert op['replacement']==replacement and re.fullmatch(value_format,raw[start:end],re.I)
   assert any(match.span(group)==(start,end) for match in re.finditer(pattern,raw,re.I)), 'Span does not match its original header/field value'
  out.extend(raw[cursor:start]);out.extend(op['replacement'].encode());cursor=end
 out.extend(raw[cursor:]);return bytes(out)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--raw-base',type=Path);parser.add_argument('--home-prefix');parser.add_argument('--repo',type=Path);args=parser.parse_args()
 root=Path(__file__).resolve().parent;m=json.loads((root/'manifest.json').read_bytes());assert m['format']=='m61-group-fixed-gates-public-v1'
 aliases=m['aliases'];by={r['alias']:r for r in aliases};assert len(by)==len(aliases)==m['raw_alias_count'];assert len({r['raw_relative'] for r in aliases})==len(aliases)
 assert aliases==sorted(aliases,key=lambda r:r['alias']) and sha(canonical(aliases))==m['aliases_aggregate_sha256']
 files=m['public_files'];index={r['path']:r for r in files};assert len(index)==len(files);assert sha(canonical(files))==m['public_files_aggregate_sha256']
 actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()};assert actual==set(index)|{'manifest.json'};assert len(actual)==m['public_file_count']
 for name,row in index.items():
  b=safe(root,name).read_bytes();assert (len(b),sha(b))==(row['bytes'],row['sha256'])
 inspect=runpy.run_path(str(root/'publication_policy.py.txt'),run_name='policy')['inspect']
 for name in actual:
  b=safe(root,name).read_bytes();assert inspect(m['publication_prefix']+'/'+name,b)==[],name
  assert not re.search(rb'/home/[A-Za-z0-9_.-]+',b), 'Generic HOME path, with or without trailing slash'
  if args.home_prefix:assert args.home_prefix.encode().rstrip(b'/') not in b, 'Private bare HOME remains'
  assert not re.search(rb'learning_session=[A-Za-z0-9_-]{20,}|x-csrf-token:\s*[0-9a-f]{64}|Bearer\s+[A-Za-z0-9._-]{20,}',b,re.I),name
 scan=json.loads((root/'publication-scan.json').read_bytes());assert scan['inspected_targets']==sorted(m['publication_prefix']+'/'+p for p in actual) and scan['failures']==[]
 assert scan['policy_sha256']==sha((root/'publication_policy.py.txt').read_bytes())
 raw_count=0
 for row in aliases:
  public=index[row['public_path']];assert (public['bytes'],public['sha256'])==(row['public_bytes'],row['public_sha256']);assert row['transform_count']==len(row['transforms'])
  assert row['raw_bytes']+sum(len(op['replacement'].encode())-(op['raw_end']-op['raw_start']) for op in row['transforms'])==row['public_bytes']
  if not row['transforms']:assert (row['raw_bytes'],row['raw_sha256'])==(row['public_bytes'],row['public_sha256'])
  if args.raw_base:
   b=safe(args.raw_base,row['raw_relative']).read_bytes();assert (len(b),sha(b))==(row['raw_bytes'],row['raw_sha256']);assert apply(b,row['transforms'],args.home_prefix.encode() if args.home_prefix else None)==safe(root,row['public_path']).read_bytes();raw_count+=1
 def read(name):return json.loads(safe(root,by[name]['public_path']).read_bytes())
 def bind(value,field,name):assert value[field]==by[name]['raw_sha256'],(field,name)
 def source(name):
  value=read(name);assert value['count']==len(value['files'])==m['source_count'];assert value['aggregate_sha256']==sha(canonical(value['files']));assert len({r['path'] for r in value['files']})==value['count'];return value
 def git(name):
  value=read(name);assert value['commit']==m['fixed_commit'];assert value['expected_count']==value['actual_count']==len(value['files'])==m['source_count'];assert value['all_match']==all(r['matches'] for r in value['files']);assert all(r['matches']==(r['git_blob']==r['actual_git_blob'] and r['git_mode']==r['actual_mode']) for r in value['files']);return value
 preflight=read('preflight.json');assert preflight['fixed_commit']==m['fixed_commit'] and preflight['source_count']==m['source_count'];assert preflight['ui_top_level_file_count']==44
 gates=[name for name,_ in preflight['commands']];assert gates==['01-ruff','02-mypy','03-python','04-web-lint','05-web-typecheck','06-web-tests','07-web-build','08-spec','09-native']
 summary=json.loads((root/'summary.json').read_bytes());assert [r['gate'] for r in summary['gates']]==gates
 for name,command in preflight['commands']:
  receipt=read(name+'/receipt.json');running=read(name+'/running.json');assert receipt['command']==running['command']==command;assert receipt['fixed_commit']==receipt['git_after']==running['commit']==m['fixed_commit']
  assert receipt['started_at']==running['started_at'] and receipt['finished_at']>=receipt['started_at'];assert receipt['before_count']==receipt['after_count']==m['source_count']
  for filename,field in [('run.log','log_sha256'),('source-before.json','source_before_sha256'),('source-after.json','source_after_sha256'),('git-before.json','git_before_sha256'),('git-after.json','git_after_sha256')]:bind(receipt,field,name+'/'+filename)
  bind(running,'source_before_sha256',name+'/source-before.json')
  for file,digest in receipt['driver_hashes'].items():assert digest==by[file]['raw_sha256']==running['driver_hashes'][file]==preflight['driver_hashes'][file]
  before,after=source(name+'/source-before.json'),source(name+'/source-after.json');gb,ga=git(name+'/git-before.json'),git(name+'/git-after.json')
  assert before['aggregate_sha256']==receipt['before_aggregate']==preflight['source_aggregate'];assert after['aggregate_sha256']==receipt['after_aggregate']
  b={r['path']:r for r in before['files']};a={r['path']:r for r in after['files']};changed=[key for key in sorted(b.keys()|a.keys()) if b.get(key)!=a.get(key)]
  assert changed==receipt['changed_inputs'] and receipt['unchanged']==(not changed);assert receipt['git_match_before']==gb['all_match'] and receipt['git_match_after']==ga['all_match']
  row=next(r for r in summary['gates'] if r['gate']==name)
  for field in ['exit_code','unchanged','git_match_after','changed_inputs','started_at','finished_at']:assert row[field]==receipt[field]
 native=read('09-native/receipt.json');restoration=read('09-native/restoration.json');bsource=source('09-native/source-before.json');asource=source('09-native/source-after.json');bgit=git('09-native/git-before.json')
 for field,name in [('ui_before_manifest_sha256','09-native/ui-before/manifest.json'),('ui_after_manifest_sha256','09-native/ui-after/manifest.json')]:bind(native,field,name)
 bind(restoration,'restoration_driver_sha256','restore-inspected-outputs.py');bind(restoration,'original_guard_driver_sha256','restore.py')
 bind(restoration,'original_native_receipt_sha256','09-native/receipt.json');bind(restoration,'restored_source_sha256','09-native/restored-source.json');bind(restoration,'restored_git_sha256','09-native/restored-git.json')
 assert restoration['fixed_commit']==m['fixed_commit'];assert restoration['original_unchanged']==native['unchanged'] and restoration['original_changed_inputs']==native['changed_inputs'];assert restoration['source_count']==m['source_count'] and restoration['all_sources_match_before_and_fixed_git_after_restoration']
 assert source('09-native/restored-source.json')==bsource and git('09-native/restored-git.json')['all_match']
 assert sorted(r['path'] for r in restoration['restored'])==native['changed_inputs']
 bs={r['path']:r for r in bsource['files']};as_={r['path']:r for r in asource['files']};gs={r['path']:r for r in bgit['files']}
 for r in restoration['restored']:assert r['before_sha256']==r['restored_sha256']==bs[r['path']]['sha256'] and r['after_sha256']==as_[r['path']]['sha256']
 metrics_before=read('09-native/ui-before/m1-native-zoom-metrics.json');metrics_after=read('09-native/ui-after/m1-native-zoom-metrics.json')
 assert metrics_before['browser']=='153.0.8010.36' and metrics_after['browser']=='153.0.8010.52'
 assert {k:v for k,v in metrics_before.items() if k!='browser'}=={k:v for k,v in metrics_after.items() if k!='browser'}
 assert len(native['changed_inputs'])==5 and set(native['changed_inputs'])=={'docs/ui/m1-after-1440.png','docs/ui/m1-after-1920.png','docs/ui/m1-after-390-agent.png','docs/ui/m1-native-zoom-metrics.json','docs/ui/m1-session-three-way-conflict.png'}
 # Summary facts remain direct projections of actual original log/artifact data.
 results=summary['actual_results']
 def log(name):return safe(root,by[name]['public_path']).read_text()
 assert results['python_terminal_line'] in log('03-python/run.log')
 assert results['python_environment_skip']==[line for line in log('03-python/run.log').splitlines() if line.startswith('SKIPPED ')]
 assert all(line in log('06-web-tests/run.log') for line in results['web_terminal_lines'])
 assert results['mypy_terminal_line']==log('02-mypy/run.log').strip()
 assert results['native_terminal_line'] in log('09-native/run.log')
 assert results['spec_generated_artifacts']==read('08-spec/run.log')['generated_artifacts']
 assert len(results['numeric_results'])==3
 for row in results['numeric_results']:
  value=read(row['raw_alias']);assert value[row['field']]['result']==row['result']
  assert row['result']['verdict']=='BLOCKED' and row['result']['outcome']=='environment_unavailable' and row['result']['exit_code']==1
 binding=m['native_completion_binding'];assert binding['native_receipt_sha256']==by['09-native/receipt.json']['raw_sha256'] and binding['restoration_sha256']==by['09-native/restoration.json']['raw_sha256'] and binding['root_reported_native_and_restoration_complete']
 ui=json.loads((root/'ui-snapshot-resolutions.json').read_bytes());assert ui['count_per_snapshot']==44 and len(ui['entries'])==88;assert ui['changed_pair_count']==len(native['changed_inputs'])
 ui_by={r['raw_alias']:r for r in ui['entries']};assert len(ui_by)==88;raw_ui=0
 for side in ['before','after']:
  manifest=read(f'09-native/ui-{side}/manifest.json');assert manifest['count']==len(manifest['files'])==44
  for entry in manifest['files']:
   name=f"09-native/ui-{side}/{entry['archived_file']}";row=ui_by[name];assert (row['raw_bytes'],row['raw_sha256'])==(entry['bytes'],entry['sha256']);assert row['source_git_path']==entry['path'] and row['source_commit']==m['fixed_commit']
   if row['resolution']=='public_changed_pair':assert row['public_alias']==name and (by[name]['raw_bytes'],by[name]['raw_sha256'])==(row['raw_bytes'],row['raw_sha256'])
   else:
    assert row['resolution']=='exact_unchanged_git_blob';assert (row['git_blob'],row['git_mode'])==(gs[entry['path']]['git_blob'],gs[entry['path']]['git_mode']);assert (row['raw_bytes'],row['raw_sha256'])==(bs[entry['path']]['bytes'],bs[entry['path']]['sha256'])
    if args.raw_base:
     raw=safe(args.raw_base,row['raw_relative']).read_bytes();assert (len(raw),sha(raw))==(row['raw_bytes'],row['raw_sha256']);raw_ui+=1
 git_sources=0
 if args.repo:
  tree={}
  for line in subprocess.check_output(['git','ls-tree','-rz',m['fixed_commit']],cwd=args.repo).split(b'\0'):
   if not line:continue
   header,path=line.split(b'\t',1);mode,kind,oid=header.decode().split();name=path.decode()
   if not name.startswith('progress/'):assert kind=='blob';tree[name]=(mode,oid)
  assert len(tree)==m['source_count'] and set(tree)==set(bs)
  names=sorted(tree);output=subprocess.check_output(['git','cat-file','--batch'],input=('\n'.join(tree[name][1] for name in names)+'\n').encode(),cwd=args.repo);cursor=0
  for name in names:
   end=output.index(b'\n',cursor);oid,kind,size=output[cursor:end].decode().split();cursor=end+1;size=int(size);payload=output[cursor:cursor+size];cursor+=size;assert output[cursor:cursor+1]==b'\n';cursor+=1
   assert kind=='blob' and (gs[name]['git_mode'],gs[name]['git_blob'])==tree[name] and oid==tree[name][1];assert (len(payload),sha(payload))==(bs[name]['bytes'],bs[name]['sha256']);git_sources+=1
  assert cursor==len(output)
 print(json.dumps(dict(status='VERIFIED_CAPTURED_EVIDENCE',public_files=len(actual),raw_aliases=len(aliases),raw_aliases_replayed=raw_count,unchanged_ui_raw_replayed=raw_ui,ui_resolutions=88,gate_receipts=9,git_source_blobs_verified=git_sources,publication_scan='PASS',tests_executed=False),sort_keys=True))
if __name__=='__main__':main()
