import { useEffect, useRef } from 'react'
import type { ProviderConfigView } from '../../../../../packages/contracts/generated/api-types'
import type { ProviderPort } from './providerClient'
import { useProviderSecret } from './useProviderSecret'
export function ProviderSecretPanel({ workspace, config, port, changed, onState }: { workspace: string; config: ProviderConfigView | null; port: ProviderPort; changed: () => void; onState: (state: { dirty: boolean; busy: boolean }) => void }) {
  const secret = useProviderSecret(workspace, config, port, changed), callback = useRef(onState); callback.current = onState
  useEffect(() => { callback.current({ dirty: secret.dirty, busy: secret.busy }) }, [secret.dirty, secret.busy])
  return <section aria-label="秘密控制"><h3>秘密控制</h3><p>输入只在当前页面临时保留；不会写入浏览器草稿或恢复存储。刷新后不能恢复原秘密命令。</p>
    <p>新命令使用的已读配置：{secret.basis ? `配置 r${secret.basis.revision} · ${secret.basis.secret_present ? '有秘密引用' : '无秘密引用'}` : '请先保存并读回配置'}。引用存在不表示密钥有效或可调用。</p>
    <label>新秘密<input type="password" value={secret.text} onChange={event => secret.edit(event.target.value)} disabled={!config || secret.busy || !!secret.command} autoComplete="new-password" spellCheck={false} /></label>
    <div className="provider-actions"><button disabled={!config || secret.busy || secret.rejected || secret.command?.kind === 'delete' || !secret.text.trim() && secret.command?.kind !== 'write'} onClick={() => void secret.run('write')}>{secret.command?.kind === 'write' ? '重试原秘密写入命令' : '保存秘密'}</button><button disabled={!config || secret.busy || secret.rejected || secret.command?.kind === 'write'} onClick={() => void secret.run('delete')}>{secret.command?.kind === 'delete' ? '重试原删除引用命令' : '删除秘密引用'}</button>{secret.dirty && <button disabled={secret.busy} onClick={secret.discard}>明确丢弃临时秘密命令</button>}</div>
    {secret.error && <p role="alert">{secret.error}</p>}
    {secret.ack && <p role="status">原秘密命令已确认 · r{secret.ack.revision} · 当时{secret.ack.secret_present ? '有' : '无'}引用。当前状态另行回读。</p>}
    {secret.remote && <p>最近实际读回的配置：r{secret.remote.revision} · {secret.remote.secret_present ? '有秘密引用' : '无秘密引用'}。</p>}
    {secret.rejected && secret.command && <section aria-label="秘密控制版本比较"><h4>比较原基准与当前版本</h4><p>原始基准 r{secret.command.base.revision}；当前{secret.correctionBasis ? `r${secret.correctionBasis.revision}` : '尚未读回'}；本页{secret.command.kind === 'write' ? '仍保留临时输入，内容不回显' : '候选为删除引用'}。</p><button disabled={!secret.correctionBasis || secret.busy} onClick={secret.correct}>采用当前版本，明确更正秘密命令</button></section>}
    <p className="provider-muted">删除使引用不可再调度；不能撤回已发生外发，也不承诺介质级擦除。</p>
  </section>
}
