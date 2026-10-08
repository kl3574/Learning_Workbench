"""Explicit manually reviewed candidates; never recurse through browser/runtime output."""
from pathlib import Path
import hashlib,json,os,datetime
os.umask(0o077)
e=Path(__file__).resolve().parent;s=e/'seal-22eb';dest=s/'publication-candidates';dest.mkdir(mode=0o700)
sha=lambda b:hashlib.sha256(b).hexdigest()
binding=json.loads((s/'SOURCE_BINDINGS.json').read_text())
stages=['red-handler','red-handler-02','green-client','fixed-mechanism','review-native','web-strict','identity-observation','focused-types','final-mechanism','final-types','final-web-strict','final-review','bound-mechanism','bound-types','diff-check','route-phase','exact-review','exact-mechanism','exact-types','exact-web-strict','exact-diff']
choices=[]
def add(path,label=None):choices.append((path,label or str(path.relative_to(e))))
for name in ['REPORT.md','SOURCE_BINDINGS.json','STAGE_HISTORY.json','owned.patch']:add(s/name,name)
for h in binding['git_heads']:add(s/'git'/f'{h}.json','git/'+h+'.json')
for p in binding['changed_paths']:add(s/'source'/p,'source/'+p)
for name in ['run.py','run-bound.py','mechanism.config.ts','focused-types.json','playwright-official-types.d.ts','seal-evidence.py','prepare-candidates.py']:add(e/name,'harness/'+name)
for stage in stages:
 for name in ['command.json','receipt.json','source-before.json','source-after.json']:add(e/stage/name,'stages/'+stage+'/'+name)
# Read and individually admitted success logs plus the inert mechanism RED only.
for stage in ['red-handler-02','green-client','exact-review','exact-mechanism','exact-types','exact-web-strict','exact-diff']:add(e/stage/'run.log','logs/'+stage+'.log')
for stage in ['red-handler-02','green-client']:add(e/stage/'responseJsonBarrier.check.ts','historical-source/'+stage+'/responseJsonBarrier.check.ts')
review='exact-review-output/review-real-history-and-ex-756c0-d-old-revision-after-reload/'
for name in ['actual-review-history.json','review-history-after-1440.png','review-history-after-390.png']:add(e/(review+name),'observations/'+name)
for stage in ['route-phase','exact-review']:add(e/(stage+'-output/review-a-delayed-old-revie-e1a43--a-real-independent-attempt/late-response-phases.json'),'observations/'+stage+'-phases.json')
add(e/'exact-mechanism-output/responseJsonBarrier.check.-be431--an-unrelated-request-alone/identity-phase.json','observations/identity-phase.json')
assert len({label for _,label in choices})==len(choices)
records=[]
for path,label in choices:
 raw=path.read_bytes();binary=path.suffix=='.png'
 if binary:public=raw;transform='identity PNG, manually viewed'
 else:
  raw.decode('utf-8');public=raw.replace(b'${HOME}',b'${HOME}');transform='literal home-prefix-only' if public!=raw else 'identity UTF-8'
 out=dest/label;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(public)
 assert out.read_bytes()==public
 records.append(dict(raw_path=str(path),candidate_path=label,raw_bytes=len(raw),candidate_bytes=len(public),raw_sha256=sha(raw),candidate_sha256=sha(public),transformation=transform))
manifest=dict(source_sha=binding['head'],count=len(records),png_count=sum(r['candidate_path'].endswith('.png') for r in records),created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),allowed_transforms=['identity','literal ${HOME} -> ${HOME}'],exclusions=['all non-admitted raw failure logs','browser profiles','database','key','credential state','cache','ZIP','TMPDIR'],files=records)
(s/'SAFE_CANDIDATES.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Closed candidate readback, preserving and rechecking every original input.
for item in records:
 raw=Path(item['raw_path']).read_bytes();candidate=(dest/item['candidate_path']).read_bytes()
 assert sha(raw)==item['raw_sha256'] and sha(candidate)==item['candidate_sha256']
 assert candidate==(raw if item['candidate_path'].endswith('.png') else raw.replace(b'${HOME}',b'${HOME}'))
actual={str(p.relative_to(dest)) for p in dest.rglob('*') if p.is_file()}
assert actual=={x['candidate_path'] for x in records}
receipt=dict(source_sha=binding['head'],candidate_count=len(records),candidate_pngs=manifest['png_count'],all_candidates_read_back=True,all_raw_sources_read_back=True,extra_candidates=[],source_bindings_sha256=sha((s/'SOURCE_BINDINGS.json').read_bytes()),report_sha256=sha((s/'REPORT.md').read_bytes()),safe_manifest_sha256=sha((s/'SAFE_CANDIDATES.json').read_bytes()),boundary='Candidates only; root independent review pending. No publish/install/source mutation.')
(s/'READBACK.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
