import { useEffect, useState } from 'react'
import type { ContentRef, RetrievalQueryView } from '../../../../../packages/contracts/generated/api-types'
import type { ReaderTarget } from '../reader/target'
import { canonical, normalizedRefs, readerPath } from './retrievalModel'
import { retrievalClient, type RetrievalPort } from './retrievalClient'
import { useRetrieval } from './useRetrieval'
import { SourcePanel } from '../reader/SourcePanel'
import './retrieval.css'
export type ScopeChoice = { label: string; ref: ContentRef }
const states: Record<RetrievalQueryView['index_state'], string> = { missing: '尚无索引', building: '已登记构建任务', stale: '原索引需要重新核验', ready: '索引已就绪' }
const results: Record<RetrievalQueryView['result_state'], string> = { not_ready: '尚未查询：索引未就绪', matched: '找到相关材料', no_match: '所选材料没有匹配', indexed_empty: '索引内没有可检索词', resource_omitted: '存在匹配，但完整材料超出返回预算' }
const jobStates = { queued: '排队中', running: '构建中', awaiting_approval: '等待确认', completed: '已完成', failed: '失败', cancelled: '已取消' }
export function RetrievalPanel({ workspace, paused, choices, initial, open, onState, port = retrievalClient }: {
  workspace: string; paused: boolean; choices: ScopeChoice[]; initial: ContentRef | null; open: (target: ReaderTarget) => void;
  onState: (value: { safe: boolean }) => void; port?: RetrievalPort;
}) {
  const [refs, setRefs] = useState<ContentRef[]>(() => initial ? [initial] : [])
  const [text, setText] = useState('')
  const data = useRetrieval(workspace, refs, paused, port)
  useEffect(() => { onState({ safe: data.safe }); return () => onState({ safe: true }) }, [data.safe, onState])
  const selectedKey = canonical(refs)
  const selectedCommands = data.commands.filter(command => canonical(command.scope_refs) === selectedKey)
  const unresolved = selectedCommands.filter(command => !command.ack && !command.rejected)
  const select = (value: ContentRef[]) => { if (data.busy) return; setRefs(normalizedRefs(value)) }
  if (paused) return <p role="status">当前策略暂不允许读取学科材料。原索引命令保留在本机；权限恢复后重新核验。</p>
  return <section className="retrieval-panel" aria-label="精确范围材料检索">
    <p>只查找你明确选择的本地公开材料。词法匹配分数不代表内容核验或学习掌握，不会调用模型。</p>
    <fieldset disabled={data.busy}><legend>明确选择检索范围</legend>
      {choices.map(choice => <label key={canonical(choice.ref)}><input type="radio" name="retrieval-scope" checked={refs.length === 1 && canonical(refs[0]) === canonical(choice.ref)} onChange={() => select([choice.ref])} />{choice.label} · {choice.ref.id} · r{choice.ref.revision}</label>)}
      {!choices.length && <p>请先在阅读区打开真实教材小节或内容块；也可明确恢复下方已有索引范围。</p>}
    </fieldset>
    {refs.length > 0 && <details><summary>本次完整范围引用（{refs.length} 项）</summary>{refs.map(ref => <p key={canonical(ref)}>{ref.entity} · {ref.id} · r{ref.revision}<code>{ref.sha256}</code></p>)}</details>}
    <div className="retrieval-actions"><button disabled={data.busy || !refs.length} onClick={() => void data.refresh()}>刷新范围与任务</button><button disabled={data.busy} onClick={() => void data.loadOverview()}>查看已登记索引</button></div>
    {data.overview && <section aria-label="已登记索引"><p>以下仅是各自登记事实，没有全工作区就绪状态。</p>{data.overview.items.map(item => <div key={item.scope_sha256}><p>{item.scope_refs.map(ref => `${ref.id} · r${ref.revision}`).join('、')}</p><button disabled={data.busy} onClick={() => select(item.scope_refs)}>明确选用此登记范围</button></div>)}{!data.overview.items.length && <p>尚无已登记索引。</p>}{data.overview.next_cursor && <button disabled={data.busy} onClick={() => void data.loadOverview(data.overview!.next_cursor!)}>下一页索引</button>}</section>}
    {data.status && <section aria-label="所选范围索引状态"><strong>{states[data.status.state]}</strong><details><summary>查看索引版本与核验摘要</summary><p>范围 SHA-256：<code>{data.status.scope_sha256}</code></p><p>当前材料描述：<code>{data.status.corpus_sha256}</code></p><p>已提交索引：{data.status.index_version ?? '无'}{data.status.indexed_corpus_sha256 && <code>{data.status.indexed_corpus_sha256}</code>}</p><p>构建时间：{data.status.last_built_at ?? '尚无完成事实'}</p></details></section>}
    <button className="primary-button" disabled={data.busy || !data.status || !data.safe || !!unresolved.length || data.status.state === 'building'} onClick={() => void data.begin('rebuild')}>明确按已读描述重建索引</button>
    {!!selectedCommands.length && <section aria-label="原索引命令"><details open={!!unresolved.length}><summary>原索引命令与回执（{selectedCommands.length}）</summary><p>原命令回执与当前任务分别记录。</p>{selectedCommands.map(command => <div key={command.command_id}><p>{command.kind === 'rebuild' ? '重建' : '取消'}命令：<code>{command.command_id}</code></p>{command.ack ? <p>原命令已确认：{jobStates[command.ack.status]}。当前状态另行回读。</p> : command.rejected ? <p>原基准已被服务端拒绝。刷新后可明确按新描述创建新命令。</p> : <button disabled={data.busy || !data.safe} onClick={() => void data.retry(command)}>重试原{command.kind === 'rebuild' ? '重建' : '取消'}命令</button>}</div>)}</details></section>}
    {data.commands.some(command => canonical(command.scope_refs) !== selectedKey && !command.ack && !command.rejected) && <section aria-label="其他范围未确认命令">{data.commands.filter(command => canonical(command.scope_refs) !== selectedKey && !command.ack && !command.rejected).map(command => <button key={command.command_id} disabled={data.busy} onClick={() => select(command.scope_refs)}>恢复原范围 {command.scope_refs.map(ref => `${ref.id} r${ref.revision}`).join('、')}</button>)}</section>}
    {data.job && <section aria-label="实际索引任务"><h3>任务当前读回：{jobStates[data.job.status]}</h3><p>{data.job.id} · r{data.job.revision} · {data.job.progress.label}</p><p>{data.job.progress.completed} / {data.job.progress.total ?? '未知'} 块</p>{data.job.error && <p role="alert">{data.job.error.code} · {data.job.error.message}</p>}{['queued', 'running', 'awaiting_approval'].includes(data.job.status) && <button disabled={data.busy || !!unresolved.length || !data.safe} onClick={() => void data.begin('cancel')}>明确取消当前索引任务</button>}</section>}
    <form onSubmit={event => { event.preventDefault(); void data.query(text) }}><label>检索词<input aria-label="检索词" value={text} onChange={event => setText(event.target.value)} disabled={data.busy} /></label><button disabled={data.busy || !refs.length || !text.trim()}>查询所选材料</button></form>
    {data.busy && <p role="status">正在读取或处理原命令…</p>}
    {(data.error || data.storageError) && <p role="alert">{data.error || data.storageError}</p>}
    {data.view && <section aria-label="检索结果"><h3>{results[data.view.result_state]}</h3><p>索引状态：{states[data.view.index_state]} · 完整匹配：{data.view.matched_count ?? '未查询'} · 返回：{data.view.hits.length}</p><p>完整块遗漏：数量限制 {data.view.omissions.result_limit}、正文预算 {data.view.omissions.text_byte_budget}、响应预算 {data.view.omissions.json_byte_budget}。</p>{data.view.warnings.map((warning, index) => <p key={index}>{warning.code} · {warning.message}</p>)}
      {data.view.hits.map(hit => <article key={canonical(hit.ref)} className="retrieval-hit"><h4>{hit.title} · r{hit.ref.revision}</h4><p>来自所选未审材料，不代表内容已核验。匹配分数 {hit.score.toFixed(3)}。</p><p>当前指针：{hit.current_ref.id} · r{hit.current_ref.revision} · {hit.lifecycle === 'archived' ? '已归档，保留原修订' : '未归档'}</p><code>{hit.locator}</code><pre aria-label={`完整原文：${hit.title}`}>{hit.text}</pre><details><summary>精确来源与父链</summary><p>来源状态：{hit.provenance.state === 'frozen' ? '绑定冻结来源记录' : '来源尚未解析'}；不代表原件现时可下载。</p>{hit.provenance.original && <p>{hit.provenance.original.media_type} · {hit.provenance.original.size} 字节<code>{hit.provenance.original.sha256}</code></p>}{hit.provenance.citations.map(citation => <p key={citation.id}>{citation.title} · {citation.verification}<code>{citation.source_sha256 ?? '引用没有来源哈希'}</code></p>)}{hit.provenance.warnings.map((warning, index) => <p key={index}>{warning.code} · {warning.message}</p>)}{hit.parent_paths.map((path, index) => <div key={index}><p>{[path.course_title, path.lesson_title, hit.title].filter(value => value !== null).join(' / ')}</p><p>{[path.root_ref, path.course_ref, path.lesson_ref, path.block_ref].filter(value => value !== null).map(ref => `${ref!.entity}:${ref!.id}@r${ref!.revision}#${ref!.sha256}`).join(' → ')}</p>{readerPath(path) ? <button disabled={data.busy || !data.safe} onClick={() => { if (data.safe && !paused) open(readerPath(path)!) }}>沿此完整教材路径打开</button> : <p>此范围没有完整教材父链，不推测父级。</p>}</div>)}</details>{hit.warnings.map((warning, index) => <p key={index}>{warning.code} · {warning.message}</p>)}<button disabled={data.busy} onClick={() => void data.inspect(hit.ref)}>回读此精确块与来源</button></article>)}
    </section>}
    {data.block && <section aria-label="独立精确块只读查看"><h3>{data.block.block.title} · r{data.block.block_ref.revision}</h3><p>此查看不推测父教材、不切换其他修订，也不记录学习完成。</p><pre>{data.block.body}</pre><SourcePanel value={data.block} refresh={() => { if (data.block) void data.inspect(data.block.block_ref) }} /></section>}
  </section>
}
