"""Generate synthetic, hash-valid author/learner packages from the embedded contracts.
Run after extracting domain_models.py to packages/contracts/. Does not access network.
Derived from PRODUCT_DESIGN.md v3.0.0 appendix E.
Source sha256: ab061119163b5b2a10411bb90d7cae45bf2e2b14082f4e9266f6c9452db3870c
"""
from __future__ import annotations
from pathlib import Path
import hashlib, sys, zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes as canonical
NOW='2026-09-14T00:00:00Z' # deterministic fixture timestamp, not a claim about user activity

def sha(data): return hashlib.sha256(data).hexdigest()
def safe_write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()!=data: raise RuntimeError(f'fixture differs, refusing overwrite: {path}')
    path.write_bytes(data)
def generate(destination:Path):
    # Models, not handwritten hash placeholders, produce the frozen object identities.
    payloads={}
    def text(path,value):
        data=value.encode('utf-8');payloads[path]=data;return sha(data)
    def put(path,obj):
        data=canonical(obj);payloads[path]=data
        return dm.ContentRef(entity=obj.entity,id=obj.id,revision=obj.revision,sha256=sha(data))
    concept=dm.Concept(id='concept_ols',revision=1,title='一维最小二乘',skill_dimensions=['compute','derive'])
    cref=dm.ContentRef(entity='concept',id=concept.id,revision=concept.revision,sha256=sha(canonical(concept)))
    body=r'''# 一维最小二乘的完整小例题

目标：在 $y_i=h_i\theta+e_i$ 中由已知 $h_i,y_i$ 估计实参数 $\theta$。
给定 $h=(1,2)$、$y=(2,4)$，使用损失 $L(\theta)=\sum_{i=1}^{2}(y_i-h_i\theta)^2$。
展开：$L(\theta)=(2-\theta)^2+(4-2\theta)^2=20-20\theta+5\theta^2$。
配方：$L(\theta)=5(\theta-2)^2$，因为实数平方非负，最小值在 $\hat\theta=2$ 唯一达到。
检查：$A=\sum h_i^2=5>0$，$B=\sum h_i y_i=10$，$B/A=2$。
边界：若所有 $h_i=0$，则损失与 $\theta$ 无关，不能宣称唯一估计。
小结：正的 $A$ 保证这个二次目标有唯一最小点；这不自动证明任意噪声下统计最优。
'''
    bh=text('content/block_ols.r1.md',body)
    block=dm.ContentBlock(id='block_ols',revision=1,kind='worked_example',title='含观测模型、逐步计算与边界检查的例题',body_path='content/block_ols.r1.md',body_sha256=bh,concepts=['concept_ols'])
    bref=put('blocks/block_ols.r1.json',block)
    lesson=dm.Lesson(id='lesson_ols',revision=1,title='从观测模型到最小二乘：一维参数的计算与唯一性',objectives=['逐步计算A、B和参数估计','检查唯一性条件'],block_refs=[bref])
    lref=put('lessons/lesson_ols.r1.json',lesson)
    qs=[dm.QuestionPublic(id='question_choice',revision=1,kind='single_choice',stem_markdown='以上例题中A是多少？',choices=[dm.Choice(id='opt_a',text_markdown='3'),dm.Choice(id='opt_b',text_markdown='5')],concept_ids=['concept_ols'],skill='compute',exposure_group='group_ols_A',input_instructions='选择一个选项'),
        dm.QuestionPublic(id='question_numeric',revision=1,kind='numeric',stem_markdown='以上例题中的B是多少？',concept_ids=['concept_ols'],skill='compute',exposure_group='group_ols_B',input_instructions='填写有限实数，无单位'),
        dm.QuestionPublic(id='question_calculation',revision=1,kind='calculation',stem_markdown='计算以上例题的参数估计并写出配方步骤。',concept_ids=['concept_ols'],skill='compute',exposure_group='group_ols_theta',input_instructions='填写最终值，步骤另存；本fixture自动评分仅对应最终数值')]
    qrefs=[dm.ContentRef(entity='question',id=q.id,revision=q.revision,sha256=sha(canonical(q))) for q in qs]
    payloads['questions/public.jsonl']=b''.join(canonical(q)+b'\n' for q in qs)
    solutions=[]
    for i,(qref,answer) in enumerate(zip(qrefs,['opt_b','10','2'])):
        sol=dm.SolutionPrivate(id=f'solution_{i}',revision=1,question_ref=qref,grading_kind='choice_exact' if i==0 else 'numeric_tolerance',accepted_answers=[answer],absolute_tolerance=0.0,relative_tolerance=0.0,solution_markdown='请参照本节逐步计算；此为合成测试材料，不代表已经人工审校。',review_status='needs_review')
        solutions.append(sol)
    payloads['private/solutions.jsonl']=b''.join(canonical(s)+b'\n' for s in solutions)
    practice=dm.PracticeSet(id='practice_ols',revision=1,title='A、B与参数估计练习',lesson_ref=lref,question_refs=qrefs)
    pref=put('practice/practice_ols.r1.json',practice)
    assessment=dm.AssessmentBlueprint(id='assessment_ols',revision=1,title='计算诊断（合成样例）',question_refs=qrefs,allowed_modes=['independent','assisted','open_book'])
    aref=put('assessments/assessment_ols.r1.json',assessment)
    course=dm.Course(id='course_ols',revision=1,title='一维含噪声参数估计：公式、计算、先修关系与独立作答',audience='自学者',lesson_refs=[lref],concept_refs=[cref],sections=[dm.CourseSection(id='section_one',title='第1章 观测与最小二乘',lesson_ids=[lesson.id])],objectives=['理解目标函数','完成确定性计算'])
    course_ref=put('course.json',course)
    payloads['concepts.json']=canonical([concept.model_dump(mode='json')])
    symbol=dm.Symbol(id='symbol_theta',tex=r'\theta',meaning='待估计标量参数',domain=r'\mathbb{R}',dimension='1',scope=course.id,first_definition=bref)
    payloads['symbols.json']=canonical([symbol.model_dump(mode='json')])
    payloads['sources/citations.json']=canonical([])
    payloads['checks/quality-receipt.json']=canonical({'schema_version':'3.0.0','fixture_only':True,'mathematical':'NOT_RUN','sources':'NOT_RUN','independent_pedagogy':'NOT_RUN','note':'Schema验证不是内容审核；禁止把本回执当作发布批准'})
    route=dm.Route(id='route_ols',revision=1,title='计算入门路线',goal='阅读、练习、自测',steps=[dm.RouteStep(id='step_read',title='阅读例题',target=lref,completion_rule='read'),dm.RouteStep(id='step_practice',title='练习',target=pref,requires_steps=['step_read'],completion_rule='practice_submitted'),dm.RouteStep(id='step_test',title='诊断',target=aref,requires_steps=['step_practice'],completion_rule='assessment_submitted')])
    safe_write(destination/'route.json',canonical(route))
    for profile in ['author','learner']:
        selected={k:v for k,v in payloads.items() if profile=='author' or not k.startswith('private/')}
        folder=destination/f'course-{profile}'
        entries=[]
        for path,data in sorted(selected.items()):
            media='text/markdown' if path.endswith('.md') else 'application/x-ndjson' if path.endswith('.jsonl') else 'application/json'
            entry=dm.FileEntry(path=path,size=len(data),sha256=sha(data),media_type=media,visibility='author_private' if path.startswith('private/') else 'learner')
            entries.append(entry);safe_write(folder/path,data)
        manifest=dm.Manifest(package_id=f'package_{profile}',profile=profile,created_at=NOW,files=entries)
        safe_write(folder/'manifest.json',canonical(manifest))
        # Files have deterministic bytes; ZIP header timestamps are also deterministic.
        zpath=destination/f'course-{profile}.learnpack.zip'
        if zpath.exists(): zpath.unlink() # only synthetic generated archive under destination
        with zipfile.ZipFile(zpath,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for f in sorted(folder.rglob('*')):
                if f.is_file():
                    info=zipfile.ZipInfo(str(f.relative_to(folder)),date_time=(2026,9,14,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                    z.writestr(info,f.read_bytes())
    request=dm.TutorRequest(thread_id='thread_ols',workspace_id='workspace_local',message='为什么A必须严格大于零？',intent='derive',context=dm.ViewContext(view_kind='lesson',active_ref=lref),web_search=False)
    safe_write(destination/'tutor-request.json',canonical(request))
    safe_write(destination/'fixture-summary.json',canonical({'course_ref':course_ref.model_dump(mode='json'),'question_count':len(qs),'fixture_only':True}))
    return destination
if __name__=='__main__':
    print(generate(ROOT/'fixtures'/'synthetic'))
