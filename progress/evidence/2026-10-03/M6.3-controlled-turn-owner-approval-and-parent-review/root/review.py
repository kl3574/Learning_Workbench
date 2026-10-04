import datetime,hashlib,json,subprocess
from pathlib import Path
B=Path('$HOME/.cache/learning-workbench-acceptance');P=B/'m63-turn-contract-proposal-oct04';R=B/'m62-public-safe-oct02';O=Path(__file__).parent
sha=lambda b:hashlib.sha256(b).hexdigest()
H='4e8d4f79f7090af997b48926a0a9050fe2170b7d';F='docs/proposals/m63-controlled-turn-approvals-artifacts.md'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip()==H
assert not subprocess.check_output(['git','status','--porcelain'],cwd=P)
assert sha((P/F).read_bytes())=='f1877e0ae083a036dc1b338fdb6f72f130f64160667a5704ec4ba9e608a43e52'
assert subprocess.check_output(['git','show',H+':'+F],cwd=P)==(P/F).read_bytes()
assert sha((R/'PRODUCT_DESIGN.md').read_bytes())=='bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144'
assert not (O/'READBACK.json').exists()
review={'status':'ROOT_STATIC_DESIGN_REVIEW_NO_CONFIRMED_BLOCKER','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'proposal_commit':H,'proposal_sha256':sha((P/F).read_bytes()),'source_base':'b3bbf8d9c4a1c9065be501497ba9b7117a21acf2','current_source':'4ecc27a883782855a6e5611d7610979e4b4b05ca','sole_spec_sha256':sha((R/'PRODUCT_DESIGN.md').read_bytes()),'read_scope':'Full 382-line proposal; selected normative session/bootstrap/budget/approval/AC21 contracts; actual main composition, RequestPreparer, Jobs owner dispatch and bootstrap routes. Backend/contracts/migrations unchanged b3bb to4ecc. Not complete engineering-map or runtime validation.','standards':'Closed named DTOs/owner ports, original ACK decoding, forward migrations and read-only GET retained. No second normative package adopted.','spec':'New semantics explicitly unapproved: current session turn projection, named Codex grants and strict operation/artifact readbacks. Existing bootstrap grant never reused as model/tool permit. AC21 safety/import-to-draft bounds retained.','tradeoff':'One complete model request per turn; tool feedback needing second model call fails before transmission. Explicit new turn+input+grant needed. This does not promise an uninterrupted autonomous Agent loop or whole M6.3 acceptance.','proof_boundary':'Production complete raw-input proof/interception/resource-enforcement remain unproven; zero external model calls. Existing user authorization to test Agent remains, but this review does not invent a proof or waive product per-request consent.','approval':'NOT_APPROVED; no canonical spec/code/remote change by this review','boundary':'Independent parent static design review after author self-review; no implementation tests, CLI/system probes, models or account operations.'}
(O/'READBACK.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(review,ensure_ascii=False))
