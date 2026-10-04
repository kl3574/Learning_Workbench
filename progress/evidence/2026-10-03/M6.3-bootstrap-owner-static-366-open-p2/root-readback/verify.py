from pathlib import Path
import hashlib,importlib.util,json,subprocess
base=Path('$HOME/.cache/learning-workbench-acceptance');root=base/'m62-public-safe-oct02'
producer=base/'m63-bootstrap-owner-static-review-366-oct03'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
raw=json.loads((producer/'RAW_MANIFEST.json').read_text());safe=json.loads((producer/'SAFE_SHARE.json').read_text());source=json.loads((producer/'SOURCE.json').read_text())
assert raw['count']==len(raw['files'])==safe['count']==len(safe['files'])==27
for item in raw['files']:
 data=(producer/item['path']).read_bytes();assert sha(data)==item['sha256'] and len(data)==item['bytes']
for item in safe['files']:
 data=(producer/item['path']).read_bytes(); public=(producer/'public-candidates'/item['path']).read_bytes()
 assert sha(data)==item['raw_sha256'] and sha(public)==item['public_sha256']
 assert public==data.replace(b'$HOME',b'$HOME')
head='366d7b862379b3f3fa27808b04dbbd1b2694a6bc'
assert source['review_commit']==head and len(source['source_files'])==22
for item in source['source_files']:
 blob=subprocess.check_output(['git','show',head+':'+item['path']],cwd=root)
 assert sha(blob)==item['sha256'] and len(blob)==item['bytes']
 assert subprocess.check_output(['git','rev-parse',head+':'+item['path']],cwd=root,text=True).strip()==item['blob_sha1']
report={'status':'PASS_REVIEW_PROVENANCE_ONE_OPEN_P2','head':head,'source_files_independently_bound':22,'raw_files':27,'exact_home_public_files':27,
 'finding':'One static P2: new owner lock file created before authorization and historical command replay in fixed366. No claim of second start or DB write.',
 'fix_state':'Owner reports WIP ExitStack change; not fixed-source rechecked here.',
 'scope':'Owner/service/repository/HTTP/lifecycle static review. No runtime/isolation system probe, test, CLI, network, model or old diagnostic restart. Full stage unaccepted.'}
(Path(__file__).parent/'READBACK.json').write_text(json.dumps(report,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('pack',base/'m62-v313-pushed-progress-sync-oct03/package.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
path=module.package('M6.3-bootstrap-owner-static-366-open-p2',[
 ('review','m63-bootstrap-owner-static-review-366-oct03',[item['path'] for item in safe['files']]),
 ('metadata','m63-bootstrap-owner-static-review-366-oct03',['RAW_MANIFEST.json','SAFE_SHARE.json','SAFE_SCAN.json']),
 ('root-readback','m63-bootstrap-owner-root-readback-oct03',['verify.py','READBACK.json'])],
 {'status':'FIXED_INTERMEDIATE_OWNER_STATIC_REVIEW_ONE_P2_OPEN','head':head,
 'independent_provenance':'27 raw/explicit-public hashes and 22 fixed Git source blobs independently checked.',
 'finding':report['finding'],'fix_state':report['fix_state'],'boundary':report['scope']})
state=module.read_state();task=next(t for t in state['tasks'] if t['id']=='M6.3');task['evidence_paths'].append(path)
code='M63_BOOTSTRAP_OWNER_FILE_ADMISSION'
assert not any(item['code']==code for item in state['blockers'])
state['blockers'].append({'code':code,'status':'FIXED_366_STATIC_P2_WIP_FIX_PENDING_FIXED_RECHECK','description':'固定366独立静态P2：session POST在当前准入和原ACK回放前创建未登记owner文件；不是第二CLI或DB写。作者已在WIP调整锁获取顺序，需固定delta和永久反例复核，当前不报修复完成。'})
task['blockers'].append(code);module.save(state)
print(json.dumps(report))
