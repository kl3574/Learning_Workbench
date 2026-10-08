"""Read only approved nonsecret state columns from two proven synthetic fixture DBs."""
from contextlib import closing
from pathlib import Path
import hashlib,json,re,sqlite3
E=Path(__file__).parent
BASE=Path('$HOME/.cache/lw-m63-dcf-oct03/pytest')
proof=json.loads((E/'mapping.json').read_text())
assert proof['inputs_unchanged'] and len(proof['failed_selected'])==2
queries={
 'jobs': "SELECT kind,status,revision,cancel_requested,retry_count,next_retry_at,lease_owner IS NOT NULL AS has_lease_owner,lease_until,created_at,updated_at,json_extract(result_json,'$.error_code') AS error_code,json_extract(result_json,'$.error.code') AS nested_error_code FROM jobs ORDER BY created_at,kind",
 'imports': "SELECT status,created_at FROM ingestion_imports ORDER BY created_at",
 'job_event_counts': "SELECT type,count(*) AS count,min(occurred_at) AS first_at,max(occurred_at) AS last_at FROM job_events GROUP BY type ORDER BY type"}
result=[]
for node,folder in proof['failed_selected'].items():
 directory=BASE/folder/'data';db=directory/'workspace.sqlite3'
 assert all(not x.is_symlink() for x in (BASE,BASE/folder,directory,db))
 assert db.resolve()==db and db.is_file()
 assert not (directory/'workspace.sqlite3-wal').exists()
 assert not (directory/'workspace.sqlite3-shm').exists()
 before=(db.stat().st_ino,db.stat().st_size,db.stat().st_mtime_ns)
 contents=sorted(x.name for x in directory.iterdir())
 with closing(sqlite3.connect(db.as_uri()+'?mode=ro&immutable=1',uri=True)) as connection:
  connection.row_factory=sqlite3.Row
  connection.execute('PRAGMA query_only=ON')
  assert connection.execute('PRAGMA query_only').fetchone()[0]==1
  connection.execute('BEGIN')
  data={name:[dict(row) for row in connection.execute(query)] for name,query in queries.items()}
  for job in data['jobs']:
   for key in ('error_code','nested_error_code'):
    value=job[key]
    assert value is None or (isinstance(value,str) and re.fullmatch('[A-Z][A-Z0-9_]{0,79}',value))
  assert connection.total_changes==0
  connection.rollback()
 assert before==(db.stat().st_ino,db.stat().st_size,db.stat().st_mtime_ns)
 assert contents==sorted(x.name for x in directory.iterdir())
 result.append({'nodeid':node,'synthetic_basetemp_subdirectory':folder,'query_only':True,'read_only_immutable_uri':True,
  'database_and_directory_stat_unchanged':True,'rows':data})
output={'source_head':proof['fixed_head'],'association_receipt_sha256':hashlib.sha256((E/'mapping.json').read_bytes()).hexdigest(),
 'queries':queries,'cases':result,
 'limits':'No input/body/credential/actor/command/receipt/ledger document read or output. No DB bytes copied or hashed. No process or test body executed. State read after completed full gate; no timing cause inference or recovery attempted.'}
(E/'safe-metadata.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'case_count':len(result),'query_only':True,'source_unchanged':True}))
