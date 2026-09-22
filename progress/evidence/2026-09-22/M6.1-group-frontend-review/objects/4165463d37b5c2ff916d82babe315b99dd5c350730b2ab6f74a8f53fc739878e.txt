import { useState } from 'react'
import type { ApprovalDecision, AuthoringGroupNumericCheckView, NumericCheckView, NumericPlan } from '../../../../../packages/contracts/generated/api-types'
export function NumericPlanDisplay({ plan }: { plan: NumericPlan }) {
  return <section aria-label="完整算术计划"><h4>完整算术计划</h4><p>使用有限 binary64 运算；单位只是标签，不检查维度相容或换算，随机种子为 null。</p>
    <table><caption>全部变量</caption><thead><tr><th>变量</th><th>值</th><th>单位</th></tr></thead><tbody>{plan.variables.map(v => <tr key={v.name}><td>{v.name}</td><td>{v.value}</td><td>{v.unit}</td></tr>)}</tbody></table>
    {plan.assertions.map(v => <article key={v.id}><h5>{v.id}</h5><p>表达式：<code>{v.expression}</code></p><p>期望 {v.expected}；actual 与 expected 单位标签：{v.unit}</p><p>绝对容差 {v.atol}；相对容差 {v.rtol}</p></article>)}
  </section>
}
export function NumericCheckPanel({ value, busy, commandExists = false, decide, refresh }: { value: NumericCheckView | AuthoringGroupNumericCheckView; busy: boolean; commandExists?: boolean; decide: (body: ApprovalDecision) => void; refresh: () => void }) {
  const identity = `${value.id}:${value.revision}:${value.operation_sha256}`
  const [confirmation, setConfirmation] = useState<string | null>(null), confirmed = confirmation === identity
  const runtime = value.runtime
  return <section aria-label="独立数值执行批准"><h3>单独批准本机算术复算</h3><p>数值 PASS 只表示本次计划按记录的输入与容差通过；不证明正文与计划对应、推导正确或来源已审。</p>
    <p>当前决定：{value.decision}{value.expired ? ' · 预览已过期' : ''} · r{value.revision}</p><p>有效期：{value.created_at} 至 {value.expires_at}</p>
    {'target' in value && <p>本次组内成员：{value.target.member_key} · {value.target.entity} · <code>{value.target.member_sha256}</code></p>}
    <NumericPlanDisplay plan={value.plan} />
    <section aria-label="本次隔离范围"><h4>本次隔离与资源范围</h4><p>仅本机隔离计算，不联网，不读取工作区、个人文件或提供商秘密；缺可靠隔离时阻断，不回退到普通 Python。</p><p>wall {runtime.wall_seconds} 秒；CPU {runtime.cpu_seconds} 秒；内存 {runtime.memory_bytes} bytes；输出 {runtime.output_bytes} bytes；计算进程上限 {runtime.evaluator_process_limit}</p><p>解释器 {runtime.python_version}；沙箱 {runtime.sandbox_version}；{runtime.evaluator_version}</p><p>计算器 SHA256 <code>{runtime.evaluator_sha256}</code></p><p>运行文件清单 SHA256 <code>{runtime.runtime_manifest_sha256}</code></p><p>本次操作 SHA256 <code>{value.operation_sha256}</code></p></section>
    {value.decision === 'pending' && <><label><input type="checkbox" checked={confirmed} disabled={busy || commandExists || value.expired} onChange={e => setConfirmation(e.target.checked ? identity : null)} />我已核对全部变量、表达式、容差、候选与本机隔离范围，单独批准这一次执行</label><button disabled={busy || commandExists || !confirmed || value.expired} onClick={() => decide({ decision: 'approve_once', expected_revision: value.revision, operation_sha256: value.operation_sha256 })}>明确批准本次数值执行</button><button disabled={busy || commandExists} onClick={() => decide({ decision: 'decline', expected_revision: value.revision, operation_sha256: value.operation_sha256 })}>明确拒绝本次数值执行</button></>}
    {commandExists && <p>本次检查已有保留的原决定命令，请回放原命令或另行读取当前状态，不创建第二份决定。</p>}
    <button disabled={busy} onClick={refresh}>另行读取数值检查当前状态</button>
    {value.job && <p>实际检查任务：{value.job.id} · {value.job.status} · r{value.job_revision}。可在安全列表取消；取消不抹掉已经执行的事实。</p>}
    {value.result ? <section aria-label="实际数值结果"><h4>实际数值结果：{value.result.verdict}</h4><p>{value.result.outcome} · 开始 {value.result.started_at ?? '未知／未取得'} · 结束 {value.result.finished_at} · 退出码 {value.result.exit_code ?? '未知／未取得'}</p>{value.result.assertions.map(v => <p key={v.id}>{v.id}：实际 {v.actual ?? '未取得有限结果'} · {v.passed ? '通过' : '未通过'} {v.error_code}</p>)}<p>数学审校 NOT_RUN；来源审校 NOT_RUN；独立教学审校 NOT_RUN。草稿尚未发布。</p><details><summary>执行记录哈希</summary><p>input {value.result.input_sha256}</p><p>output {value.result.output_sha256 ?? '没有取得完整输出'}</p><p>result {value.result.result_sha256}</p></details></section> : <p>尚未读到该实际任务的最终检查结果，未推断执行成功。</p>}
    {value.warnings.map((v, i) => <p key={i}>{v.code}：{v.message}</p>)}
  </section>
}
