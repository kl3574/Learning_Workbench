from pathlib import Path
import json,subprocess,hashlib
BASE=Path(__file__).resolve().parent;ROOT=BASE.parent/'m62-active';HEAD='1fffd996e9334f7f28dcdeb970430c9aa4052ee3';FOUNDATION='416b53261dafa0ddbdec3adf4ef2deab058b866b'
git=lambda *args:subprocess.check_output(['git',*args],cwd=ROOT)
origins={}
# The storage worktree branched before the Tutor test repair. Its delta from
# FOUNDATION therefore includes a reversal; only the four authored storage paths
# are adopted. The original erroneous attribution was rejected, never accepted.
for name in ['migrations/0017_review_history.sql','tests/integration/test_review_storage_migration.py','tests/integration/test_review_storage_constraints.py','docs/adr/0023-review-history-storage.md']:
 origins[name]='4bf176de1cdf0a76cdf0fa965027ec3a5367551f'
for ancestor,endpoint in [('72e4e64','d1bc330'),(FOUNDATION,'9d5f4d6'),(FOUNDATION,'347312c'),('4bf176de','9fff7cc'),('72e4e64','f18c92c'),(FOUNDATION,'ab11b811')]:
 for name in git('diff','--name-only',ancestor,endpoint).decode().splitlines():
  if name.startswith('progress/'):continue
  if endpoint=='9fff7cc' and name in ['services/api/app/application/review_checks.py','tests/integration/test_review_structure_checks.py']:continue
  origins[name]=git('rev-parse',endpoint).decode().strip()
rows=[]
for name in git('ls-tree','-r','--name-only',HEAD).decode().splitlines():
 if name.startswith('progress/'):continue
 actual=git('show',HEAD+':'+name);origin=origins.get(name,FOUNDATION);expected=git('show',origin+':'+name)
 assert actual==expected,(name,origin)
 rows.append(dict(path=name,origin_commit=origin,bytes=len(actual),sha256=hashlib.sha256(actual).hexdigest(),actual_git_bytes_identical=True))
assert len(rows)==981
(BASE/'composition-binding.json').write_text(json.dumps(dict(code_commit=HEAD,source_count=len(rows),actual_git_blobs_read=len(rows)*2,files=rows,scope='Actual corrected source composition, not inherited test success. Initial ancestry-mapping guard failure retained separately.'),indent=2)+'\n')
print('PASS: 981 engineering inputs, 1962 actual Git blobs; corrected explicit storage origin mapping')
