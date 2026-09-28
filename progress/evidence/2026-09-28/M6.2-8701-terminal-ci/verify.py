"""Offline public and exact-original replay; no tests, network or writes."""
import argparse
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path, PurePosixPath

def sha(raw):return hashlib.sha256(raw).hexdigest()
def safe(base,name):
    path=PurePosixPath(name)
    assert not path.is_absolute() and '..' not in path.parts
    return base/name
def checked(path,row,prefix=''):
    raw=path.read_bytes()
    assert len(raw)==row[prefix+'bytes'] and sha(raw)==row[prefix+'sha256'],str(path)
    return raw
def replay(raw,spans):
    out,cursor=bytearray(),0
    for s in spans:
        start,end=s['raw_offset'],s['raw_offset']+s['raw_length']
        assert cursor<=start<end<=len(raw) and sha(raw[start:end])==s['raw_sha256']
        out.extend(raw[cursor:start]);assert len(out)==s['public_offset']
        out.extend(s['replacement'].encode());cursor=end
    out.extend(raw[cursor:]);return bytes(out)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-base',type=Path,help='Parent of the named private cache')
    args=parser.parse_args();root=Path(__file__).resolve().parent
    m=json.loads((root/'manifest.json').read_bytes());expected={'manifest.json'}
    included,public,originals={},{},{}
    for row in m['included_raw']:
        expected.add(row['public_path']);data=checked(safe(root,row['public_path']),row,'public_')
        included[row['raw_path']]=row;public[row['raw_path']]=data
        end=0
        for span in row['spans']:
            offset=span['public_offset'];replacement=span['replacement'].encode()
            assert end<=offset and data[offset:offset+len(replacement)]==replacement
            end=offset+len(replacement)
        if args.raw_base:
            raw=checked(safe(args.raw_base,m['original_cache_name']+'/'+row['raw_path']),row,'raw_')
            assert replay(raw,row['spans'])==data;originals[row['raw_path']]=raw
    for row in m['generated']:
        expected.add(row['path']);checked(safe(root,row['path']),row)
    assert expected=={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    excluded={row['raw_path']:row for row in m['excluded_raw']}
    assert not set(included)&set(excluded)
    if args.raw_base:
        base=args.raw_base/m['original_cache_name']
        for name,row in excluded.items():originals[name]=checked(safe(base,name),row,'raw_')
        assert set(originals)=={p.relative_to(base).as_posix() for p in base.rglob('*') if p.is_file()}
        assert sha(originals['MANIFEST.json'])==m['original_manifest_sha256']
        frozen=json.loads(originals['MANIFEST.json'])['files']
        assert len(frozen)==m['frozen_manifest_members']
        for row in frozen:
            assert len(originals[row['path']])==row['bytes'] and sha(originals[row['path']])==row['sha256']
    e=json.loads(public['FINAL_JOB_EVIDENCE.json']);bound=m['terminal_ci'];label=e['terminal_poll']
    assert e['head']==bound['head'] and e['pr_actual_checkout']==bound['pr_actual_checkout'] and e['actual_tree']==bound['tree']
    assert len(e['jobs'])==12
    actual_jobs={}
    for event in ['push','pull_request']:
        commit=json.loads(public['checkout-'+event+'.json'])
        checkout=e['head'] if event=='push' else e['pr_actual_checkout']
        assert commit['sha']==checkout and commit['tree']['sha']==e['actual_tree']
        run=json.loads(public[label+'-'+event+'-run.json'])
        assert run['id']==bound['runs'][event]['id'] and run['event']==event and run['head_sha']==e['head']
        assert run['status']=='completed' and run['conclusion']==bound['runs'][event]['conclusion'] and run['run_attempt']==1
        jobs=json.loads(public[label+'-'+event+'-jobs.json'])['jobs']
        assert len(jobs)==6 and all(j['status']=='completed' for j in jobs)
        actual_jobs[event]={j['id']:j for j in jobs}
        assert set(actual_jobs[event])=={j['id'] for j in e['jobs'] if j['event']==event}
    ansi=re.compile(r'\x1b\[[0-9;]*[A-Za-z]');apt=0;failures=[]
    for job in e['jobs']:
        actual=actual_jobs[job['event']][job['id']]
        assert job['name']==actual['name'] and job['conclusion']==actual['conclusion']
        binding=included[job['log_path']]
        assert binding['raw_sha256']==job['log_sha256'] and binding['raw_bytes']==job['log_bytes']
        assert all(s['reason']=='exact filesystem path alias' for s in binding['spans'])
        lines=[ansi.sub('',line) for line in public[job['log_path']].decode().splitlines()]
        assert job['checkout']['sha'] in lines[job['checkout']['line']-1]
        assert job['checkout']['sha']==(e['head'] if job['event']=='push' else e['pr_actual_checkout'])
        for row in job['scope_summaries']+job['environment_or_skip_evidence']+job['failure_lines']:
            assert lines[row['line']-1]==row['text']
        if job['installed_packages']:
            assert len(job['installed_packages'])==4 and job['apt_step']=='success'
            for package,row in job['installed_packages'].items():
                assert package in lines[row['line']-1] and row['version'] in lines[row['line']-1]
            apt+=1
        if job['conclusion']=='failure':failures.append(job['event']+'/'+job['name'])
    assert sorted(failures)==sorted(bound['failed_jobs']) and apt==bound['apt_exact_installations']
    members=0
    for artifact in e['artifacts']:
        name='artifacts/'+artifact['event']+'-'+str(artifact['id'])+'.zip'
        assert name in excluded and excluded[name]['raw_sha256']==artifact['sha256']
        assert artifact['server_digest']=='sha256:'+artifact['sha256']
        archive=zipfile.ZipFile(io.BytesIO(originals[name])) if args.raw_base else None
        if archive:assert {i.filename for i in archive.infolist() if not i.is_dir()}=={i['path'] for i in artifact['members']}
        try:
            for row in artifact['members']:
                path='extracted/'+Path(name).stem+'/'+row['path']
                assert included[path]['raw_bytes']==row['bytes'] and included[path]['raw_sha256']==row['sha256']
                if archive:assert archive.read(row['path'])==originals[path]
                members+=1
        finally:
            if archive:archive.close()
    assert members==bound['artifact_members'] and len(e['artifacts'])==bound['artifacts']
    print(json.dumps({'public_files':len(expected),'included_raw':len(included),'excluded_raw':len(excluded),
        'complete_logs':12,'failed_jobs':failures,'exact_apt_installations':apt,'artifact_members':members,
        'private_replay':bool(args.raw_base),'unique_archive_containers_private':len(e['artifacts']),
        'head':e['head'],'actual_tree':e['actual_tree'],'network_requests':0,'product_tests':0},indent=2))

if __name__=='__main__':main()
