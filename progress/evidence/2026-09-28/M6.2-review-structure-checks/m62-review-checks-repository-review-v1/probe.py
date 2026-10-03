import json
from types import SimpleNamespace
from pydantic import ValidationError
from services.api.app.application.errors import ApiError
from services.api.app.application.review_checks import StructuralReviewReport, review_structure, ORDER
marker='synthetic-private-review-input'
results=[]
for requested in [False,True]:
 try:review_structure(SimpleNamespace(model_dump=lambda **_: {'private':marker}),requested=requested)
 except ApiError as error:
  assert error.code=='REVIEW_MATERIAL_INTEGRITY' and marker not in str(error)
  results.append({'case':'bad_material_requested_'+str(requested),'result':'safe_integrity_rejection'})
 else:raise AssertionError('bad material accepted')
raw={'version':'review-structure-report-v1','candidate':{'draft_id':'draft_fixture','draft_revision':1,'entity':'block','candidate_sha256':'a'*64},'material_descriptor_sha256':'b'*64,'requested':False,'structural':'NOT_RUN','checks':[{'code':code,'status':'NOT_RUN','detail_code':'not_requested'} for code in ORDER]}
result=StructuralReviewReport.model_validate(raw)
assert repr(result)=='StructuralReviewReport()' and all(repr(c)=='StructuralReviewCheck()' for c in result.checks)
results.append({'case':'unrequested_closed_report','result':'all_four_NOT_RUN_safe_repr'})
for field in ['raw_text','mathematical']:
 try:StructuralReviewReport.model_validate({**raw,field:marker})
 except ValidationError as error:
  assert marker not in str(error)
  results.append({'case':field,'result':'forbidden_safe_validation'})
 else:raise AssertionError('unknown verdict/prose field accepted')
print(json.dumps({'scope':'typed/pure safety probes; no DB/owner/approval proof','cases':results},indent=2))
