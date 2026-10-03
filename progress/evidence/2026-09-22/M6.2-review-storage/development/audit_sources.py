from pathlib import Path
import hashlib, json, subprocess
ROOT=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-review-storage-active')
BASE=Path(__file__).parent
BASELINE='16f4ae1355c4398a6b419b2fa883ec5211624c3d'
FINAL='4bf176de1cdf0a76cdf0fa965027ec3a5367551f'

def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT)
def dump(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def digest(data): return hashlib.sha256(data).hexdigest()
def tree(commit):
    rows={}
    for entry in git('ls-tree','-rz',commit).split(b'\0'):
        if not entry:continue
        meta,name=entry.split(b'\t',1);mode,kind,blob=meta.decode().split();name=name.decode()
        if not name.startswith('progress/'):rows[name]={'git_mode':mode,'git_blob_sha1':blob}
    return rows
blobs={}
def blob(blobid):
    if blobid not in blobs:
        raw=git('cat-file','blob',blobid)
        blobs[blobid]={'sha256':digest(raw),'bytes':len(raw)}
    return blobs[blobid]
results=[]
for stage in sorted(BASE.iterdir()):
    if not stage.is_dir() or not (stage/'receipt.json').exists():continue
    stage_result={'stage':stage.name,'snapshots':[]}
    sides=[]
    for side in ['before','after']:
        value=json.loads((stage/f'{side}.json').read_text());head=value['head'];expected=tree(head)
        actual=value['files']
        if isinstance(actual,list):actual={r['path']:r for r in actual}
        actual={name:row for name,row in actual.items() if not name.startswith('progress/')}
        discrepancies=[]
        if set(expected)!=set(actual):discrepancies.append({'path_set_difference':sorted(set(expected)^set(actual))})
        for name,row in expected.items():
            registered=blob(row['git_blob_sha1'])
            if actual.get(name,{}).get('sha256')!=registered['sha256'] or actual.get(name,{}).get('bytes')!=registered['bytes']:
                discrepancies.append({'path':name,'kind':'actual_bytes_do_not_match_actual_commit'})
        stage_result['snapshots'].append({'side':side,'head':head,'source_count':len(expected),
            'all_source_bytes_match_actual_git':not discrepancies,'discrepancies':discrepancies})
        sides.append(actual)
    stage_result['changed_sources']=sorted(name for name in set(sides[0])|set(sides[1]) if sides[0].get(name)!=sides[1].get(name))
    results.append(stage_result)
commits=git('rev-list','--reverse',f'{BASELINE}..{FINAL}').decode().splitlines()
paths=git('diff','--name-only',BASELINE,FINAL).decode().splitlines()
snapshots=[]
for commit in commits:
    directory=BASE/'source'/commit;directory.mkdir(parents=True)
    for name in paths:
        lookup=f'{commit}:{name}'
        query=subprocess.run(['git','cat-file','-e',lookup],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if query.returncode: continue
        raw=git('show',lookup);target=directory/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        snapshots.append({'commit':commit,'path':name,'sha256':digest(raw),'bytes':len(raw),'git_blob_sha1':git('rev-parse',lookup).decode().strip()})
    patch=git('diff','--binary',f'{commit}^',commit,'--',*paths);(directory/'change.patch').write_bytes(patch)
protected=['PRODUCT_DESIGN.md','migrations/0001_baseline.sql','migrations/0016_draft_candidate_identities.sql','packages/contracts/domain_models.py']
unchanged=[]
for name in protected:
    before=git('show',f'{BASELINE}:{name}');after=git('show',f'{FINAL}:{name}')
    unchanged.append({'path':name,'before_sha256':digest(before),'after_sha256':digest(after),'unchanged':before==after})
report={'baseline':BASELINE,'final':FINAL,'final_parent_chain_commits':commits,'changed_paths':paths,
        'source_snapshot_count':len(snapshots),'source_snapshots':snapshots,'protected_bytes':unchanged,'stages':results,
        'note':'Initial runner retained all tracked files; engineering reconciliation excludes progress. The original regression ran while a new test was appended; its 229 PASS is not a fixed-source final gate. No recorded original is overwritten.'}
dump(BASE/'source-audit.json',report)
(BASE/'final-change.patch').write_bytes(git('diff','--binary',BASELINE,FINAL))
print(json.dumps({'stages':len(results),'snapshots':len(snapshots),'all_stage_sides_match_actual_git':all(all(s['all_source_bytes_match_actual_git'] for s in r['snapshots']) for r in results),'changed_during_stages':[{r['stage']:r['changed_sources']} for r in results if r['changed_sources']],'protected_unchanged':all(p['unchanged'] for p in unchanged)},indent=2))
