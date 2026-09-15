from pathlib import Path
import datetime, hashlib, json, re, sys
base=Path('<DIAGNOSIS_CACHE>')
root=Path('<REPOSITORY_ROOT>')
public=base.parent/'m42-route-draft-diagnosis-public-v1'
public.mkdir(exist_ok=False)
artifact_base='progress/evidence/2026-09-15/M4.2-route-draft-diagnosis'
def digest(data):return hashlib.sha256(data).hexdigest()
transforms=[(str(base),'<DIAGNOSIS_CACHE>'),(str(root),'<REPOSITORY_ROOT>'),('<ACCEPTANCE_CACHE>','<ACCEPTANCE_CACHE>'),('<NATIVE_TMPDIR>','<NATIVE_TMPDIR>'),('<USER_HOME>','<USER_HOME>')]
def normalize(data):
    text=data.decode()
    applied=[]
    for raw,alias in transforms:
        if raw in text: applied.append({'rule':'normalize personal filesystem prefix','to':alias,'count':text.count(raw)});text=text.replace(raw,alias)
    return text.encode(),applied
entries=[]
def copy(path,target=None):
    rel=target or str(path.relative_to(base));raw=path.read_bytes()
    if path.suffix=='.png':data=raw;applied=[]
    else:data,applied=normalize(raw)
    dest=public/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    entries.append({'path':rel,'original_path':normalize(str(path).encode())[0].decode(),'original_sha256':digest(raw),'public_sha256':digest(data),'bytes':len(data),'transformations':applied,'image_viewed':True if path.suffix=='.png' else None})
selected_png_runs={'run-05-artifacts','run-06-artifacts','run-10-artifacts','run-11-artifacts','run-12-artifacts'}
for path in sorted(base.iterdir()):
    if path.is_file():copy(path)
    elif path.name.endswith('-source') or path.name=='fixed-harness-01':
        for child in sorted(path.rglob('*')):
            if child.is_file():copy(child)
    elif re.fullmatch(r'run-\d+-artifacts',path.name):
        for child in sorted(path.rglob('*')):
            if child.is_file() and (child.suffix in {'.json','.md'} or child.suffix=='.png' and path.name in selected_png_runs):copy(child)
owned=['apps/web/src/shared/createResponseDraftJournal.ts','apps/web/src/shared/createResponseDraftJournal.test.tsx','apps/web/src/features/routes/RouteEditorDraftSequence.test.tsx','tests/e2e/route-draft-input.spec.ts']
for p in owned:copy(base/'fixed-source-01'/p,'final-source/'+p+'.txt')
# Record actual unchanged assertion/body comparisons, independent of personal paths.
def body(path):
    text=path.read_text();text=text[text.index("test('real route creation"):];return text.split('\n\nimport { startObserver')[0].rstrip()
original=body(base/'original-routes.spec.ts.txt')
assertions={'original_body_sha256':digest(original.encode()),'controlled_original_body_equal':body(base/'routes-controlled.spec.ts')==original,'fixed_controlled_body_equal':body(base/'fixed-harness-01/routes-controlled.spec.ts')==original,'fixed_original_body_equal':body(base/'fixed-harness-01/routes-observed.spec.ts')==original,'observer_transform':'Only exact source root import prefixes relocated into immutable fixed-source-01; assertions and observation/control logic unchanged.'}
for name in ['observer.ts','observer-sampled.ts','observer-controlled.ts']:
    old=(base/name).read_text();new=(base/'fixed-harness-01'/name).read_text();assertions[name]={'exact_bytes_after_source_root_relocation':old.replace('<ACCEPTANCE_CACHE>/m42-4cf13f7',str(base/'fixed-source-01'))==new,'original_sha256':digest(old.encode()),'fixed_sha256':digest(new.encode())}
assert all(assertions[k] for k in ['controlled_original_body_equal','fixed_controlled_body_equal','fixed_original_body_equal'])
new=(base/'fixed-source-01/tests/e2e/route-draft-input.spec.ts').read_text()
old=(base/'permanent-before-02.spec.ts').read_text().replace("'<ACCEPTANCE_CACHE>/m42-4cf13f7/apps/web/node_modules/@playwright/test/index.mjs'","'../../apps/web/node_modules/@playwright/test/index.mjs'").replace("'<ACCEPTANCE_CACHE>/m42-4cf13f7/apps/web/src/workbench/DraftStore.ts'","'../../apps/web/src/workbench/DraftStore'").replace("'<ACCEPTANCE_CACHE>/m42-4cf13f7/tests/e2e/restartRuntime.ts'","'./restartRuntime'")
assertions['permanent_old4cf_vs_fixed_native_bytes_equal_after_import_relocation']=old==new
assert old==new
(public/'assertion-and-observer-comparison.json').write_text(json.dumps(assertions,ensure_ascii=False,indent=2))
results={
'run-01':'HARNESS_COLLECTION_ERROR: missing ESM package scope; no case executed.',
'run-02':'PASS 1 original case (4.6s; 5.1s total).',
'run-03':'PASS 5 original repetitions (25.2s total). Natural sample including run02: 6/6 passed; does not close original full-suite failure.',
'run-04':'PASS 5 original repetitions with CPU rate 2 and read-only DOM input/frame sampling (26.5s total). Own-field temporary disabling was observed, no lost goal in these five.',
'run-05':'FAIL 1 original full case, actual initial IDB save/load Promise delivery held until goal focus, CPU rate 2. Empty goal matches original symptom; no route POST/PUT in observer. Case13.9s. Sufficient controlled trigger, not unique original cause.',
'run-06':'FAIL 3/3 minimized native cases, no CPU throttle, no Import/tasks/server write; actual goal value empty after native fill. Each1.7-1.8s.',
'run-07':'HARNESS_COLLECTION_ERROR: extra closing parenthesis in new native. Bad source preserved; no case executed.',
'run-08':'FAIL 2 new native cases on unchanged4cf. save_first: goal text retained but focus lost, 5s focus assertion failed, case6.7s. load_first: goal text empty, immediate assertion failed, case1.6s. These different failures are recorded separately.',
'run-09':'ENVIRONMENT_SETUP_ERROR 2 cases before UI: immutable snapshot lacked .toolchain link. No product assertion ran.',
'run-10':'PASS 2 new native cases on immutable4cf plus final four owner files, actual cases1.9/1.8s total4.0s. Both goal text/focus/durable IDB record retained, no conflict. Full event ordering in each JSON.',
'run-11':'PASS original controlled full case with original assertions/CPU2/gates/observer: case4.7s total5.1s. Real route POST/PUT, manual false/history/ref assertions all completed.',
'run-12':'PASS original full case with unchanged original steps/assertions and read-only route observer: case4.4s total4.7s.',
'unit-red-01':'Original shared: 1FAIL1PASS. Initial two-sequence test iteration; not proof of both consumption orders.',
'unit-red-02':'Original shared: 4FAIL403ms (2 own-input false conflicts, 2 peer-candidate disappearance after old ACK).',
'unit-green-01':'First enqueue fix, same four test bytes: 4PASS923ms.',
'unit-red-03':'First enqueue fix: 4PASS1FAIL; single-write/no-new-edit late ACK incorrectly reports safe although local candidate not durable.',
'unit-red-04':'Same single-write failure, tests tightened with ACK consumption/Profiler observation: 4PASS1FAIL1.06s.',
'unit-green-02':'Observed-record durability and immediate candidate preservation: same tests5PASS1.01s.',
'unit-resolve-red-01':'Permanent adopted real DraftStore/hook cases: 2FAIL343ms. First loses UI newer peer/baseline (disk retained); second loses explicit selected A after old branch B preservation (disk/hook lack A and unsafe false).',
'unit-resolve-green-01':'First resolve protection iteration plus route seam: 7PASS1.02s.',
'unit-resolve-green-02':'Added selected preservation quota/workspace/remount plus prior notes:23PASS1.81s. Quota is explicit injected DOMException, not physical quota exhaustion.',
'unit-full-01':'Main at captured intermediate source:283PASS47files3.43s, before normal own-resolution notification regression was added.',
'unit-resolve-own-red-01':'Normal explicit selection own load-before-ACK:1FAIL3PASS, returns false new-edit conflict. Proves separate normal-choice edge.',
'unit-resolve-own-green-01':'Known exact resolution identity excludes retired branch preservation only during that in-flight write;24focusedPASS1.80s.',
'unit-full-02':'Main capture:284PASS1FAIL3.48s, failing test is concurrent CI owner newly introduced Workbench initial-navigation RED; source stable during run. This is NOT route fixed full-suite success.',
'unit-fixed-full-01':'Immutable exact4cf plus final four route/journal files, excluding concurrent Workbench edits:284PASS47files3.04s. Full frontend units for this isolated scope, not full platform gates.',
'lint-01':'PASS app TypeScript lint after enqueue fix.',
'lint-02':'PASS app TypeScript lint at final e24982ac shared source.',
 'types-native-fixed-01':'FAIL external strict TS due existing explicit @playwright/test/index.mjs imports without declaration mapping. No source mutation.',
 'types-native-fixed-02':'PASS external strict TS with homecache ambient binding of that exact module pattern to installed official Playwright types; no any, no test/runtime source edits.'}
summary={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'artifact_base':artifact_base,'scope':'Bounded route local draft diagnosis and repair, not M4.2 whole-stage acceptance, not M7 all-size/accessibility acceptance. Original exact4cf files/raw runs remain unchanged. No publish action performed by this owner.','original_failure':'Root exact4cf full-native suite was77PASS1FAIL at original route saved-open button; DB readback zero route writes is root-owned separate evidence, not proof of no request. The original failing full suite had no controlled delivery ledger, so later controlled RED cannot prove its unique timing cause. Separate CI Workbench continue-reading failures are not attributed to this route issue.','results':results,'final_source':{p:digest((base/'fixed-source-01'/p).read_bytes()) for p in owned},'ordering_boundary':'Permanent native save_first/load_first names describe actual returned Promise delivery order; native event ledgers record it. Unit own_save_first waits next write start proving earlier ACK consumed; own_load_first waits real load delivery and React commit while save ACK remains held. Do not equate a gate release alone with consumer completion.','quota_boundary':'Explicit DOMException QuotaExceededError is injected for the selected preservation write. Real DraftStore persistence before/after, memory visibility, beforeunload, workspace switch and remount retry are checked; physical storage exhaustion is not claimed.','normalization':'Only private filesystem prefixes normalized in public derived text. Original raw files are retained unchanged. stdout_sha256 and source SHA fields in raw receipts still identify original bytes; manifest public_sha256 identifies derived publication bytes. Runtime ids, HTTP statuses, assertions, timings and business bodies are unchanged. PNG bytes unchanged, each selected PNG personally viewed. Other private PNGs from naturally passing runs are retained privately and intentionally not copied.','timestamp_semantics':'started_at/finished_at in run receipts bound wrapper command execution including test/setup overhead; printed per-test durations are separate. Wrapper recorded wall times are not inferred UI event times.','known_metadata_correction':'fixed-source-01-manifest.json has manually mistyped base_commit; immutable original retained alongside fixed-source-01-manifest-correction.json. Correct exact commit4cf13f7ed2456d0c7d62a49513055db8b2c8fb20, per-file copied source hashes unaffected.','visual_readback':[e['path'] for e in entries if e['image_viewed']]}
(public/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
# Derived run index binds every actual run's source/test inventory and original output.
index=[]
for name,result in results.items():
    receipt=base/(name+'.json')
    row=json.loads(receipt.read_text());sources=row.get('sources_before',{})
    index.append({'run':name,'result':result,'receipt':name+'.json','original_receipt_sha256':digest(receipt.read_bytes()),'log':name+'.log','original_log_sha256':digest((base/(name+'.log')).read_bytes()),'exit_code':row.get('exit_code'),'started_at':row.get('started_at'),'finished_at':row.get('finished_at'),'source_changes':row.get('source_changes'),'shared_sha256':sources.get(owned[0]),'permanent_route_unit_sha256':sources.get(owned[2]),'permanent_shared_unit_sha256':sources.get(owned[1]),'native_sha256':sources.get(owned[3]),'observer_sha256':row.get('observer_sha256'),'test_sha256':row.get('test_sha256')})
(public/'run-index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2))
for filename in ['assertion-and-observer-comparison.json','summary.json','run-index.json']:
    data=(public/filename).read_bytes();entries.append({'path':filename,'original_path':None,'original_sha256':None,'public_sha256':digest(data),'bytes':len(data),'transformations':[{'rule':'new derived explanatory metadata; original evidence unmodified'}],'image_viewed':None})
(public/'manifest.json').write_text(json.dumps({'artifact_base':artifact_base,'files':entries},ensure_ascii=False,indent=2))
sys.path.insert(0,str(root));from scripts.check_publication import inspect
flags={str(p.relative_to(public)):inspect(artifact_base+'/'+str(p.relative_to(public)),p.read_bytes()) for p in public.rglob('*') if p.is_file()};flags={p:v for p,v in flags.items() if v}
report={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':len(entries)+1,'status':'PASS' if not flags else 'FAIL','flags':flags,'manifest_sha256':digest((public/'manifest.json').read_bytes()),'scanner_source_sha256':digest((root/'scripts/check_publication.py').read_bytes()),'scope':'Bounded scanner plus explicit synthetic provenance/PNG visual review. Does not claim arbitrary private-data recognition.'}
(base/'public-package-v1-scan.json').write_text(json.dumps(report,indent=2));print(json.dumps({'package':str(public),**report},indent=2));sys.exit(bool(flags))
