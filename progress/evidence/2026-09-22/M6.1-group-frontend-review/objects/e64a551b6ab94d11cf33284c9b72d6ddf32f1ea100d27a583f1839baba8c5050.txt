import { useEffect, useRef, useState } from 'react'
import type { AuthoringPrepareWrite, AuthoringGroupPrepareWrite, ContentRef } from '../../../../../packages/contracts/generated/api-types'
import { checkedAuthoring } from './authoringCommands'
import { AuthoringTargets, type GroupTargets } from './AuthoringTargets'
import { sameRef } from '../reader/target'
export function AuthoringForm({ currentBlock, busy, submit, submitGroup, denied = () => {}, onDirty }: { currentBlock: ContentRef | null; busy: boolean; submit: (body: AuthoringPrepareWrite) => Promise<void>; onDirty: (dirty: boolean) => void; submitGroup?: (body: AuthoringGroupPrepareWrite) => Promise<void>; denied?: (reason: unknown) => void }) {
  const [topic, setTopic] = useState(''), [prerequisites, setPrerequisites] = useState(''), [objectives, setObjectives] = useState(''), [proof, setProof] = useState<'full' | 'declared_dependencies'>('full'), [provider, setProvider] = useState('')
  const [kind, setKind] = useState<'worked_example' | 'lesson' | 'practice_set' | 'assessment'>('worked_example')
  const [targets, setTargets] = useState<GroupTargets>({ concepts: [], lesson: null }), [modes, setModes] = useState<Array<'independent' | 'assisted' | 'open_book'>>([]), [time, setTime] = useState(''), [unlimited, setUnlimited] = useState(false)
  const [refs, setRefs] = useState<ContentRef[]>([]), [id, setId] = useState(''), [revision, setRevision] = useState(''), [hash, setHash] = useState(''), [error, setError] = useState('')
  const callback = useRef(onDirty); callback.current = onDirty
  useEffect(() => { callback.current(!!topic || !!prerequisites || !!objectives || proof !== 'full' || !!provider || !!refs.length || !!id || !!revision || !!hash || kind !== 'worked_example' || targets.concepts.length > 0 || !!targets.lesson || modes.length > 0 || !!time || unlimited) }, [kind, targets, modes, time, unlimited, topic, prerequisites, objectives, proof, provider, refs, id, revision, hash])
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
      const common = { topic, prerequisites: lines(prerequisites), objectives: lines(objectives), proof_policy: proof, output_kind: kind, provider_id: provider, source_refs: refs }
      if (kind === 'worked_example') {
        const body = checkedAuthoring<AuthoringPrepareWrite>('AuthoringPrepareWrite', common)
        setError(''); await submit(body)
      } else {
        if (!submitGroup) throw new Error('组合创作当前不可用。')
        if (kind === 'assessment' && !unlimited && (!/^[1-9][0-9]*$/.test(time) || !Number.isSafeInteger(Number(time)))) throw new Error('请明确选择不限时，或填写正整数秒数。')
        const body = checkedAuthoring<AuthoringGroupPrepareWrite>('AuthoringGroupPrepareWrite', { ...common, target_concept_refs: targets.concepts, ...(kind === 'practice_set' ? { lesson_ref: targets.lesson } : {}), ...(kind === 'assessment' ? { allowed_modes: modes, time_limit_seconds: unlimited ? null : Number(time) } : {}) })
        setError(''); await submitGroup(body)
      }
    } catch (reason) { setError(reason instanceof Error ? reason.message : '准备要求无效，未发送。') }
  }
  return <section aria-label={kind === 'worked_example' ? '准备单个例题候选' : '准备组合草稿'}><h3>{kind === 'worked_example' ? '准备一个例题候选' : '准备组合草稿'}</h3><p>先保存教学要求与准确材料，再另行核对模型调用授权。不会覆盖教材，也不会自动运行数值检查。</p>
    <fieldset disabled={busy}><legend>本次教学要求</legend>
      {submitGroup && <label>创作类型<select value={kind} onChange={event => setKind(event.target.value as typeof kind)}><option value="worked_example">单个例题</option><option value="lesson">教材小节</option><option value="practice_set">习题集</option><option value="assessment">测试题组</option></select></label>}
      <label>{kind === 'worked_example' ? '例题主题' : '创作主题'}<textarea value={topic} onChange={e => setTopic(e.target.value)} /></label>
      <label>已声明先修（每行一条）<textarea value={prerequisites} onChange={e => setPrerequisites(e.target.value)} /></label>
      <label>学习目标（每行一条，至少一条）<textarea value={objectives} onChange={e => setObjectives(e.target.value)} /></label>
      <label>证明策略<select value={proof} onChange={e => setProof(e.target.value as typeof proof)}><option value="full">完整证明</option><option value="declared_dependencies">明确声明所依赖的结论</option></select></label>
      <label>已配置的提供商 ID<input value={provider} onChange={e => setProvider(e.target.value)} /></label><p>请从设置中的实际配置选择 ID。配置存在不代表具备完整输入计量证明或已授权调用。</p>
      {kind !== 'worked_example' && <AuthoringTargets value={targets} change={setTargets} practice={kind === 'practice_set'} busy={busy} denied={denied} />}
      {kind === 'assessment' && <section aria-label="本次测试要求"><h4>本次测试要求</h4>{(['independent', 'assisted', 'open_book'] as const).map(mode => <label key={mode}><input type="checkbox" checked={modes.includes(mode)} onChange={event => setModes(old => event.target.checked ? [...old, mode] : old.filter(value => value !== mode))} />{{ independent: '独立测试', assisted: '辅助测试', open_book: '开卷测试' }[mode]}</label>)}<label><input type="checkbox" checked={unlimited} onChange={event => setUnlimited(event.target.checked)} />明确不限时</label><label>测试时限（秒）<input disabled={unlimited} inputMode="numeric" value={time} onChange={event => setTime(event.target.value)} /></label></section>}
      <h4>本次材料范围</h4>{!refs.length && <p>无已选教材来源。不会自动加入当前教材或父级内容。</p>}
      {currentBlock?.entity === 'block' && <button disabled={refs.some(v => sameRef(v, currentBlock)) || refs.length >= 8} onClick={() => add(currentBlock)}>明确加入当前准确内容块</button>}
      {refs.map((ref, i) => <p key={`${ref.id}:${ref.revision}`}>{ref.id} · r{ref.revision} · <code>{ref.sha256}</code> <button onClick={() => setRefs(old => old.filter((_, index) => index !== i))}>移除材料 {i + 1}</button></p>)}
      <details><summary>明确加入其他准确内容块</summary><label>内容块 ID<input value={id} onChange={e => setId(e.target.value)} /></label><label>内容修订<input inputMode="numeric" value={revision} onChange={e => setRevision(e.target.value)} /></label><label>内容 SHA256<input value={hash} onChange={e => setHash(e.target.value)} /></label><button onClick={() => add({ entity: 'block', id, revision: /^[1-9][0-9]*$/.test(revision) ? Number(revision) : 0, sha256: hash })}>加入这份准确引用</button></details>
      <button onClick={() => void prepare()}>{kind === 'worked_example' ? '明确准备本次例题任务' : '明确准备本次组合创作任务'}</button>
    </fieldset>{error && <p role="alert">{error}</p>}
  </section>
}
