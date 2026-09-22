import { lazy, Suspense } from 'react'
import type { AuthoringContentPlan, AuthoringDraftMemberRef, AuthoringGroupDraftView, AuthoringPrivateSolutionView } from '../../../../../packages/contracts/generated/api-types'
import { NumericPlanDisplay } from './NumericCheckPanel'
const Markdown = lazy(() => import('../../shared/Markdown').then(module => ({ default: module.Markdown })))

export function GroupPlan({ value }: { value: AuthoringContentPlan }) {
  return <section aria-label="冻结的内容计划"><h4>冻结的内容计划</h4><p>服务端先校验并保存本次完整回答中的计划，再按计划校验候选。目标索引覆盖属于结构检查；目标达成、先修充分性与教学效果尚未独立审查。</p><ol>{value.entries.map(entry => <li key={entry.member_key}>{entry.entity === 'block' ? entry.title : `题目 ${entry.member_key}`} · {entry.kind}<p>学习目标：{entry.objective_indexes.map(index => value.objectives[index]).join('；') || '未分配'}；先修：{entry.prerequisite_indexes.map(index => value.prerequisites[index]).join('；') || '未分配'}；组内依赖：{entry.depends_on_keys.join('、') || '无'}</p></li>)}</ol></section>
}
export function AuthoringGroupDraft({ value, solution, busy, readSolution, preview, refresh, readNumeric }: { value: AuthoringGroupDraftView; solution: AuthoringPrivateSolutionView | null; busy: boolean; readSolution: (member: string) => void; preview: (member: AuthoringDraftMemberRef) => void; refresh: () => void; readNumeric: (id: string) => void }) {
  const limited = value.numeric_check_ids.length >= 100
  return <section aria-label="组合草稿候选"><h3>{value.root.title}</h3><p>草稿 · r{value.candidate.draft_revision} · 尚未发布。所有组内成员与私有答案绑定同一份候选。</p>
    <GroupPlan value={value.content_plan} />
    <Suspense fallback={<p role="status">正在排版组合草稿…</p>}>
      {value.blocks.map(block => {
        const member = value.root.entity === 'lesson' ? value.root.blocks.find(ref => ref.member_key === block.member_key) : undefined
        return <article key={block.member_key}><h4>{block.payload.title}</h4><Markdown sourceKey={`authoring-${value.candidate.draft_id}-${block.member_key}`}>{block.payload.body_markdown}</Markdown><details><summary>核对正文、来源与符号声明</summary><pre>{block.payload.body_markdown}</pre><pre>{JSON.stringify({ member, source_refs: block.payload.declared_source_refs, symbols: block.payload.symbols }, null, 2)}</pre></details>{block.payload.kind === 'worked_example' && <><NumericPlanDisplay plan={block.payload.numeric_plan} /><button disabled={busy || limited || !member} onClick={() => { if (member) preview(member) }}>为例题 {block.payload.title} 准备独立数值预览</button></>}</article>
      })}
      {value.questions.map((question, index) => <article key={question.member_key}><h4>第 {index + 1} 题 · {question.kind}</h4><Markdown sourceKey={`authoring-${value.candidate.draft_id}-${question.member_key}`}>{question.stem_markdown}</Markdown>{question.choices.map(choice => <div key={choice.id}>{choice.id}：<Markdown>{choice.text_markdown}</Markdown></div>)}<p>作答格式：{question.input_instructions} · 最高分 {question.max_score}</p><button disabled={busy} onClick={() => readSolution(question.member_key)}>明确读取第 {index + 1} 题的私有解答草稿</button></article>)}
      {solution && <section aria-label="私有解答草稿"><h4>已明确读取的私有解答 · {solution.payload.question.member_key}</h4><p>需审查；题目与解答的结构绑定不代表答案唯一或评分语义已验证。</p><Markdown>{solution.payload.answer.solution_markdown}</Markdown><h5>评分说明</h5><Markdown>{solution.payload.answer.rubric_markdown}</Markdown><details><summary>核对私有答案、规则与准确绑定</summary><pre>{JSON.stringify(solution, null, 2)}</pre></details>{solution.payload.answer.numeric_plan ? <><NumericPlanDisplay plan={solution.payload.answer.numeric_plan} /><button disabled={busy || limited} onClick={() => preview(solution.payload.question)}>为这份准确题目解答准备独立数值预览</button></> : <p>此解答未提供可运行数值计划。</p>}</section>}
    </Suspense>
    <p>预览只准备待批准操作。此候选累计保留 {value.numeric_check_ids.length} / 100 份预览，已拒绝或过期的预览仍计入。</p><button disabled={busy} onClick={refresh}>刷新组合候选的检查记录</button>{value.numeric_check_ids.map(id => <button key={id} disabled={busy} onClick={() => readNumeric(id)}>读取组数值检查 {id}</button>)}
    <p>Schema {value.validation.schema}；计划成员 {value.validation.plan_membership}；私有答案绑定 {value.validation.private_bindings}。数学、来源与独立教学审校均 NOT_RUN。</p>
    {value.validation.question_checks.map(check => <p key={check.question.member_key}>{check.question.member_key}：评分规则结构 {check.grading_compatibility}；答案集合结构 {check.accepted_answer_membership}。答案唯一性、干扰项合理性、条件充分性、单位语义、解答与评分语义、目标对齐和先修充分性均 NOT_RUN。</p>)}
    <details><summary>核对完整候选身份与成员</summary><pre>{JSON.stringify({ candidate: value.candidate, plan_ref: value.plan_ref, root: value.root, private_solution_refs: value.private_solution_refs }, null, 2)}</pre></details>
  </section>
}
