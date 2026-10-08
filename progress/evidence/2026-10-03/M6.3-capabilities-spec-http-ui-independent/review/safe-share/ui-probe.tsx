import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { CodexCapabilities, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import { request } from '../../api/client'
import { CodexCapabilitiesPanel } from './CodexCapabilitiesPanel'
import type { CodexCapabilityPort } from './codexClient'
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
const workspace = 'workspace_independent_codex'
const session = (): SessionResponse => ({workspace_id:workspace, actor_session_id:'actor_synthetic_independent',role:'author',csrf_token:'synthetic-only',active_independent_attempt_id:null,active_open_book_attempt_id:null})
const available = (): CodexCapabilities => ({available:true,authorized:false,adapter_version:'codex-cli/0.160.0',sandbox_roots:[{id:'workspace_default',label:'隔离 Broker'}],capabilities:{approvals:false,interrupt:false,artifacts:false}})
function deferred<T>() { let resolve!: (value:T)=>void; const promise=new Promise<T>(r=>{resolve=r}); return {promise,resolve} }
const click=()=>fireEvent.click(screen.getByRole('button',{name:'检查 Codex 连接'}))
test.each(['permission','workspace','port','access','unmount'])('late session cannot start a capability read after %s invalidation',async mode=>{
 const pending=deferred<SessionResponse>(),capabilities=vi.fn(async()=>available())
 const p:CodexCapabilityPort={session:vi.fn(()=>pending.promise),capabilities}
 const view=render(<CodexCapabilitiesPanel workspace={workspace} admitted port={p}/>);click()
 await waitFor(()=>expect(p.session).toHaveBeenCalledOnce())
 if(mode==='unmount')view.unmount()
 else if(mode==='access'){
  vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({...session(),role:'learner'}),{status:200})))
  await act(async()=>{await request('POST /api/v1/session/role',{role:'learner'},{'Idempotency-Key':'independent-role'})})
 }else view.rerender(<CodexCapabilitiesPanel workspace={mode==='workspace'?'workspace_other':workspace} admitted={mode!=='permission'} port={mode==='port'?{session:vi.fn(async()=>session()),capabilities:vi.fn(async()=>available())}:p}/>)
 await act(async()=>pending.resolve(session()));expect(capabilities).not.toHaveBeenCalled()
 expect(screen.queryByText('codex-cli/0.160.0')).toBeNull()
})
test('late old port completion cannot erase or replace a newer scoped unavailable observation',async()=>{
 const pending=deferred<CodexCapabilities>(),old:CodexCapabilityPort={session:async()=>session(),capabilities:vi.fn(()=>pending.promise)}
 const fresh:CodexCapabilityPort={session:async()=>session(),capabilities:vi.fn(async()=>({available:false,authorized:false,adapter_version:null,sandbox_roots:[],capabilities:{approvals:false,interrupt:false,artifacts:false}}))}
 const view=render(<CodexCapabilitiesPanel workspace={workspace} admitted port={old}/>);click();await waitFor(()=>expect(old.capabilities).toHaveBeenCalledOnce())
 view.rerender(<CodexCapabilitiesPanel workspace={workspace} admitted port={fresh}/>);click();await screen.findByText('未连接 Codex：未发现可用的本机适配器。')
 await act(async()=>pending.resolve({...available(),authorized:true}));expect(screen.getByText('未连接 Codex：未发现可用的本机适配器。')).toBeTruthy()
 expect(screen.queryByText('此工作区的 Codex 连接与授权状态已确认。')).toBeNull()
})
