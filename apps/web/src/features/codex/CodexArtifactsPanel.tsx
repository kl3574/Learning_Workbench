import { useEffect, useRef, useState } from 'react'
import type { DraftStore } from '../../workbench/DraftStore'
import { sameValue } from '../providers/providerSchema'
import { ImportWorkflow } from '../imports/ImportWorkflow'
import type { RecoveryId } from '../imports/recovery'
import type { ArtifactPort } from './artifactClient'
import { useCodexArtifacts } from './useCodexArtifacts'
export type ArtifactsPanelState = { dirty: boolean; safe: boolean; isolated: boolean; discardForms?: () => void }
export function CodexArtifactsPanel({ workspace, writeAdmitted, port, store, formStore, onState }: {
 workspace: string; writeAdmitted: boolean; port?: ArtifactPort; store?: DraftStore; formStore?: DraftStore; onState?: (value: ArtifactsPanelState) => void
}) {
 const state = useCodexArtifacts(workspace, writeAdmitted, port, store, formStore), callback = useRef(onState); callback.current = onState
 const [preview, setPreview] = useState<{ workspace: string; actor: string; target: RecoveryId } | null>(null)
 const [previewState, setPreviewState] = useState<{ dirty: boolean; safe: boolean; discardForms?: () => void }>({ dirty: false, safe: true })
 const previewAllowed = state.allowed && preview?.workspace === workspace && preview.actor === state.actor
 const dirty = state.dirty || previewState.dirty, safe = state.safe && previewState.safe, isolated = state.isolated && previewState.safe
 useEffect(() => { callback.current?.({ dirty, safe, isolated, discardForms: previewState.discardForms }) }, [dirty, safe, isolated, previewState.discardForms])
 const m = state.manifest, selection = state.fields.selection, using = !!m && !!selection && sameValue(selection.basis, m)
 const open = async (id: string) => { const actor = state.actor, target = await state.openPreview(id); if (target && actor) setPreview({ workspace, actor, target }) }
 return <section aria-label="Codex 产物清单与回导">
  <h3>产物清单与明确选择回导</h3>
  <p>仅显示服务端保存的受检产物。默认没有真实模型证明或执行器时不会产生清单；无清单不代表执行成功。</p>
  <button disabled={state.busy} onClick={() => void state.refresh()}>读取产物记录与权限</button>
  <button disabled={state.busy || !state.canSave} onClick={() => void state.saveMemory()}>仅保存产物本机事实</button>
  {state.retained > 0 && <p role="status">有 {state.retained} 项原 actor 的命令或表单尚在隔离内存；离开前请保存本机事实。</p>}
  {state.error && <p role="alert">{state.error}</p>}{state.message && <p role="status">{state.message}</p>}
  {!state.allowed ? <p>清单、选择与回导详情仅当前作者且测试策略允许后可读取。原表单与未知命令保留，没有自动 POST。</p> : <>
   <label>产物来源 session ID<input value={state.fields.session_id} disabled={state.busy} onChange={e => state.edit({ session_id: e.target.value })} /></label>
   <label>产物来源 turn ID<input value={state.fields.turn_id} disabled={state.busy} onChange={e => state.edit({ turn_id: e.target.value })} /></label>
   <button disabled={state.busy || !state.fields.session_id || !state.fields.turn_id} onClick={() => void state.read()}>独立读取当前产物清单</button>
   <details><summary>恢复本机原选择表单</summary>{state.forms.map(form => <button key={form.snapshot_id} disabled={state.busy} onClick={() => void state.restore(form)}>恢复产物表单 {form.draft_id} · {form.sequence}</button>)}</details>
   {m && <section aria-label="当前产物清单 GET">
    <p>来源 turn：{m.manifest.turn_id}；真实来源终态：<strong>{m.manifest.source_outcome}</strong>。受检扫描 PASS 不证明内容正确。</p>
    <p>数学审校 {m.manifest.mathematical}；来源核验 {m.manifest.sources}；独立教学审校 {m.manifest.independent_pedagogy}。</p>
    <p>清单 SHA-256：<code style={{ overflowWrap: 'anywhere' }}>{m.manifest_sha256}</code>；总计 {m.manifest.total_bytes} 字节。</p>
    {m.manifest.source_outcome === 'unknown' && <p role="status">来源副作用未可靠封闭，只可诊断和受控下载，禁止回导。</p>}
    {!m.manifest.entries.length && <p>没有可用产物，不能回导。</p>}
    <button disabled={state.busy || !m.manifest.entries.some(e => e.import_kind !== null && e.size > 0) || m.manifest.source_outcome === 'unknown'} onClick={state.chooseManifest}>使用此清单建立新选择</button>
    <ul>{m.manifest.entries.map(entry => <li key={entry.artifact_id}>
     <label><input type="checkbox" aria-label={`选择产物 ${entry.logical_path}`} checked={using && selection!.artifact_ids.includes(entry.artifact_id)} disabled={state.busy || !using || entry.import_kind === null || entry.size === 0 || m.manifest.source_outcome === 'unknown'} onChange={e => state.select(entry.artifact_id, e.target.checked)} />{entry.logical_path}</label>
     <p>{entry.media_type} · {entry.size} 字节 · 扫描 {entry.scan} · {entry.import_kind ?? '仅下载，不支持回导'}</p>
     <code style={{ overflowWrap: 'anywhere' }}>{entry.sha256}</code>
     <button disabled={state.busy} onClick={() => void state.download(entry)}>受控下载 {entry.logical_path}</button>
    </li>)}</ul>
    {m.manifest.excluded.length > 0 && <details><summary>被排除的项</summary>{m.manifest.excluded.map(e => <p key={e.entry_id}>{e.entry_id} · {e.reason}</p>)}</details>}
   </section>}
   {selection && <section aria-label="原清单选择"><p>保存的选择绑定清单 SHA-256：<code style={{ overflowWrap: 'anywhere' }}>{selection.basis.manifest_sha256}</code>；原来源终态 {selection.basis.manifest.source_outcome}。</p>
    <p>数学、来源、独立教学审校均 NOT_RUN。以下文件只准备 Import 预览，不代表已审、已入库或已发布。</p>
    <ul>{selection.artifact_ids.map(id => <li key={id}>{selection.basis.manifest.entries.find(e => e.artifact_id === id)!.logical_path} · {id}</li>)}</ul>
    <button disabled={state.busy || !state.canSubmit} onClick={() => void state.submit()}>明确新建所选产物的回导预览</button>
   </section>}
   <section aria-label="原回导命令与 ACK">{state.commands.map(command => <article key={command.command_id}>
    <p>{command.command_id} · {command.ack ? '原 202 ACK 已保存' : command.error ? `原命令收到 ${command.error.status}；基准保留` : '结果未知；原 key 与完整选择保留'}</p>
    <details><summary>核对原回导命令与回执</summary><pre>{JSON.stringify(command, null, 2)}</pre></details>
    <button disabled={state.busy || !state.canReplay(command)} onClick={() => void state.execute(command)}>显式回放回导原 key {command.command_id}</button>
    {command.ack && <><p>原聚合 Job {command.ack.id} · {command.ack.status}。这是永久原 ACK，当前状态另读。</p><button disabled={state.busy} onClick={() => void state.readImports(command)}>读取回导当前子项 {command.ack.id}</button></>}
   </article>)}</section>
   {state.aggregate && <section aria-label="回导聚合当前 GET"><h4>回导聚合与 Import 子项</h4><p>聚合 Job {state.aggregate.view.job.id} · {state.aggregate.view.job.status}；原 actor {state.aggregate.view.actor_session_id}。</p>
    <p>聚合 completed 仅表示预览准备完成，不授予人工质量批准。</p>
    <ol>{state.aggregate.view.items.map(item => <li key={item.artifact_id}><p>{item.artifact_id} → Import {item.import_id}；子 Job {item.job.id} · {item.job.status}</p><code style={{ overflowWrap: 'anywhere' }}>{item.source_sha256}</code>
     <button disabled={state.busy || !!preview} onClick={() => void open(item.import_id)}>打开普通 Import 预览 {item.import_id}</button></li>)}</ol>
   </section>}
  </>}
  {preview && <div hidden={!previewAllowed}>
   <p>已进入普通 Import 流程。请明确读取原候选；任何后续确认或审核仍需单独操作。</p>
   {previewState.dirty && <button disabled={!previewState.safe} onClick={() => previewState.discardForms?.()}>保留原回导事实，丢弃当前预览临时设置</button>}
   <button disabled={!previewState.safe || previewState.dirty} onClick={() => setPreview(null)}>关闭普通 Import 预览</button>
   <ImportWorkflow workspaceId={preview.workspace} paused={!previewAllowed} requestedImport={preview.target} close={() => { if (previewState.safe && !previewState.dirty) setPreview(null) }} onState={setPreviewState} />
  </div>}
 </section>
}
