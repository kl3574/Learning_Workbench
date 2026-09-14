import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterAll, afterEach, beforeAll, beforeEach, expect, test, vi } from 'vitest'
import { IDBFactory } from 'fake-indexeddb'
import fixture from './fixture.json'
const transport = vi.hoisted(() => ({ call: vi.fn() }))
vi.mock('<WORKTREE>/apps/web/src/api/client.ts', () => ({ request: (...args: unknown[]) => transport.call(...args) }))
let hooks: typeof import('<WORKTREE>/apps/web/src/features/practice/usePracticeSession')
let drafts: typeof import('<WORKTREE>/apps/web/src/features/practice/practiceDrafts')
let remotes: Record<string, any>, puts: {id: string; body: any}[], gets: string[]
let customPut: ((id: string, body: any) => Promise<any>) | null
let customMutation: ((route: string, id: string, body: any) => Promise<any>) | null
let workspace: string
beforeAll(async () => {
 vi.stubGlobal('indexedDB',new IDBFactory())
 hooks=await import('<WORKTREE>/apps/web/src/features/practice/usePracticeSession')
 drafts=await import('<WORKTREE>/apps/web/src/features/practice/practiceDrafts')
})
beforeEach(() => {
 remotes=structuredClone(fixture.sessions);puts=[];gets=[];customPut=null;customMutation=null
 workspace='workspace_'+crypto.randomUUID().replaceAll('-','')
 transport.call.mockImplementation(async (route: string, body: any, _headers: unknown, options: any) => {
  const id=options?.path?.id
  if(route.startsWith('GET ')) {gets.push(id);return structuredClone(remotes[id])}
  if(route.startsWith('PUT ')) {
   puts.push({id,body:structuredClone(body)})
   if(customPut)return customPut(id,body)
   const current=remotes[id]
   if(current.revision!==body.expected_revision)throw Object.assign(new Error('真实CAS形状的合成412'),{status:412})
   remotes[id]={...current,revision:current.revision+1,responses:structuredClone(body.responses)}
   return {id,revision:remotes[id].revision,saved_at:'2026-09-14T00:00:00Z'}
  }
  if(customMutation)return customMutation(route,id,body)
  throw new Error('Unexpected transport route')
 })
})
afterEach(async () => {cleanup();await new Promise(resolve=>setTimeout(resolve,30))})
afterAll(async () => {await drafts.practiceDraftStore.close();vi.unstubAllGlobals()})
const target=(id:string)=>({...fixture.target,session_id:id})
const answer=(value:string)=>({question_id:fixture.sessions.practice_session_A.questions[0].id,answer:value,steps_markdown:''})
async function mount(id = 'practice_session_A') {
 const hook=renderHook(({id})=>hooks.usePracticeSession(workspace,target(id)),{initialProps:{id}})
 await waitFor(()=>expect(hook.result.current.state).toBe('saved'))
 await waitFor(()=>expect(hook.result.current.commandReady).toBe(true))
 return hook
}
async function edit(hook: Awaited<ReturnType<typeof mount>>,text: string) {
 act(()=>hook.result.current.update(answer(text)))
 await waitFor(()=>expect(hook.result.current.localSaving).toBe(false))
}
function deferred<T>() {let resolve!:(value:T)=>void;const promise=new Promise<T>(yes=>{resolve=yes});return {promise,resolve}}
test('unsent responses from session A must not be rebound or automatically written to session B',async()=>{
 const hook=await mount()
 await edit(hook,'A_ONLY_UNSENT')
 hook.rerender({id:'practice_session_B'})
 await waitFor(()=>expect(hook.result.current.snapshot?.id).toBe('practice_session_B'))
 await act(async()=>{await new Promise(resolve=>setTimeout(resolve,650))})
 const local=await drafts.practiceDraftStore.load(workspace)
 console.log('CROSS_SESSION_OBSERVED',JSON.stringify({target:hook.result.current.snapshot?.id,put_ids:puts.map(item=>item.id),remoteB:remotes.practice_session_B.responses,localB:local['practice:practice_session_B']?.text}))
 expect(remotes.practice_session_B.responses).toEqual([])
 expect(puts.filter(item=>item.id==='practice_session_B')).toHaveLength(0)
})
test('switching while a response PUT is pending must eventually read the new session',async()=>{
 const hook=await mount();await edit(hook,'A_PENDING')
 const gate=deferred<any>()
 customPut=()=>gate.promise
 let completion:Promise<void>|undefined
 act(()=>{completion=hook.result.current.save()})
 await waitFor(()=>expect(puts).toHaveLength(1))
 hook.rerender({id:'practice_session_B'})
 await act(async()=>{gate.resolve({id:'practice_session_A',revision:2,saved_at:'2026-09-14T00:00:00Z'});await completion})
 await act(async()=>{await new Promise(resolve=>setTimeout(resolve,150))})
 console.log('PENDING_SWITCH_OBSERVED',JSON.stringify({gets,snapshot:hook.result.current.snapshot?.id,state:hook.result.current.state}))
 expect(gets).toContain('practice_session_B')
 expect(hook.result.current.snapshot?.id).toBe('practice_session_B')
})
test('412 preserves the visible and durable local candidate for explicit comparison',async()=>{
 const hook=await mount();await edit(hook,'MY_LOCAL')
 remotes.practice_session_A={...remotes.practice_session_A,revision:2,responses:[answer('OTHER_PAGE')]}
 await act(async()=>{await hook.result.current.save()})
 expect(hook.result.current.state).toBe('conflict')
 expect(hook.result.current.conflict?.local[0].answer).toBe('MY_LOCAL')
 expect(hook.result.current.conflict?.remote.responses[0].answer).toBe('OTHER_PAGE')
 const local=await drafts.practiceDraftStore.load(workspace)
 expect(drafts.decodePracticeEnvelope(local['practice:practice_session_A'].text,workspace).candidate_responses[0].answer).toBe('MY_LOCAL')
})
test('restoring an unsent candidate after another page submitted preserves it locally without PUT',async()=>{
 const hook=await mount();await edit(hook,'LOCAL_AFTER_SUBMITTED')
 remotes.practice_session_A=structuredClone(fixture.submitted_session_A)
 await act(async()=>{await hook.result.current.retry()})
 expect(hook.result.current.conflict).not.toBeNull()
 act(()=>hook.result.current.resolveServer(true))
 expect(hook.result.current.responses[0].answer).toBe('LOCAL_AFTER_SUBMITTED')
 expect(hook.result.current.state).toBe('offline')
 await waitFor(()=>expect(hook.result.current.localSaving).toBe(false))
 await act(async()=>{await new Promise(resolve=>setTimeout(resolve,500))})
 expect(puts).toHaveLength(0)
 const local=await drafts.practiceDraftStore.load(workspace)
 expect(drafts.decodePracticeEnvelope(local['practice:practice_session_A'].text,workspace).candidate_responses[0].answer).toBe('LOCAL_AFTER_SUBMITTED')
})
test('production-like keyed unmount with PUT in flight keeps A and B separate and recovers A on return',async()=>{
 const a=await mount();await edit(a,'A_DURABLE_BEFORE_LEAVING')
 const gate=deferred<void>()
 customPut=async(id,body)=>{
  if(id==='practice_session_A')await gate.promise
  remotes[id]={...remotes[id],revision:remotes[id].revision+1,responses:structuredClone(body.responses)}
  return {id,revision:remotes[id].revision,saved_at:'2026-09-14T00:00:00Z'}
 }
 let completion:Promise<void>|undefined
 act(()=>{completion=a.result.current.save()})
 await waitFor(()=>expect(puts).toHaveLength(1));a.unmount()
 const b=await mount('practice_session_B');await edit(b,'B_OWN_DURABLE')
 await act(async()=>{await b.result.current.save()})
 await act(async()=>{gate.resolve();await completion})
 expect(b.result.current.responses[0].answer).toBe('B_OWN_DURABLE')
 expect(remotes.practice_session_A.responses[0].answer).toBe('A_DURABLE_BEFORE_LEAVING')
 expect(remotes.practice_session_B.responses[0].answer).toBe('B_OWN_DURABLE')
 b.unmount()
 const restored=renderHook(()=>hooks.usePracticeSession(workspace,target('practice_session_A')))
 await waitFor(()=>expect(restored.result.current.snapshot?.id).toBe('practice_session_A'))
 await waitFor(()=>expect(restored.result.current.needsRecovery).toBe(true))
 expect(restored.result.current.storedEnvelope?.candidate_responses[0].answer).toBe('A_DURABLE_BEFORE_LEAVING')
 await act(async()=>{await restored.result.current.restore(restored.result.current.storedEnvelope!)})
 if(restored.result.current.conflict)act(()=>restored.result.current.resolveServer(false))
 expect(restored.result.current.responses[0].answer).toBe('A_DURABLE_BEFORE_LEAVING')
 expect(puts.map(item=>[item.id,item.body.responses[0].answer])).toEqual([['practice_session_A','A_DURABLE_BEFORE_LEAVING'],['practice_session_B','B_OWN_DURABLE']])
})
test('production-like unmount during reveal cannot display a late A solution in B or preload it on return',async()=>{
 const a=await mount();const gate=deferred<void>()
 customMutation=async(route,id)=>{
  expect(route).toBe('POST /api/v1/practice/sessions/{id}/solutions')
  await gate.promise
  const current=remotes[id]
  remotes[id]={...current,revision:2,assisted:true,exposure_event_ids:['event_synthetic_reveal'],assistance:current.assistance.map((item:any,index:number)=>index===0?{...item,solution_revealed:true}:item)}
  return {solution_markdown:'PRIVATE_A_REVEAL_ONLY',exposure_event_id:'event_synthetic_reveal',revision:2,review_status:'needs_review'}
 }
 let completion:Promise<void>|undefined
 act(()=>{completion=a.result.current.reveal(fixture.sessions.practice_session_A.questions[0].id)})
 await waitFor(()=>expect(a.result.current.busy).toBe(true));a.unmount()
 const b=await mount('practice_session_B')
 await act(async()=>{gate.resolve();await completion})
 expect(b.result.current.solutions).toEqual({});expect(b.result.current.snapshot?.id).toBe('practice_session_B')
 b.unmount()
 const restored=await mount()
 expect(restored.result.current.snapshot?.assistance[0].solution_revealed).toBe(true)
 expect(restored.result.current.solutions).toEqual({})
})
