import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { ContentRef } from '../../../../../packages/contracts/generated/api-types'
import { getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import { useAuthoring } from './useAuthoring'
import { authoringClient, type AuthoringPort } from './authoringClient'
import { AuthoringControlList } from './AuthoringControlList'
import { AuthoringGroupDraft, GroupPlan } from './AuthoringGroupDraft'
import { AuthoringForm } from './AuthoringForm'
import { AuthoringConsent } from './AuthoringConsent'
import { NumericCheckPanel, NumericPlanDisplay } from './NumericCheckPanel'
import type { ProviderPort } from '../providers/providerClient'
import './authoring.css'
export function AuthoringPanel({ workspace, paused, currentBlock, onState, port = authoringClient, provider }: { workspace: string; paused: boolean; currentBlock: ContentRef | null; onState: (value: { dirty: boolean; safe: boolean }) => void; port?: AuthoringPort; provider?: ProviderPort }) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  const state = useAuthoring(workspace, paused, port), [formDirty, setFormDirty] = useState(false), [consentState, setConsentState] = useState({ dirty: false, safe: true })
  const callback = useRef(onState); callback.current = onState
  useEffect(() => { if (!state.academic) { setFormDirty(false); setConsentState({ dirty: false, safe: true }) } }, [state.academic, workspace, access])
  const dirty = state.academic && formDirty || consentState.dirty || state.commands.some(v => !v.ack), safe = state.ready && !state.busy && consentState.safe
  useEffect(() => { callback.current({ dirty, safe }) }, [dirty, safe])
  const detail = state.detail, draft = state.draft, numeric = state.numeric
  return <div className="authoring-panel"><p>可以准备例题、教材小节、习题集与测试题组草稿。模型调用与数值执行分别授权；数学、来源与教学质量均待审查。</p>
    <button disabled={state.busy} onClick={() => void state.refresh()}>刷新安全任务列表与当前权限</button>
    {state.error && <p role="status">{state.error}</p>}
    <AuthoringControlList jobs={state.jobs} busy={state.busy || !state.controlReady} academic={state.academic} read={id => void state.read(id)} cancel={job => void state.cancel(job)} />
    {state.cursor && <button disabled={state.busy} onClick={() => void state.refresh(true)}>继续读取安全任务</button>}
    <section aria-label="原创作命令回执"><h3>本机保留的原命令</h3>{state.commands.map(command => <article key={command.command_id}><p>{command.kind === 'cancel' ? '取消任务' : command.kind === 'prepare' ? '准备例题' : command.kind === 'group_prepare' ? '准备组合草稿' : ['numeric_preview', 'group_numeric_preview'].includes(command.kind) ? '数值检查预览' : '独立数值决定'} · {command.ack ? '原命令已确认' : command.rejection ? '服务端拒绝，保留原基准' : '结果未知，原 key 与完整命令保留'}</p><details><summary>核对原命令</summary><p>{command.command_id}</p>{command.kind !== 'cancel' && <pre>{JSON.stringify(command.body, null, 2)}</pre>}{command.ack && <p>原回执不是当前状态。请从任务列表重新读取；数值检查从原候选的检查列表进入。</p>}</details><button disabled={state.busy || !(command.kind === 'cancel' ? state.controlReady : state.ready) || !!command.ack} onClick={() => void state.execute(command)}>回放原命令 {command.command_id}</button></article>)}</section>
    {!state.academic ? <p role="status">当前只开放安全任务控制。主题、材料、候选、数值输入与结果已收起；请在作者会话且当前测试策略允许后明确重新读取。</p> : <div key={`${workspace}:${access}`}>
      <AuthoringForm currentBlock={currentBlock} busy={state.busy || !state.ready} submit={body => state.create({ kind: 'prepare', body })} submitGroup={port.groups ? body => state.create({ kind: 'group_prepare', body }) : undefined} denied={state.reportAccessError} onDirty={setFormDirty} />
      {detail && <section aria-label="受保护创作详情"><h3>{detail.summary.title}</h3><p>实际任务状态：{detail.summary.status} · r{detail.summary.job_revision}</p><button disabled={state.busy} onClick={() => void state.read(detail.summary.id)}>重新读取本次创作任务</button>
        <details><summary>完整原教学要求与实际材料</summary><pre>{JSON.stringify(detail.request, null, 2)}</pre><p>实际包装字符数 {detail.preparation.character_count}，不是 token 计数。</p>{!detail.preparation.materials.length && <p>无已选教材来源。</p>}{detail.preparation.materials.map(v => <article key={`${v.ref.id}:${v.ref.revision}`}><h4>{v.title} · 材料未审</h4><pre>{JSON.stringify(v, null, 2)}</pre></article>)}</details>
        {detail.preparation.warnings.map((v, i) => <p key={i}>{v.code}：{v.message}</p>)}
        {'variant' in detail && <><details><summary>本次明确选择的已有目标</summary>{detail.preparation.targets.map(target => <p key={`${target.ref.entity}:${target.ref.id}:${target.ref.revision}`}>{target.metadata.title} · {target.ref.entity} · r{target.ref.revision}</p>)}</details>{detail.content_plan && <GroupPlan value={detail.content_plan} />}</>}
        <AuthoringConsent key={`${detail.summary.id}:${workspace}:${access}`} workspace={workspace} value={detail} refresh={() => void state.read(detail.summary.id)} denied={state.reportAccessError} onState={setConsentState} port={provider} />
        <section aria-label="原生成输出"><h4>原模型输出，未逐项核验</h4><pre>{detail.raw_answer ?? '尚未取得回答原文。'}</pre>{detail.raw_refusal !== null && <><h4>原拒答</h4><pre>{detail.raw_refusal}</pre></>}<p>提供商终态 {detail.provider_outcome ?? '未知／尚无'}；输入 tokens {detail.usage.input_tokens ?? '未知'}；输出 tokens {detail.usage.output_tokens ?? '未知'}</p><p>Schema {detail.validation.schema}；引用声明 {detail.validation.references}；符号声明 {detail.validation.symbol_declarations}。数学、来源与独立教学审校均 NOT_RUN。</p>{detail.validation.issues.map((v, i) => <p key={i}>{v.code}：{v.message}</p>)}{detail.error_code && <p>{detail.error_code}</p>}</section>
        {detail.summary.candidate && <button disabled={state.busy} onClick={() => void state.readDraft()}>{'variant' in detail ? '读取这份准确组合候选' : '读取这份准确例题候选'}</button>}
      </section>}
      {draft && !('root' in draft) && <section aria-label="例题草稿候选"><h3>{draft.payload.title}</h3><p>状态 draft · r{draft.candidate.draft_revision}；尚未发布。检查通过不授予数学或来源审核。</p><pre aria-label="完整候选正文">{draft.payload.body_markdown}</pre><details><summary>准确候选、来源与符号声明</summary><pre>{JSON.stringify({ candidate: draft.candidate, body_sha256: draft.body_sha256, source_refs: draft.payload.declared_source_refs, symbols: draft.payload.symbols }, null, 2)}</pre></details><NumericPlanDisplay plan={draft.payload.numeric_plan} /><button disabled={state.busy || !state.ready || draft.numeric_check_ids.length >= 100} onClick={() => void state.create({ kind: 'numeric_preview', draft_id: draft.candidate.draft_id, body: { candidate: draft.candidate } })}>明确准备独立数值检查预览</button><p>预览不执行；需另一次明确批准。此候选已保留 {draft.numeric_check_ids.length} / 100 份预览。</p><button disabled={state.busy} onClick={() => void state.readDraft()}>刷新候选的检查记录</button>{draft.numeric_check_ids.map(id => <button key={id} disabled={state.busy} onClick={() => void state.readNumeric(id)}>读取数值检查 {id}</button>)}</section>}
      {draft && 'root' in draft && <AuthoringGroupDraft value={draft} solution={state.privateSolution} busy={state.busy || !state.ready} readSolution={member => void state.readPrivateSolution(member)} preview={target => void state.create({ kind: 'group_numeric_preview', draft_id: draft.candidate.draft_id, member_key: target.member_key, body: { candidate: draft.candidate, target } })} refresh={() => void state.readDraft()} readNumeric={id => void state.readNumeric(id)} />}
      {numeric && <NumericCheckPanel key={`${numeric.id}:${numeric.revision}:${numeric.operation_sha256}`} value={numeric} busy={state.busy || !state.ready} commandExists={state.commands.some(v => (v.kind === 'numeric_decision' || v.kind === 'group_numeric_decision') && v.check_id === numeric.id && (!v.rejection || !!v.ack))} decide={body => void state.create({ kind: 'target' in numeric ? 'group_numeric_decision' : 'numeric_decision', check_id: numeric.id, body })} refresh={() => void state.readNumeric(numeric.id)} />}
    </div>}
  </div>
}
