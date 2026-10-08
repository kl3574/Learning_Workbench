"""Pure fixed-Git byte comparison; no product execution or checkout mutation."""
from pathlib import Path
import subprocess,re,hashlib,json
repo=Path('$HOME/.cache/learning-workbench-acceptance/m63-review-history-timing-oct05')
base='35aebd3039241abb3393300affd593f4826a4a0c';head='c02e9e5c73d7da5e8e1617731fbefdf94f44f0e8'
git=lambda *args:subprocess.check_output(['git',*args],cwd=repo)
owned='tests/e2e/review.spec.ts'
assert git('rev-parse',head+'^').decode().strip()==base
assert git('diff','--name-only',base,head).decode().splitlines()==[owned]
a=git('show',base+':'+owned).decode();b=git('show',head+':'+owned).decode()
first="test('real history and exact material review";second="test('a delayed old review response"
assert a[:a.index(first)]==b[:b.index(first)] and a[a.index(second):]==b[b.index(second):]
x=b[:b.index(second)];old=a[:a.index(second)]
x=re.sub(r'^  // BEGIN REVIEW_HISTORY_TIMING_OBSERVER:.*?^  // END REVIEW_HISTORY_TIMING_OBSERVER\n','',x,count=1,flags=re.M|re.S)
x=x.replace('  try {\n','',1)
phases=re.findall(r"timingPhase\('([^']+)'\)",x)
x=re.sub(r"^  timingPhase\('[^']+'\)\n",'',x,flags=re.M)
for phase in ['reload-returned','review-tab-clicked','mobile-viewport-set']:
 x=x.replace("; timingPhase('"+phase+"');",';',1)
i=x.index('  } finally {');end=x.rfind('\n})');assert i<end
x=x[:i]+x[end+1:];assert x==old and len(phases)==43
sha=lambda v:hashlib.sha256(v).hexdigest()
print(json.dumps(dict(source=head,base=base,first_span_exact_after_removing_only_observer=True,first_span_sha256=sha(old.encode()),second_span_byte_exact=True,second_span_sha256=sha(a[a.index(second):].encode()),phase_calls=43,new_product_test_execution=False),indent=2))
