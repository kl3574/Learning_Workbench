import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { ProviderConfigView, ProviderSecretAck, ProviderSecretWrite } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import type { ProviderPort } from './providerClient'
import { checkedProvider } from './providerSchema'

type SecretCommand = { kind: 'write'; key: string; base: ProviderConfigView; body: ProviderSecretWrite } | { kind: 'delete'; key: string; base: ProviderConfigView }
/** Deliberately no DraftStore, browser storage, channel broadcast or body logging. */
export function useProviderSecret(workspace: string, base: ProviderConfigView | null, port: ProviderPort, changed: () => void) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  const owner = JSON.stringify([workspace, access, base?.id ?? null]), current = useRef(owner); current.current = owner
  const currentPort = useRef(port); currentPort.current = port
  const [statePort, setStatePort] = useState(port)
  const [stateOwner, setStateOwner] = useState(owner), [text, setText] = useState(''), [command, setCommand] = useState<SecretCommand | null>(null)
  const [ack, setAck] = useState<ProviderSecretAck | null>(null), [remote, setRemote] = useState<ProviderConfigView | null>(null)
  const [busy, setBusy] = useState(false), [rejected, setRejected] = useState(false), [error, setError] = useState('')
  const operation = useRef(0), active = stateOwner === owner && statePort === port, callback = useRef(changed); callback.current = changed
  const owns = (captured: string, sequence: number) => captured === current.current && port === currentPort.current && access === getSessionGeneration() && sequence === operation.current
  useEffect(() => { operation.current++; setStateOwner(owner); setStatePort(port); setText(''); setCommand(null); setAck(null); setRemote(null); setBusy(false); setRejected(false); setError(''); return () => { operation.current++ } }, [owner, port])
  // A local ACK is historical. Only an actual config read can advance a new
  // command's basis before the parent's independent refresh has arrived.
  const basis = active && base && remote?.id === base.id && remote.revision > base.revision ? remote : base
  const dirty = active && (!!text || !!command)
  useEffect(() => {
    const guard = (event: BeforeUnloadEvent) => { if (dirty || busy) { event.preventDefault(); event.returnValue = '' } }
    addEventListener('beforeunload', guard); return () => removeEventListener('beforeunload', guard)
  }, [dirty, busy])
  const run = async (kind: 'write' | 'delete') => {
    if (!active || !basis || busy || rejected || access !== getSessionGeneration()) return
    let original = command
    if (!original) {
      if (kind === 'write' && !text.trim()) { setError('秘密不能为空或全为空白，原引用未更改。'); return }
      original = kind === 'write' ? { kind, base: structuredClone(basis), key: `secret_${crypto.randomUUID()}`, body: { expected_revision: basis.revision, secret: text } } : { kind, base: structuredClone(basis), key: `secret_${crypto.randomUUID()}` }
      setCommand(original)
    }
    if (original.kind !== kind) return
    const sequence = ++operation.current, captured = owner
    setBusy(true); setError('')
    const readCurrent = async () => {
      const latest = checkedProvider<ProviderConfigView>('ProviderConfigView', await port.config(original.base.id))
      if (latest.id !== original.base.id) throw new Error('unexpected config identity')
      if (owns(captured, sequence)) setRemote(latest)
    }
    try {
      const value = checkedProvider<ProviderSecretAck>('ProviderSecretAck', original.kind === 'write' ? await port.saveSecret(original.base.id, original.body, original.key) : await port.deleteSecret(original.base.id, original.base.config_sha256, original.key))
      const expected = original.base.revision + (original.kind === 'write' || original.base.secret_present ? 1 : 0)
      if (value.id !== original.base.id || value.revision !== expected || value.secret_present !== (original.kind === 'write')) throw new Error('unexpected receipt')
      if (!owns(captured, sequence)) return
      setAck(value); setText(''); setCommand(null); setRejected(false)
      try { await readCurrent() }
      catch { if (owns(captured, sequence)) setError('原秘密控制命令已确认；当前配置尚未读回。') }
      if (owns(captured, sequence)) callback.current()
    } catch (reason) {
      if (!owns(captured, sequence)) return
      if (reason instanceof ApiError && reason.status === 412) {
        setRejected(true); setRemote(null)
        try { await readCurrent() } catch { /* Never fabricate a correction basis. */ }
      }
      if (owns(captured, sequence)) setError(reason instanceof ApiError && reason.status === 412 ? '秘密控制版本冲突。临时输入与原基准仍保留，比较后再更正。' : '原秘密控制命令尚未确认。只可用本页仍保留的原 key 和原字节重试；当前 secret_present 不能确认刚输入的秘密。')
    } finally { if (owns(captured, sequence)) setBusy(false) }
  }
  const correct = () => {
    if (!active || !command || !remote || !rejected || busy || access !== getSessionGeneration() || command.base.id !== remote.id) return
    setCommand(command.kind === 'write' ? { ...command, key: `secret_${crypto.randomUUID()}`, base: remote, body: { ...command.body, expected_revision: remote.revision } } : { ...command, key: `secret_${crypto.randomUUID()}`, base: remote })
    setRejected(false); setError('已明确采用当前配置版本，新的秘密控制命令尚未发送。')
  }
  const discard = () => { if (!busy) { setText(''); setCommand(null); setRejected(false); setError('临时秘密输入已从本页状态丢弃；未执行新的控制命令。') } }
  return { basis: active ? basis : null, text: active ? text : '', command: active ? command : null, ack: active ? ack : null, remote: active ? remote : null, busy: active && busy, dirty, rejected: active && rejected, error: active ? error : '', edit: (value: string) => { if (active && !busy && !command) { setText(value); setAck(null) } }, run, correct, discard }
}
