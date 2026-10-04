"""Independent fixed Git and exact admitted documentary readback; no product execution."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,subprocess
ROOT=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m71-codex-backup-synthetic-owner-oct05')
OWNER=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m71-codex-backup-synthetic-dfd-evidence-oct05')
SOURCE='942fc533ca48e1a561199fb992d80e76622948c1'
ORIGINAL='dfd9a77de24c2ca9145466f91299a13d0a2d967b'
BASE='d6d4d9b98316d7f3790eb60e5d1bb4aca67450d1'
SPEC='b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
blobs={};trees={}
def tree(head):
    if head in trees:return trees[head]
    rows={}
    for item in git('ls-tree','-rz',head).split(b'\0'):
        if not item:continue
        meta,p=item.split(b'\t',1);p=p.decode();mode,kind,oid=meta.decode().split()
        if p.startswith('progress/'):continue
        assert kind=='blob'
        if oid not in blobs:blobs[oid]=git('cat-file','blob',oid)
        b=blobs[oid];rows[p]={'mode':mode,'type':kind,'git_blob':oid,'bytes':len(b),'sha256':sha(b)}
    trees[head]=rows;return rows
def reverse(data,entry):
    assert len(data)==entry['size']and sha(data)==entry['sha256']
    if entry['transformation']=='none':
        assert sha(data)==entry['original_sha256'];return data
    assert entry['transformation']=='exact home absolute prefix to $HOME display only'
    parts=data.split(b'$HOME');n=len(parts)-1;assert n<=20
    for bits in range(1<<n):
        b=parts[0]
        for i,p in enumerate(parts[1:]):b+=(b'<LOCAL_HOME>'if bits>>i&1 else b'$HOME')+p
        if sha(b)==entry['original_sha256']:
            assert b.replace(b'<LOCAL_HOME>',b'$HOME')==data;return b
    raise AssertionError(('undeclared transformation',entry['path']))
def verify():
    assert git('rev-parse','HEAD').decode().strip()==SOURCE and git('status','--porcelain')==b''
    mb=(OWNER/'SAFE_SHARE_REVIEW.json').read_bytes();ob=(OWNER/'OUTER_ALLOWLIST.json').read_bytes()
    assert sha(mb)=='5ae427e1282589d1907d7d21ed7d017df8bab460f19fc2e7aaeaf471861f1c8d'
    assert sha(ob)=='37fa449ee70c338b8e1541f434130342204c1a506608c5492924fb49bb6d9efd'
    manifest=json.loads(mb);outer=json.loads(ob)
    assert manifest['fixed_source']==outer['source_commit']==SOURCE
    assert manifest['candidate_count']==outer['candidate_count']==len(manifest['entries'])==56
    assert outer['entries']==[{'path':'SAFE_SHARE_REVIEW.json','sha256':sha(mb),'size':len(mb)}]
    data={};raw={};entries={}
    for e in manifest['entries']:
        n=e['path'];p=Path(n);assert not p.is_absolute()and '..'not in p.parts and n not in data
        data[n]=(OWNER/'safe-share'/p).read_bytes();raw[n]=reverse(data[n],e);entries[n]=e
    assert sha(data['REPORT.md'])=='681b8574ef6af59d942bd7f92638fe9413e55df68c67ce3fe67d553f98f19955'
    assert sha(data['READBACK.json'])=='d8b325eed26c0326d2f545cf8333d96b107f097cefa8805081ac90d45be30583'
    assert sha(data['SHA256_BINDINGS.json'])=='7d457495ae7181bb77f891808f3a70745dc2b1b99d3158480c655a246644b87a'
    def obj(n):return json.loads(data[n])
    for h,p in [(ORIGINAL,BASE),(SOURCE,ORIGINAL)]:assert git('show','-s','--format=%P',h).decode().strip()==p
    current=tree(SOURCE);base=tree(BASE);initial=tree(ORIGINAL)
    assert len(current)==len(initial)==1523 and len(base)==1522
    assert all(current[p]==r for p,r in base.items())
    changed=git('diff','--name-only',BASE,SOURCE).decode().splitlines();assert changed==['tests/integration/test_backup_codex_turn_history.py']
    assert current['PRODUCT_DESIGN.md']['sha256']==SPEC
    for h,n in [(ORIGINAL,'source/original-test.py'),(SOURCE,'source/final-test.py')]:assert raw[n]==git('show',h+':'+changed[0])
    assert raw['source/final-change.patch']==git('diff',BASE,SOURCE)
    maps=[];stages=[];bindings=0
    for stage,head,exit in [('01-original-focused',ORIGINAL,1),('02-fixed-focused',SOURCE,0),('03-related-backups',SOURCE,0),('04-ruff',SOURCE,0),('05-diff-check',SOURCE,0)]:
        command=obj(stage+'/command.json');receipt=obj(stage+'/receipt.json')
        assert command['source_commit']==receipt['source_commit']==head
        assert receipt['engineering_inputs']==1523 and receipt['source_inputs_unchanged']is True
        assert receipt['exit_code']==exit and receipt['status']==('FAIL'if exit else'PASS')
        assert receipt['approval_import_new_owner_coverage']==receipt['workspace_restore_preview_commit']==receipt['full_platform_gate']=='NOT_RUN'
        before=obj(stage+'/before.json');after=obj(stage+'/after.json');assert before==after and before['source_commit']==head
        for phase in ['before','after']:
            n=stage+'/'+phase+'.json';mapping=obj(n);rows=mapping['entries'];fixed=tree(head)
            assert len(rows)==len({r['path']for r in rows})==len(fixed)==1523
            assert set(r['path']for r in rows)==set(fixed)
            for r in rows:
                f=fixed[r['path']];assert r=={'path':r['path'],'size':f['bytes'],'sha256':f['sha256'],'git_blob':f['git_blob']}
            bindings+=len(rows);maps.append({'path':n,'sha256':sha(data[n]),'source_commit':head,'entry_count':len(rows)})
        log=stage+'/run.log';admitted=log in raw
        if admitted:assert sha(raw[log])==receipt['original_log_sha256']
        stages.append({'stage':stage,'head':head,'command':command,'receipt':receipt,'log_admitted':admitted,'original_log_sha256':receipt['original_log_sha256']})
    sb=obj('SHA256_BINDINGS.json');distinct={r['git_blob']for h in [ORIGINAL,SOURCE]for r in tree(h).values()}
    assert maps==sb['maps']and bindings==sb['exact_git_size_sha256_entry_bindings']==15230
    assert len(distinct)==sb['distinct_checked_git_blobs']==1505
    assert len(maps)==sb['map_count']==10
    assert '2 failed'in data['01-original-focused/bounded-failure.txt'].decode()
    assert '2 passed'in data['02-fixed-focused/run.log'].decode()
    assert '21 passed'in data['03-related-backups/run.log'].decode()
    assert data['04-ruff/run.log'].decode()=='All checks passed!\n'and data['05-diff-check/run.log']==b''
    clis=[];archives=[]
    for stage in ['01-original-focused','02-fixed-focused','03-related-backups']:
        for variant in ['queued','manifest']:
            prefix='cli/'+stage+'-'+variant+'/';r=obj(prefix+'backup-cli-receipt.json')
            assert r['exit_code']==0 and r['source_tables_unchanged']is True and r['restore_acceptance']=='NOT_RUN'
            assert data[prefix+'backup-cli.stderr']==b''
            assert r['source_files_unchanged']is(stage!='01-original-focused')
            if stage=='01-original-focused':assert set(r['changed_source_paths'])=={'backup-cli.stderr','backup-cli.stdout','uv-a9411322b96c4e84.lock'}
            else:assert r['changed_source_paths']==[]
            clis.append({'candidate_prefix':prefix,'receipt':r,'stdout_sha256':sha(data[prefix+'backup-cli.stdout']),'stdout_original_declared_sha256':entries[prefix+'backup-cli.stdout']['original_sha256']})
            if stage!='01-original-focused':
                n=prefix+'archive-metadata.json';a=obj(n);m=a['manifest']
                assert a['checked_payloads']==m['files']and m['restore_acceptance']=='NOT_RUN'and m['sensitive_personal_data']is True and m['consent_dispatch_disabled']is True
                manifest_bytes=json.dumps(m,ensure_ascii=False,sort_keys=True).encode();assert sha(manifest_bytes)==a['archive_manifest_sha256']
                expected={'workspace.sqlite3'}|({'blobs/d7e6e49b6dae3201055d2b0cbe41284e04bae1e717d2f6431b6b201f0eb480a2'}if variant=='manifest'else set())
                assert set(p['path']for p in m['files'])==expected
                if variant=='manifest':assert next(p for p in m['files']if p['path'].startswith('blobs/'))['size']==26
                for count in ['codex_approval_events','codex_import_batches','codex_artifact_import_events']:assert m['object_counts'][count]==0
                archives.append({'path':n,'metadata_sha256':sha(data[n]),'archive_manifest_reconstructed_sha256':sha(manifest_bytes),'archive_sha256_owner_declaration_not_directly_read':a['archive_sha256'],'files':m['files']})
    assert obj('READBACK.json')['candidate_count']==53 and sb['original_readback_candidate_count_semantics']=='53 files before READBACK.json itself; original SAFE_SHARE.json lists 54; final allowlist adds two documentary files'
    assert git('rev-parse','HEAD').decode().strip()==SOURCE and git('status','--porcelain')==b''
    return {'read_at_utc':datetime.now(timezone.utc).isoformat(),'review_type':'PURE_SOURCE_AND_PREEXISTING_EXPLICIT_DOCUMENTARY_READBACK_NO_NEW_TEST_EXECUTION','source_sha':SOURCE,'base':BASE,'parent':ORIGINAL,'sole_spec_sha256':SPEC,'inputs':1523,'base_inputs':1522,'all_base_inputs_unchanged':1522,'changed_paths':changed,'numstat':git('diff','--numstat',BASE,SOURCE).decode().splitlines(),'candidate_base':str(OWNER/'safe-share'),'owner_explicit_SAFE_sha256':sha(mb),'owner_explicit_OUTER_sha256':sha(ob),'candidate_count':56,'candidate_count_semantics':'Original READBACK53 before itself, original manifest54, final+two documentary56; explicitly qualified not silently corrected.','candidates':[dict(e,verified_candidate_and_reconstructed_original_declaration=True)for e in entries.values()],'map_count':10,'map_bindings':15230,'distinct_gate_Git_blobs':1505,'maps':maps,'stages':stages,'cli_runs':clis,'archive_metadata':archives,'map_boundary':'Original execution maps record size/SHA256/Gitblob only, not runtime file modes. Immutable full Git mode/type/blob/size/SHA independently read; mode is not retroactively added to run maps.','runner_boundary':'Admitted runner and finalize scripts statically read/hashed; execution receipts do not contain runner hashes. No retroactive run-level runner hash invented. Display-transformed scripts are archival not runnable equivalents.','original_failure_boundary':'Only explicitly admitted bounded failure excerpt read; original complete FAIL log remains excluded/unread and its SHA is declared in actual receipt.','archive_boundary':'Only admitted four archive metadata candidates checked, including reconstructable manifest SHA; no ZIP, DB or payload raw file opened here. Original passed tests performed payload/auth checks.','restore_preview_commit':'NOT_RUN','background_lifespan_worker_recovery':'NOT_RUN','GenericApproval_Import_backup_coverage':'NOT_RUN','fresh_actor_denial_scope':'Old turn-start and outbound grant body/key denied; no GenericApproval history exists. No old-actor worker grant consumption executed.','M7_acceptance':'NOT_RUN_TODO_DEPENDS_ON_M6','actual_vendor_Codex_CLI':'NOT_RUN','new_product_execution':False,'source_or_canonical_edited':False,'old_seals_edited':False,'remote_publication':False}
if __name__=='__main__':
    result=verify();p=Path(__file__).with_name('READBACK.json');p.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ['inputs','all_base_inputs_unchanged','candidate_count','map_count','map_bindings','distinct_gate_Git_blobs']},indent=2))
