from pathlib import Path
import json,sys,tempfile
root=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-review-job-lifecycle-active');sys.path.insert(0,str(root))
from services.api.app.application.errors import ApiError
from services.api.app.infrastructure.authoring_job_repository import AuthoringJobRepository
from services.api.app.infrastructure.review_job_repository import ReviewJobRepository
from tests.integration.test_review_job_lifecycle import prepared,create
if __name__ == '__main__':
    results=[]
    with tempfile.TemporaryDirectory(prefix='review-job-independent-') as tmp:
     gen=prepared.__wrapped__(Path(tmp))
     case=next(gen);database,identity,value=create(case)
     # No transaction: an inherited write currently succeeds and autocommits.
     with database.connect() as conn:
      assert not conn.in_transaction
      repo=ReviewJobRepository(conn,identity.workspace_id)
      lease=repo.claim(value.review_id)
      row=repo.load(value.review_id)
      results.append({'probe':'claim_without_caller_transaction','in_transaction_after':conn.in_transaction,'status':row['status'],'revision':row['revision'],'event_count':conn.execute('SELECT count(*) FROM job_events WHERE job_id=?',(value.review_id,)).fetchone()[0]})
     # A forbidden review transition is detected after UPDATE and event append.
     with database.transaction() as conn:
      repo=ReviewJobRepository(conn,identity.workspace_id)
      before=conn.total_changes
      try:repo.transition(repo.load(value.review_id),'awaiting_approval')
      except ApiError as e:code=e.code
      else:code='NO_ERROR'
      row=conn.execute('SELECT status,revision FROM jobs WHERE id=?',(value.review_id,)).fetchone()
      results.append({'probe':'catch_forbidden_review_transition_inside_caller_transaction','raised':code,'changes_before_error':conn.total_changes-before,'status_at_commit':row['status'],'revision_at_commit':row['revision']})
     with database.transaction(immediate=False) as conn:
      try:ReviewJobRepository(conn,identity.workspace_id).load(value.review_id)
      except ApiError as e:results[-1]['subsequent_checked_read_error']=e.code
     # A row from the other same-workspace consumer can be modified before rejection.
     with database.transaction() as conn:
      authoring=AuthoringJobRepository(conn,identity.workspace_id)
      authoring.create('job_cross_owner','authoring',{'version':'synthetic_lifecycle_only'})
      row=authoring.load('job_cross_owner');before=conn.total_changes
      try:ReviewJobRepository(conn,identity.workspace_id).transition(row,'cancelled',cancel=True,result={'synthetic':True})
      except ApiError as e:code=e.code
      else:code='NO_ERROR'
      results.append({'probe':'review_transition_on_checked_authoring_row','raised':code,'changes_before_error':conn.total_changes-before})
     with database.transaction(immediate=False) as conn:
      row=AuthoringJobRepository(conn,identity.workspace_id).load('job_cross_owner')
      results[-1].update(persisted_authoring_status=row['status'],persisted_authoring_revision=row['revision'])
     try:next(gen)
     except StopIteration:pass
    out=Path(__file__).parent/'probes.json';out.write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))
