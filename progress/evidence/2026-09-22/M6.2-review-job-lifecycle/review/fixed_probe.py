from pathlib import Path
import json,sys,tempfile
root=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-review-job-lifecycle-active');sys.path.insert(0,str(root))
from services.api.app.application.errors import ApiError
from services.api.app.infrastructure.authoring_job_repository import AuthoringJobRepository
from services.api.app.infrastructure.review_job_repository import ReviewJobRepository
from tests.integration.test_review_job_lifecycle import prepared,create
from tests.integration.test_authoring_numeric_provider_history import table_hashes

if __name__ == '__main__':
    rows=[]
    with tempfile.TemporaryDirectory(prefix='review-job-fixed-independent-') as tmp:
        gen=prepared.__wrapped__(Path(tmp));case=next(gen);database,identity,value=create(case)
        before=table_hashes(database)
        with database.connect() as conn:
            try:ReviewJobRepository(conn,identity.workspace_id).claim(value.review_id)
            except ApiError as e:assert e.code=='TRANSACTION_REQUIRED'
            else:raise AssertionError('autocommit claim admitted')
        assert table_hashes(database)==before
        rows.append({'case':'autocommit_claim','result':'REJECTED_ZERO_PERSISTENT_CHANGE'})
        with database.transaction() as conn:
            authoring=AuthoringJobRepository(conn,identity.workspace_id)
            authoring.create('job_cross_owner','authoring',{'version':'synthetic_lifecycle_only'})
        before=table_hashes(database)
        with database.transaction() as conn:
            authoring=AuthoringJobRepository(conn,identity.workspace_id)
            row=authoring.load('job_cross_owner')
            try:ReviewJobRepository(conn,identity.workspace_id).transition(row,'cancelled',cancel=True,result={'synthetic':True})
            except ApiError as e:assert e.code=='JOB_MISSING'
            else:raise AssertionError('wrong consumer admitted')
        assert table_hashes(database)==before
        rows.append({'case':'wrong_consumer_caught_and_outer_commit','result':'REJECTED_ZERO_PERSISTENT_CHANGE'})
        with database.transaction() as conn:
            repo=ReviewJobRepository(conn,identity.workspace_id);lease=repo.claim(value.review_id)
            conn.execute('CREATE TEMP TABLE outer_work(value INTEGER NOT NULL)')
            conn.execute('INSERT INTO outer_work VALUES(1)')
            current=repo.load(value.review_id)
            for target in ['awaiting_approval','completed','running']:
                try:repo.transition(current,target)
                except ApiError:pass
                else:raise AssertionError('invalid transition admitted')
                assert dict(repo.load(value.review_id))==dict(current)
                assert conn.execute('SELECT value FROM outer_work').fetchall()[0][0]==1
                rows.append({'case':'invalid_'+target,'result':'REJECTED_ORIGINAL_ROW_RETAINED_OUTER_TRANSACTION_RETAINED'})
            conn.execute('INSERT INTO outer_work VALUES(2)')
            repo.transition(current,'completed',result={'synthetic_control_fact':True})
            assert [x[0] for x in conn.execute('SELECT value FROM outer_work ORDER BY value')]==[1,2]
            try:repo.transition(current,'cancelled',result={'synthetic':True})
            except ApiError:pass
            else:raise AssertionError('stale row admitted')
            assert repo.snapshot(value.review_id).status=='completed'
        with database.transaction(immediate=False) as conn:
            assert ReviewJobRepository(conn,identity.workspace_id).snapshot(value.review_id).status=='completed'
            assert AuthoringJobRepository(conn,identity.workspace_id).snapshot('job_cross_owner').status=='awaiting_approval'
            assert conn.execute('SELECT count(*) FROM reviews').fetchone()[0]==0
        rows.append({'case':'valid_following_transition_and_stale_row','result':'SINGLE_TERMINAL_CURRENT_OWNER_ONLY_NO_REVIEW_RECEIPT'})
        try:next(gen)
        except StopIteration:pass
    Path(__file__).with_suffix('.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps(rows,indent=2))
