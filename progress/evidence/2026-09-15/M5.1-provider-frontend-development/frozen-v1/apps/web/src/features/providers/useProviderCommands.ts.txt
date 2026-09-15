import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { ConsentProposalView, ConsentView, ProviderConfigView } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import type { ProviderPort } from './providerClient'
import { commandDirty, commandKey, commandSubject, decodeCommand, newCommand, providerCommandStore, useProviderJournal, type CommandInput, type ProviderCommand } from './providerDrafts'

export type CommandRemote = { kind: 'config'; value: ProviderConfigView } | { kind: 'proposal'; value: ConsentProposalView } | { kind: 'consent'; value: ConsentView }
export function useProviderCommands(workspace: string, paused: boolean, port: ProviderPort) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  const owner = JSON.stringify([workspace, access]), scope = useRef({ owner, paused }); scope.current = { owner, paused }
  const journal = useProviderJournal(workspace), operation = useRef(0)
  const [held, setHeld] = useState<{ owner: string; value: ProviderCommand } | null>(null), live = useRef(held); live.current = held
  const [remoteState, setRemote] = useState<{ owner: string; value: CommandRemote } | null>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [rejected, setRejected] = useState(false)
  const [sealed, setSealed] = useState(false)
  const owns = (captured: string, command: ProviderCommand) => scope.current.owner === captured && getSessionGeneration() === access && !(scope.current.paused && commandSubject(command))
  const persist = (command: ProviderCommand) => { live.current = { owner, value: command }; setHeld(live.current); journal.save(command) }
  const allCandidates: { value: ProviderCommand; text: string }[] = []
  let decodeError = ''
  for (const record of Object.values(journal.records)) for (const raw of new Set([record.text, ...record.conflicts.map(item => item.text)])) {
    try { const value = decodeCommand(raw, workspace); if (commandDirty(value)) allCandidates.push({ value, text: raw }) }
    catch { decodeError = '本机配置或授权记录无法按契约读取；原记录保留。' }
  }
  const editor = held?.owner === owner && !(paused && commandSubject(held.value)) ? held.value : null
  const remote = remoteState?.owner === owner && !(paused && remoteState.value.kind !== 'config') ? remoteState.value : null
  const safe = journal.ready && !journal.workspaceUnsafe && !journal.error && !decodeError
  const closeSafe = safe && !journal.unsafe && !busy
  const competing = editor ? allCandidates.filter(item => commandKey(item.value) === commandKey(editor) && item.text !== JSON.stringify(editor)) : []
  const candidates = allCandidates.filter(item => !paused || !commandSubject(item.value))
  useEffect(() => { operation.current++; live.current = null; setHeld(null); setRemote(null); setBusy(false); setError(''); setRejected(false); setSealed(false); return () => { operation.current++ } }, [owner, port])
  useEffect(() => { operation.current++; setRemote(null); setBusy(false); setError('') }, [paused])
  const readRemote = async (command: ProviderCommand): Promise<CommandRemote | null> => {
    if (command.kind === 'config') return { kind: 'config', value: await port.config(command.provider_id) }
    if (command.kind === 'preview') return command.ack ? { kind: 'proposal', value: await port.proposal(command.ack.id) } : null
    if (command.kind === 'grant') return { kind: 'proposal', value: await port.proposal(command.body.proposal_id) }
    if (scope.current.paused) return null
    const page = await port.consents({ consent_id: command.consent_id })
    if (page.items.length !== 1 || page.items[0].id !== command.consent_id) throw new Error('没有读回原授权身份，未猜测当前版本。')
    return { kind: 'consent', value: page.items[0] }
  }
  const refresh = async () => {
    const command = live.current?.owner === owner ? live.current.value : null
    if (!command || !owns(owner, command) || busy) return
    const sequence = ++operation.current
    setBusy(true); setRemote(null)
    try { const value = await readRemote(command); if (owns(owner, command) && sequence === operation.current) { setRemote(value ? { owner, value } : null); setError('') } }
    catch { if (owns(owner, command) && sequence === operation.current) setError('当前服务端状态尚未读回；原候选和原回执保留。') }
    finally { if (owns(owner, command) && sequence === operation.current) setBusy(false) }
  }
  const begin = (input: CommandInput) => {
    if (!safe || busy || editor && commandDirty(editor)) return false
    try {
      const command = newCommand(workspace, input)
      if (!owns(owner, command)) return false
      if (allCandidates.some(item => commandKey(item.value) === commandKey(command))) throw new Error('此对象已有未确认命令，请先恢复原候选。')
      persist(command); setRemote(null); setRejected(false); setSealed(false); setError('原命令已准备；本机保存完成后可明确发送。'); return true
    } catch (reason) { setError(reason instanceof Error ? reason.message : '候选无效，未发送。'); return false }
  }
  const restore = async (candidate: { value: ProviderCommand; text: string }) => {
    if (!safe || busy || !owns(owner, candidate.value) || editor && commandDirty(editor) && commandKey(editor) !== commandKey(candidate.value)) return
    const sequence = ++operation.current; setBusy(true); setRemote(null)
    try {
      const key = commandKey(candidate.value), stored = (await providerCommandStore.load(workspace))[key]
      if (!stored || ![stored.text, ...stored.conflicts.map(item => item.text)].includes(candidate.text)) throw new Error('原候选尚未从本机存储核对。')
      if (!owns(owner, candidate.value) || sequence !== operation.current) return
      const value = stored.conflicts.length ? await journal.resolve(key, candidate.text) : decodeCommand(candidate.text, workspace)
      if (!owns(owner, value) || sequence !== operation.current) return
      live.current = { owner, value }; setHeld(live.current); setSealed(true); setRejected(false)
      setError('已恢复原命令，尚未重发。先回放原 key 核对回执，再考虑新的更正。')
      try { const current = await readRemote(value); if (owns(owner, value) && sequence === operation.current) setRemote(current ? { owner, value: current } : null) } catch { /* Replay does not depend on a fresh provider/source read. */ }
    } catch (reason) { if (owns(owner, candidate.value) && sequence === operation.current) setError(reason instanceof Error ? reason.message : '恢复失败，候选保留。') }
    finally { if (owns(owner, candidate.value) && sequence === operation.current) setBusy(false) }
  }
  const send = async () => {
    const command = live.current?.owner === owner ? live.current.value : null
    if (!command || !commandDirty(command) || !owns(owner, command) || busy || !safe || competing.length || rejected) return
    const sequence = ++operation.current; setBusy(true); setSealed(true); setError('')
    try {
      const record = (await providerCommandStore.load(workspace))[commandKey(command)]
      if (!record || ![record.text, ...record.conflicts.map(item => item.text)].includes(JSON.stringify(command))) throw new Error('原命令尚未持久化，不发送。')
      if (!owns(owner, command) || sequence !== operation.current) return
      const ack = command.kind === 'config' ? await port.saveConfig(command.provider_id, command.body, command.command_id)
        : command.kind === 'preview' ? await port.preview(command.body, command.command_id)
          : command.kind === 'grant' ? await port.grant(command.body, command.command_id)
            : await port.revoke(command.consent_id, command.body, command.command_id)
      const acknowledged = decodeCommand(JSON.stringify({ ...command, ack }), workspace)
      if (!owns(owner, command) || sequence !== operation.current) return
      persist(acknowledged); setRejected(false)
      try { const current = await readRemote(acknowledged); if (owns(owner, command) && sequence === operation.current) setRemote(current ? { owner, value: current } : null) }
      catch { if (owns(owner, command) && sequence === operation.current) { setRemote(null); setError('原命令已确认；当前状态尚未读回，不能以原回执代替当前状态。') } }
    } catch (reason) {
      if (!owns(owner, command) || sequence !== operation.current) return
      if (reason instanceof ApiError && reason.status === 412) {
        setRejected(true); setRemote(null)
        try { const current = await readRemote(command); if (owns(owner, command) && sequence === operation.current) setRemote(current ? { owner, value: current } : null) } catch { /* No fabricated current basis. */ }
      }
      if (owns(owner, command) && sequence === operation.current) setError(reason instanceof ApiError && reason.status === 412 ? '版本冲突：原基准、本页候选与当前状态分别保留；比较后才能创建更正命令。' : '命令尚未确认。原 key、字段与版本条件保留，可重试原命令；不会自动重发。')
    } finally { if (owns(owner, command) && sequence === operation.current) setBusy(false) }
  }
  const correct = () => {
    if (!editor || !remote || busy || !safe || competing.length || !rejected && !editor.ack || !owns(owner, editor)) return
    if (editor.kind === 'config' && remote.kind === 'config' && editor.provider_id === remote.value.id) {
      persist(newCommand(workspace, { kind: 'config', provider_id: editor.provider_id, base: remote.value, body: { ...editor.body, expected_revision: remote.value.revision } }))
    } else if (editor.kind === 'revoke' && remote.kind === 'consent' && editor.consent_id === remote.value.id) {
      persist(newCommand(workspace, { kind: 'revoke', consent_id: editor.consent_id, body: { expected_revision: remote.value.revision } }))
    } else { setError('授权输入不能自动换成新版本；请由任务重新准备预览并明确批准。'); return }
    setRejected(false); setSealed(false); setError('已明确采用当前版本，生成新的更正候选；尚未发送。')
  }
  const retain = () => { if (!closeSafe) return; operation.current++; live.current = null; setHeld(null); setRemote(null); setRejected(false); setSealed(false); setError('未确认原命令已保留在本机，可从候选列表恢复。') }
  return { editor, remote, candidates, competing, busy, error, rejected, sealed, safe, closeSafe, dirty: allCandidates.length > 0, journal, decodeError, begin, restore, send, correct, retain, refresh, retryLocal: () => { if (editor) journal.save(editor) } }
}
