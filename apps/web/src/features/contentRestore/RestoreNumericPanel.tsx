import { useEffect, useRef, useState } from 'react'
import type { ContentRestoreDraftSnapshot } from '../../../../../packages/contracts/generated/api-types'
import type { RestoreNumericMaterialView } from '../../../../../packages/contracts/generated/restore-numeric-types'
import { NumericCheckPanel, NumericPlanDisplay } from '../authoring/NumericCheckPanel'
import { RestoreNumericMaterialEditor } from './RestoreNumericMaterialEditor'
import { useRestoreNumeric } from './useRestoreNumeric'
import type { RestoreNumericPort } from './restoreNumericClient'
import { discardRestoreNumericMemory } from './restoreNumericMemory'
import { useAuthoring } from '../authoring/useAuthoring'
import { AuthoringControlList } from '../authoring/AuthoringControlList'

function RestoreNumericControls({ workspace, onState }: { workspace: string; onState: (value: { dirty: boolean; safe: boolean }) => void }) {
  // Keep the existing owner-neutral Jobs controls available even when academic
  // payload is hidden. This hook is always in controls-only mode here.
  const controls = useAuthoring(workspace, true)
  const dirty = controls.commands.some(command => command.kind === 'cancel' && !command.ack && !command.rejection), safe = controls.controlReady && !controls.busy
  useEffect(() => { onState({ dirty, safe }) }, [onState, dirty, safe])
  return <section aria-label="恢复数值任务安全控制"><button disabled={controls.busy} onClick={() => void controls.refresh()}>重新读取已有数值任务安全列表</button>
    {controls.error && <p role="status">{controls.error}</p>}
    <AuthoringControlList jobs={controls.jobs.filter(job => job.kind === 'authoring_numeric_check')} busy={controls.busy || !controls.controlReady} academic={false} read={() => undefined} cancel={job => void controls.cancel(job)} />
    {controls.cursor && <button disabled={controls.busy} onClick={() => void controls.refresh(true)}>继续读取数值任务安全列表</button>}
    {controls.commands.filter(command => command.kind === 'cancel').map(command => <p key={command.command_id}>取消命令 {command.command_id} · {command.ack ? '原取消回执已保存' : command.rejection ? '原取消被拒绝，请另读当前任务' : '原取消结果未知，请在创作任务中核对原命令'}</p>)}
  </section>
}

export function RestoreNumericMaterialDisplay({ value }: { value: RestoreNumericMaterialView }) {
  return <section aria-label="实际冻结的恢复数值材料"><h4>本候选唯一冻结的数值材料</h4>
    <p>候选 {value.candidate.draft_id} · r{value.candidate.draft_revision} · <code>{value.candidate.candidate_sha256}</code></p>
    <p>材料 SHA256 <code>{value.numeric_material_sha256}</code>；原恢复记录 <code>{value.restore_record_sha256}</code>；原文 SHA256 <code>{value.body_sha256}</code></p>
    <p>提供理由：{value.material.reason}</p>
    {value.material.symbols.map(symbol => <p key={symbol.name}>符号 {symbol.name} · {symbol.tex} · 取值域 {symbol.domain} · 量纲 {symbol.dimension}</p>)}
    <NumericPlanDisplay plan={value.material.plan} />
    {value.material.variable_bindings.map(binding => <article key={binding.variable_name}><h5>变量 {binding.variable_name} 原文定位</h5><p>[{binding.value_source.start_codepoint}, {binding.value_source.end_codepoint})</p><pre>{binding.value_source.quote}</pre></article>)}
    {value.material.assertion_bindings.map(binding => <article key={binding.assertion_id}><h5>断言 {binding.assertion_id} 原文定位</h5>
      <p>公式 [{binding.expression_source.start_codepoint}, {binding.expression_source.end_codepoint})</p><pre>{binding.expression_source.quote}</pre>
      <p>期望值 [{binding.expected_source.start_codepoint}, {binding.expected_source.end_codepoint})</p><pre>{binding.expected_source.quote}</pre>
    </article>)}
    <p>精确定位不证明公式翻译、变量含义、单位和覆盖充分；仍须本次明确人工审核。更改冻结材料须另建恢复候选。</p>
  </section>
}
export type RestoreNumericStatus = { dirty: boolean; safe: boolean; closeSafe: boolean }
export function RestoreNumericPanel({ workspace, blockId, draft, paused, onState, port }: {
  workspace: string; blockId: string; draft: ContentRestoreDraftSnapshot | null; paused: boolean; onState?: (value: RestoreNumericStatus) => void; port?: RestoreNumericPort
}) {
  const state = useRestoreNumeric(workspace, blockId, paused, port), callback = useRef(onState); callback.current = onState
  const [discardingForm, setDiscardingForm] = useState(false), [discardingMemory, setDiscardingMemory] = useState(false)
  const [controlState, setControlState] = useState({ dirty: false, safe: false })
  const dirty = state.pendingForm || state.pendingMemory || controlState.dirty || state.commands.some(command => !command.ack && !command.rejection)
  const safe = !state.busy && !state.pendingMemory && controlState.safe
  useEffect(() => { callback.current?.({ dirty, safe, closeSafe: safe && !state.pendingForm }) }, [dirty, safe, state.pendingForm])
  useEffect(() => {
    if (!dirty && safe) return
    const guard = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', guard); return () => window.removeEventListener('beforeunload', guard)
  }, [dirty, safe])
  return <section className="restore-numeric-panel" aria-label="恢复例题独立数值复算"><h3>恢复例题的独立数值复算</h3>
    <p>仅对当前明确读取的恢复例题准备本机有限算术。预览、执行批准、实际运行和新的人审分别记录；不会自动发布。</p>
    {state.busy && <p role="status">正在核对数值材料与原记录…</p>}{state.error && <p role="alert">{state.error}</p>}
    {state.pendingMemory && <><p role="alert">原数值命令或 ACK 尚未落盘，隔离保留在本页；请保持页面打开。</p><button disabled={state.busy} onClick={() => setDiscardingMemory(true)}>明确放弃未落盘数值记录</button></>}
    {state.canSaveMemory && <button disabled={state.busy} onClick={() => void state.saveMemory()}>保存原会话的数值内存记录</button>}
    {discardingMemory && <div role="dialog" aria-label="放弃未落盘数值记录"><p>仅丢弃当前工作区的未落盘数值原命令或回执；已保存记录和服务端事实不变，不能恢复此内存。</p><button disabled={state.busy} onClick={() => { discardRestoreNumericMemory(workspace); setDiscardingMemory(false) }}>确认放弃未落盘数值记录</button><button onClick={() => setDiscardingMemory(false)}>继续保留数值记录</button></div>}
    {state.pendingForm && <><p>本页保留了未提交的数值材料及原依据；不会自动换基准或执行。</p>
      {!state.form && <button disabled={state.busy || !state.canRestoreForm} onClick={() => void state.restoreForm()}>重新核验并恢复原数值材料表单</button>}
      <button disabled={state.busy} onClick={() => setDiscardingForm(true)}>明确放弃未提交数值表单</button></>}
    {discardingForm && <div role="dialog" aria-label="放弃未提交数值表单"><p>明确丢弃本工作区此块的未提交手填数值材料；不删原命令、冻结材料或运行记录。</p><button disabled={state.busy} onClick={() => { state.discardForm(); setDiscardingForm(false) }}>确认放弃未提交数值表单</button><button onClick={() => setDiscardingForm(false)}>继续保留数值表单</button></div>}
    {!state.ready ? <p>当前数值材料、计划与结果已收起。安全任务列表仍可另行读取和取消任务；权限恢复后需要明确重新读取。</p> : <>
      <button disabled={!safe || state.pendingForm || !draft || draft.proposed_block.kind !== 'worked_example'} onClick={() => { if (draft) void state.select(draft) }}>重新读取这份恢复例题的数值材料</button>
      {state.snapshot && <>
        <p>实际候选 {state.snapshot.candidate.draft_id} · {state.snapshot.state} · <code>{state.snapshot.candidate.candidate_sha256}</code>；已保存预览 {state.snapshot.numeric_check_ids.length}/100。</p>
        <pre aria-label="数值核验对应的完整恢复正文">{state.snapshot.body_markdown}</pre>
        {state.snapshot.numeric_material && <RestoreNumericMaterialDisplay value={state.snapshot.numeric_material} />}
        {state.form && <RestoreNumericMaterialEditor body={state.snapshot.body_markdown} value={state.form} disabled={!safe || !state.canPreview} change={state.changeForm} />}
        <button disabled={!safe || !state.canPreview || !state.snapshot.numeric_material && !state.form?.confirmed} onClick={() => void state.preview()}>{state.snapshot.numeric_material ? '明确为这份原冻结材料新建独立预览' : '明确提交手填材料并冻结数值预览'}</button>
        <p>冻结预览不执行；另行读取完整材料与具体检查后，才可单独批准一次运行。</p>
        {state.snapshot.numeric_check_ids.map(id => <button key={id} disabled={!safe || state.pendingForm} onClick={() => void state.readCheck(id)}>另行读取恢复数值检查 {id}</button>)}
        {state.check && <NumericCheckPanel value={state.check} busy={!safe || state.pendingForm} commandExists={state.commands.some(command => command.kind === 'decision' && command.check_id === state.check!.id && (!command.rejection || !!command.ack))} decide={body => void state.decide(body)} refresh={() => void state.readCheck(state.check!.id)} />}
      </>}
      {state.commands.map(command => <article key={command.command_id}><p>{command.kind === 'preview' ? '数值材料预览' : '独立数值决定'} · {command.ack ? '原数值 ACK 已保存' : command.rejection ? '服务端拒绝，原数值基准保留' : '数值结果未知，原 key 与完整命令保留'}</p>
        <details><summary>核对原数值命令</summary><p>{command.command_id}</p><pre>{JSON.stringify(command.body, null, 2)}</pre>{command.ack && <pre>{JSON.stringify(command.ack, null, 2)}</pre>}</details>
        <button disabled={!safe || state.pendingForm || !!command.ack || !!command.rejection || !state.canReplay(command)} onClick={() => void state.execute(command)}>显式回放原数值命令 {command.command_id}</button>
        {!state.canReplay(command) && <p>原页面、会话或访问代次不能确认；只读保留，不继承原执行权限。</p>}
        {command.kind === 'preview' && command.ack && <button disabled={!safe || state.pendingForm} onClick={() => void state.readCheck(command.ack!.id)}>另行读取原预览对应的当前检查 {command.ack.id}</button>}
      </article>)}
    </>}
    <button disabled={state.busy} onClick={() => void state.permissions()}>重新核对数值权限与本机原记录</button>
    <RestoreNumericControls workspace={workspace} onState={setControlState} />
    <p>运行结果不会更新已有审核；完成后须重新读取恢复稿，另建 Review，并明确作新的数学与来源决定。最新检查和完整账本由发布时再次核验。</p>
  </section>
}
