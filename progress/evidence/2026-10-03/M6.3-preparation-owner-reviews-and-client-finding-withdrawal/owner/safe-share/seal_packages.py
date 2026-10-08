import hashlib, importlib.util, json, re, subprocess
from pathlib import Path
BASE=Path('$HOME/.cache/learning-workbench-acceptance')
OWNER=BASE/'m63-turn-preparation-owner-oct04'
E=BASE/'m63-turn-owner-evidence-oct04'
UI=BASE/'m63-current-session-client-oct04'
R=BASE/'m63-current-session-static-40925d27-oct04'
R.mkdir(exist_ok=False)
def sha(data): return hashlib.sha256(data).hexdigest()
def write(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def git(root,*args): return subprocess.check_output(['git',*args],cwd=root)
# Add the terminal result only; all original gate logs/maps/receipts stay unchanged.
history=json.loads((E/'GATE_HISTORY.json').read_text())
receipt=json.loads((E/'related-final/receipt.json').read_text())
log=(E/'related-final/run.log').read_bytes()
history['stages'].append({'stage':'related-final',**{k:receipt[k] for k in ['head','exit_code','before_equals_after','source_count','elapsed_seconds']},'summary':[x for x in log.decode().splitlines() if re.match(r'^\d+ passed,',x)],'raw_log_sha256':sha(log)})
write(E/'GATE_HISTORY.json',history)
(E/'REPORT.md').write_text('''# Codex turn preparation/control owner — fixed local slice

Source: `6f3f8107991c9fd35460d1617597988a3c6aa09d`, base `de7e21dd046e2c70d11aa95c80f6f69d308de4e8`, sole PRODUCT_DESIGN v3.0.15 SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`.

Four real HTTP operations now prepare and read turn metadata. Preparation atomically creates the real codex_turn Job/Run/context and session activity slot. It freezes original actor, exact complete request, trusted Content and Provider facts, and immutable original ACK. No CLI, model, external Provider, tool, grant or dispatch is invoked. Without a complete runtime/profile InputProof the actual saved preparation is unavailable. Capability flags remain false. This is not complete M6.3 acceptance.

Cancellation records the requested and terminal release revisions in one immutable checked event (ready r2 → prepare r3 → request r4 → release r5). Jobs/Run terminal is unique; replay and terminal new-key observations do not advance it. Current session GET is independent of the original bootstrap create ACK. Whole history/member/head, hashed creation order, retained selected Content bytes/provenance including oversized omitted refs, complete Provider history, and actual Job/Run bindings are checked. GETs use query_only reads and a fresh delivery access check after the prior WAL snapshot closes.

Fixed final gate: 13 files, **416 PASS**, two dependency deprecation warnings, pytest 234.02 seconds, runner exit 0. All 1403 non-progress tracked input maps before/after equal their fixed Git bytes. Ruff, mypy (259 sources), generation check (82), spec verification (54 core / 147 declared routes), and standalone strict TypeScript all exit 0 on the same source. Runtime routes are 120 with 27 declared but unregistered operations; unsupported endpoints were not stubbed. Previous narrower owner gate: 46 PASS. Synthetic bootstrap runtime supplies old mapped-session setup; this is not an actual CLI or model run.

Preserved original failures and counterexamples are enumerated in GATE_HISTORY.json: genuine initial 404; first fixture/rollback mismatches; cancel +1 instead of +2 and Provider damaged-history status; three same-byte 5a counterexamples for unchecked member order, oversized damaged body omission, and read delivery after actual role withdrawal; safe-error/legacy migration fixture mistakes; and the old GET response-class oracle. The original 5a counterexample file hash is identical to final source. Final gate includes all these regressions plus concurrent prepare/cancel, Policy exclusion, rollback, cross-workspace/actor, source/provider damage, read-only controls, migration and original ACK bytes. Original failed logs remain private and are never reclassified by later passes.

red-01 is a harness NOT_RUN (wrong uv executable path), not a product failure. The test-edit attempt before owner-05 raised SyntaxError and the shell continued; that repeated three existing test failures and is explicitly preserved. WIP typing/lint failures are retained. Early per-stage runner byte snapshots were not retained: current run_gate.py is not asserted to reproduce its earlier red-01/red-02/owner-01/owner-02 bytes. Actual commands and complete before/after maps were retained. The final related runner copy and static runner are retained; UTC labels, where present, and monotonic durations are distinct.

RAW_MANIFEST covers explicitly listed original text/JSON evidence, not private synthetic databases or basetemps. SAFE_SHARE alone authorizes candidate copying, with exact $HOME prefix replacement to $HOME; original SHA256 remains attached. Failed run logs are withheld because synthetic credential-bearing fixture representations can occur. GATE_HISTORY preserves their failure names/counts and original hashes without payload. No screenshots, database, credential, environment dump, or generic archive is a candidate. VERIFY.py reads only sealed files and Git objects; it runs no application/tests/CLI/model.
''')
# Independent UI static review: selected fixed sources only, no application run.
base='764090fa7312565955bc7e781f2f279bf40f9d04'; head='40925d27af4ca4e49a444d8c6d2a40dcb2b20769'
paths=git(UI,'diff','--name-only',base+'...'+head).decode().splitlines()
assert len(paths)==4 and not git(UI,'status','--porcelain')
extra=['AGENTS.md','PRODUCT_DESIGN.md','services/api/app/codex_turn_dto.py','services/api/app/codex_bootstrap_dto.py','apps/web/src/features/providers/providerSchema.ts','apps/web/src/features/codex/bootstrapCommands.ts','apps/web/src/features/codex/bootstrapMemory.ts','packages/contracts/generated/codex-bootstrap-schemas.json','packages/contracts/generated/codex-turn-schemas.json']
rows={}
for path in paths+extra:
 data=git(UI,'show',head+':'+path); rows[path]={'git_blob':git(UI,'rev-parse',head+':'+path).decode().strip(),'sha256':sha(data),'bytes':len(data)}
(R/'reviewed.patch').write_bytes(git(UI,'diff',base+'...'+head))
unchanged=['apps/web/src/features/codex/bootstrapCommands.ts','apps/web/src/features/codex/bootstrapMemory.ts','services/api/app/codex_bootstrap_dto.py','packages/contracts/generated/codex-bootstrap-schemas.json']
assert all(git(UI,'show',base+':'+p)==git(UI,'show',head+':'+p) for p in unchanged)
write(R/'SOURCE_BINDINGS.json',{'base':base,'head':head,'tree':git(UI,'rev-parse',head+'^{tree}').decode().strip(),'clean':True,'changed_paths':paths,'selected_sources':rows,'unchanged_legacy_paths':unchanged,'commands':['git diff '+base+'...'+head,'git log '+base+'..'+head+' --oneline'],'execution':'STATIC_ONLY; zero application/CLI/test/model/browser runs','reviewer_count':1,'parallel_attempt':'Standards subagent spawn rejected: agent thread limit reached; both axes reviewed by the same independent reviewer'})
(R/'REVIEW.md').write_text('''# Independent static review: current session client

Fixed `40925d27af4ca4e49a444d8c6d2a40dcb2b20769`, base `764090fa7312565955bc7e781f2f279bf40f9d04`; clean at readback. Four files, 85 added / 8 removed lines. Sole PRODUCT_DESIGN v3.0.15, SHA256 b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec. This reviewer authored none of this UI delta. No application, browser, CLI, test or model execution was performed. An attempted parallel Standards reviewer was rejected by the thread limit; this is one independent reviewer covering two axes, not two independent subagents.

## Standards

0 confirmed findings. AGENTS makes the sole spec normative. The narrow independent current-projection type/schema is appropriate to this seam; three production changes and one meaningful regression file do not introduce a material Fowler-smell finding. Generated contract artifacts and shared validator remain unchanged. No tooling-enforced formatting issues are claimed.

## Spec

0 confirmed findings. PRODUCT_DESIGN.md:1432,1645,1647 require original bootstrap ACK bytes/decoder to remain fixed and current session metadata to reflect turn history without granting execution. bootstrapClient.ts:33–59 selects the independent generated CodexCurrentSessionView schema and matches the Python DTO cross-field conditions (codex_turn_dto.py:411–433): ready revision>=2, original r2 null/false, initializing r1 null/false, failed/unknown r2 null/false. Required fields, exact booleans, Id grammar, no extra fields and safe Unicode strings use the unchanged strict validator. The old ACK branch remains unchanged; bootstrapCommands, bootstrapMemory, old Python DTO and old generated schema are byte-identical to base.

bootstrapClient.ts:72 changes only current GET decode. useBootstrap.ts:119–129 still checks exact session ID/adapter binding and the original valid(token) fence before publishing the linked state. Workspace/access/port/store/unmount, actor/Policy and fresh-session write guards at lines12,21–62,65–103 and canReplay remain unchanged. Current flags only reach panel text at CodexBootstrapPanel.tsx:46 and never feed allowed/writable/execute/replay; true flags do not grant permissions (§20.17.3 line1647).

The new regression reads actual GET transport shape with no key/body, rejects damaged current records and widening of old ACK decoders, retains original DraftStore text, and asserts no prepare/decide/create calls when rendering checked current controls. It also statically covers all-true current flags and released slots. These are meaningful test designs, but this review does not independently rerun them or claim the author's 1068-test gate. Narrow delta only; unchanged runtime/bootstrap concerns and broader turn execution remain outside review.

Standards: 0 confirmed findings. Spec: 0 confirmed findings. This is static closure of current-session UI compatibility only, not implementation or end-to-end M6.3 acceptance.
''')
# Shared packaging: no raw failure log content becomes a candidate.
spec=importlib.util.spec_from_file_location('scanner',OWNER/'scripts/check_publication.py'); scanner=importlib.util.module_from_spec(spec); spec.loader.exec_module(scanner)
def record(root,path):
 data=(root/path).read_bytes(); return {'path':path,'sha256':sha(data),'bytes':len(data)}
def package(root,raw_paths,candidates):
 raw=[record(root,p) for p in raw_paths]
 write(root/'RAW_MANIFEST.json',{'version':'explicit-raw-evidence-v1','count':len(raw),'files':raw,'excluded':'all databases, basetemp, tmp, runtime data and unlisted files'})
 out=root/'safe-share';out.mkdir(exist_ok=True)
 safe=[]; excluded=[]
 for p in candidates:
  data=(root/p).read_bytes(); derived=data.replace(b'$HOME',b'$HOME')
  issues=scanner.inspect('progress/evidence/review/'+p,derived)
  if re.search(rb'(?i)(?:authorization|x-csrf-token|cookie)[\"\x27]?\s*[:=]\s*[\"\x27]?[A-Za-z0-9_+/=-]{16,}',derived): issues.append('header value')
  if issues: excluded.append({'path':p,'sha256':sha(data),'reasons':issues}); continue
  target=out/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(derived)
  safe.append({'path':p,'raw_sha256':sha(data),'public_sha256':sha(derived),'raw_bytes':len(data),'public_bytes':len(derived),'transformation':'exact $HOME -> $HOME' if data!=derived else 'raw-identical'})
 write(root/'SAFE_SHARE.json',{'version':'explicit-safe-candidates-v1','count':len(safe),'files':safe,'excluded_candidates':excluded,'not_authorized':'No glob copy; only files listed here and the explicit outer allowlist.'})
 return excluded
stages=['red-01','red-02','owner-01','cancel-revision-red','owner-02','review-5a-red','owner-03','owner-04','owner-05','owner-06','legacy-route-red','related-final','static-final']
raw=['SOURCE_BINDINGS.json','GATE_HISTORY.json','REPORT.md','development-checks.json','test-edit-attempt.json','run_gate.py','static_runner.py','seal_packages.py','generate-01.log','mypy-01.log','mypy-02.log','mypy-03.log','mypy-04.log','ruff-02.log','ruff-03.log','ruff-04.log','ruff-05.log','ruff-06.log']
for stage in stages:
 for name in ['before.json','after.json','receipt.json','run.log','HARNESS_ERROR.json','runner.py','ruff.log','mypy.log','generated.log','spec.log','types.log']:
  path=stage+'/'+name
  if (E/path).is_file():raw.append(path)
candidates=[p for p in raw if not (p.endswith('/run.log') and p.split('/')[0] in ['red-02','owner-01','cancel-revision-red','review-5a-red','owner-04','owner-05','legacy-route-red'])]
print(json.dumps({'owner_exclusions':package(E,raw,candidates),'ui_exclusions':package(R,['SOURCE_BINDINGS.json','REVIEW.md','reviewed.patch'],['SOURCE_BINDINGS.json','REVIEW.md','reviewed.patch'])}))
