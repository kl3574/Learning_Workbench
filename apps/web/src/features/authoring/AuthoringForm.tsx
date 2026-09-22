import { useEffect, useRef, useState } from 'react'
import type { AuthoringPrepareWrite, ContentRef } from '../../../../../packages/contracts/generated/api-types'
import { checkedAuthoring } from './authoringCommands'
import { sameRef } from '../reader/target'
export function AuthoringForm({ currentBlock, busy, submit, onDirty }: { currentBlock: ContentRef | null; busy: boolean; submit: (body: AuthoringPrepareWrite) => Promise<void>; onDirty: (dirty: boolean) => void }) {
  const [topic, setTopic] = useState(''), [prerequisites, setPrerequisites] = useState(''), [objectives, setObjectives] = useState(''), [proof, setProof] = useState<'full' | 'declared_dependencies'>('full'), [provider, setProvider] = useState('')
  const [refs, setRefs] = useState<ContentRef[]>([]), [id, setId] = useState(''), [revision, setRevision] = useState(''), [hash, setHash] = useState(''), [error, setError] = useState('')
  const callback = useRef(onDirty); callback.current = onDirty
  useEffect(() => { callback.current(!!topic || !!prerequisites || !!objectives || proof !== 'full' || !!provider || !!refs.length || !!id || !!revision || !!hash) }, [topic, prerequisites, objectives, proof, provider, refs, id, revision, hash])
  const add = (ref: ContentRef) => {
    try {
      checkedAuthoring('ContentRef', ref)
      if (ref.entity !== 'block' || refs.length >= 8 || refs.some(v => v.id === ref.id && v.revision === ref.revision)) throw new Error('最多选择八个准确内容块；不能重复或替换同一修订的哈希。')
      setRefs(old => [...old, ref]); setError(''); setId(''); setRevision(''); setHash('')
    } catch (reason) { setError(reason instanceof Error ? reason.message : '准确引用无效。') }
  }
  const prepare = async () => {
    try {
      const lines = (value: string) => value.split('\n').map(v => v.trim()).filter(Boolean)
      const body = checkedAuthoring<AuthoringPrepareWrite>('AuthoringPrepareWrite', { topic, prerequisites: lines(prerequisites), objectives: lines(objectives), proof_policy: proof, output_kind: 'worked_example', provider_id: provider, source_refs: refs })
      setError(''); await submit(body)
    } catch (reason) { setError(reason instanceof Error ? reason.message : '准备要求无效，未发送。') }
  }
  return <section aria-label="准备单个例题候选"><h3>准备一个例题候选</h3><p>先保存教学要求与准确材料，再另行核对模型调用授权。不会覆盖教材，也不会自动运行数值检查。</p>
    <fieldset disabled={busy}><legend>本次教学要求</legend>
      <label>例题主题<textarea value={topic} onChange={e => setTopic(e.target.value)} /></label>
      <label>已声明先修（每行一条）<textarea value={prerequisites} onChange={e => setPrerequisites(e.target.value)} /></label>
      <label>学习目标（每行一条，至少一条）<textarea value={objectives} onChange={e => setObjectives(e.target.value)} /></label>
      <label>证明策略<select value={proof} onChange={e => setProof(e.target.value as typeof proof)}><option value="full">完整证明</option><option value="declared_dependencies">明确声明所依赖的结论</option></select></label>
      <label>已配置的提供商 ID<input value={provider} onChange={e => setProvider(e.target.value)} /></label><p>请从设置中的实际配置选择 ID。配置存在不代表具备完整输入计量证明或已授权调用。</p>
      <h4>本次材料范围</h4>{!refs.length && <p>无已选教材来源。不会自动加入当前教材或父级内容。</p>}
      {currentBlock?.entity === 'block' && <button disabled={refs.some(v => sameRef(v, currentBlock)) || refs.length >= 8} onClick={() => add(currentBlock)}>明确加入当前准确内容块</button>}
      {refs.map((ref, i) => <p key={`${ref.id}:${ref.revision}`}>{ref.id} · r{ref.revision} · <code>{ref.sha256}</code> <button onClick={() => setRefs(old => old.filter((_, index) => index !== i))}>移除材料 {i + 1}</button></p>)}
      <details><summary>明确加入其他准确内容块</summary><label>内容块 ID<input value={id} onChange={e => setId(e.target.value)} /></label><label>内容修订<input inputMode="numeric" value={revision} onChange={e => setRevision(e.target.value)} /></label><label>内容 SHA256<input value={hash} onChange={e => setHash(e.target.value)} /></label><button onClick={() => add({ entity: 'block', id, revision: /^[1-9][0-9]*$/.test(revision) ? Number(revision) : 0, sha256: hash })}>加入这份准确引用</button></details>
      <button onClick={() => void prepare()}>明确准备本次例题任务</button>
    </fieldset>{error && <p role="alert">{error}</p>}
  </section>
}
