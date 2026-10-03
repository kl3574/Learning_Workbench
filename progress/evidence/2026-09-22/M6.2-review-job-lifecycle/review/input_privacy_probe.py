import json
from pydantic import ValidationError
from services.api.app.application.review_models import ReviewJobInput
raw={'version':'draft-review-job-v1','workspace_id':'workspace_synthetic','review_id':'review_synthetic','source_kind':'import','candidate':{'draft_id':'draft_synthetic','draft_revision':1,'entity':'block','candidate_sha256':'a'*64},'request':{'expected_revision':1,'checks':['structure'],'reviewer_note':'zz_private_review_note'},'creator_session_id':'session_synthetic','rules_version':'draft-review-rules-v1','created_at':'2026-09-22T00:00:00Z'}
x=ReviewJobInput.model_validate(raw)
assert repr(x)=='ReviewJobInput()' and str(x)==''
assert x.model_dump(mode='json')==raw
for name,patch in [('unknown',{'unknown':'zz_private_review_note'}),('nested_candidate',{'candidate':{**raw['candidate'],'draft_revision':True}}),('unicode',{'request':{**raw['request'],'reviewer_note':'zz_private_review_note'+chr(0xd800)}})]:
 try:ReviewJobInput.model_validate({**raw,**patch})
 except ValidationError as e:assert 'zz_private_review_note' not in str(e)
 else:raise AssertionError(name)
print(json.dumps({'repr':'PASS','roundtrip':'PASS','safe_error_cases':3}))
