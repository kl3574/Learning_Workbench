import { useEffect, useRef } from 'react'
import { ProfileFields, ProfileComparison, selfLabels, type ConceptChoice } from './ProfileFields'
import { useProfile, type ProfilePort } from './useProfile'
import './learning.css'
export function ProfilePanel({ workspace, paused, port, concepts, conceptsError, onState, saved }: { workspace: string; paused: boolean; port: ProfilePort; concepts: ConceptChoice[]; conceptsError: string; onState: (state: { dirty: boolean; safe: boolean }) => void; saved: () => void }) {
  const profile = useProfile(workspace, paused, port), fields = profile.fields
  const callback = useRef(onState); callback.current = onState
  const notified = useRef<number | null>(null)
  useEffect(() => { callback.current({ dirty: profile.dirty, safe: profile.safe }) }, [profile.dirty, profile.safe])
  useEffect(() => { const revision = profile.editor?.acknowledged?.revision; if (revision && notified.current !== revision) { notified.current = revision; saved() } }, [profile.editor?.acknowledged?.revision, saved])
  if (paused) return <div className="learning-panel"><p>正在核验或受到当前测试策略限制。画像内容暂不显示；本机候选仍保留。</p></div>
  const blocked = profile.busy || !profile.journal.ready || profile.journal.saving || !profile.safe || !!profile.conflicts.length || !!profile.decodeError
  return <section className="learning-panel" aria-label="学习目标与基础"><p>记录你想学什么、可投入的时间和自报基础。自报不会增加独立证据，也不会改动历史成绩。</p><p role="status">{profile.busy ? '正在读写服务端画像…' : profile.dirty ? '画像更改尚未同步' : profile.saved ? '画像已保存到服务端' : '画像尚待读回'} · {profile.journal.saving ? '本机画像草稿保存中…' : profile.safe ? '本机画像草稿存储可用' : '本机画像草稿尚未安全保存'}</p>
    {[profile.error, profile.journal.error, profile.decodeError, conceptsError].filter(Boolean).map((message, index) => <p className="learning-error" role="alert" key={index}>{message}</p>)}<div className="learning-actions"><button disabled={profile.busy} onClick={() => void profile.refresh()}>重新读取画像</button>{profile.journal.error && <button onClick={profile.retryLocal}>重试本机画像保存</button>}</div>
    {(profile.needsRecovery || !!profile.conflicts.length) && <section aria-label="本机画像候选"><h3>发现本机画像候选</h3><p>每份候选保留自己的原始基准。恢复不会自动提交；其他正在编辑的页面仍可保留自己的分支。</p>{profile.candidates.map((candidate, index) => <details className="learning-candidate" open key={candidate.text}><summary>画像候选 {index + 1} · 基准修订 {candidate.value.base.revision}</summary><p>{candidate.value.fields.goals.join('；') || '尚未填写目标'}</p><p>每周 {candidate.value.fields.weekly_minutes || '尚未填写'} 分钟 · {candidate.value.fields.language}</p><button disabled={profile.busy || profile.journal.saving || !profile.safe} onClick={() => void profile.restore(candidate)}>恢复画像候选 {index + 1}</button></details>)}</section>}
    {fields && <>{!profile.claimed && !profile.needsRecovery && <button disabled={blocked || !profile.remote} onClick={profile.begin}>编辑学习目标与基础</button>}<ProfileFields value={fields} concepts={concepts} disabled={!profile.claimed || profile.busy || !profile.journal.ready || !!profile.conflicts.length || profile.needsRecovery} change={profile.edit} />{profile.editor?.base && <p className="learning-muted">编辑基准：画像修订 {profile.editor.base.revision}。概念自报与课程阅读、练习参与、测试证据分别保存。</p>}
      {profile.editor && profile.conflict && <><ProfileComparison base={profile.editor.base} local={fields} remote={profile.remote} /><div className="learning-actions"><button disabled={blocked || !profile.remote} onClick={() => profile.rebase(true)}>保留本页画像并采用服务端基准</button><button disabled={blocked || !profile.remote} onClick={() => profile.rebase(false)}>采用服务端画像</button></div></>}
      {profile.claimed && <div className="learning-actions"><button className="primary-button" disabled={blocked || profile.conflict || !profile.changed || profile.needsRecovery} onClick={() => void profile.save()}>保存学习目标与基础</button>{profile.error && <button disabled={blocked || !profile.changed || profile.needsRecovery} onClick={() => void profile.save()}>重试原画像保存命令</button>}</div>}
    </>}
    {profile.remote && (profile.remote.self_assessments?.length ?? 0) > 0 && <details><summary>核对服务端自报来源与时间</summary>{profile.remote.self_assessments?.map(item => <p key={item.concept_id}>{concepts.find(concept => concept.id === item.concept_id)?.title ?? item.concept_id}：{selfLabels[item.level]} · 用户自报 · <time dateTime={item.updated_at}>{item.updated_at}</time></p>)}</details>}
  </section>
}
