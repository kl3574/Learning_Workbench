// Real React/React Query and localStorage with controlled delayed HTTP.
// Regression: a prior recovery choice never authorizes discarding later edits.
import type { ReactNode } from 'react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { emptySession } from './model'
const calls = vi.hoisted(() => ({read:vi.fn(),save:vi.fn(),connect:vi.fn()}))
vi.mock('../api/client', () => ({ApiError:class extends Error {status:number;constructor(status:number,message:string){super(message);this.status=status}}, connectSession:calls.connect,readSessionWithMetadata:calls.read,saveSessionWithMetadata:calls.save}))
vi.mock('./useObjectDrafts', () => ({useObjectDrafts:()=>({})}))
import { useWorkbench } from './useWorkbench'
import { pendingKey, readLocal } from './uiCache'
afterEach(cleanup)
beforeEach(()=>{localStorage.clear();vi.clearAllMocks()})
test('a pending restore response must not erase a layout edit made after restore was clicked',async()=>{
  const original=emptySession(), recovered={...original,nav_width:320}
  calls.connect.mockResolvedValue('workspace_probe');calls.read.mockResolvedValue({data:original,etag:'"synthetic-full-r1"'})
  const cache=new QueryClient({defaultOptions:{queries:{retry:false}}})
  const wrapper=({children}:{children:ReactNode})=><QueryClientProvider client={cache}>{children}</QueryClientProvider>
  const view=renderHook(()=>useWorkbench(),{wrapper})
  await waitFor(()=>expect(view.result.current.status).toBe('saved'))
  let release!:(value:unknown)=>void
  calls.read.mockReturnValueOnce(new Promise(resolve=>{release=resolve}))
  let restoring!:Promise<void>
  act(()=>{restoring=view.result.current.restorePending({key:'another-page-pending',session:recovered,base:original,etag:'"synthetic-full-r1"'})})
  act(()=>view.result.current.set(value=>({...value,nav_width:340})))
  expect(view.result.current.session.nav_width).toBe(340)
  await act(async()=>{release({data:original,etag:'"synthetic-full-r1"'});await restoring})
  expect(view.result.current.session.nav_width).toBe(340)
  expect(JSON.parse(readLocal(pendingKey('workspace_probe'))!).session.nav_width).toBe(340)
  expect(view.result.current.error).toMatch(/新改动|新修改/)
})

test('explicit server choice must not discard edits made after that choice',async()=>{
  const original=emptySession()
  calls.connect.mockResolvedValue('workspace_probe');calls.read.mockResolvedValue({data:original,etag:'"synthetic-full-r1"'})
  const cache=new QueryClient({defaultOptions:{queries:{retry:false}}})
  const wrapper=({children}:{children:ReactNode})=><QueryClientProvider client={cache}>{children}</QueryClientProvider>
  const view=renderHook(()=>useWorkbench(),{wrapper})
  await waitFor(()=>expect(view.result.current.status).toBe('saved'))
  let release!:(value:unknown)=>void, entered!:()=>void
  const started=new Promise<void>(resolve=>{entered=resolve})
  calls.read.mockImplementationOnce(()=>{entered();return new Promise(resolve=>{release=resolve})})
  let reconnecting!:Promise<void>
  await act(async()=>{reconnecting=view.result.current.reconnect(true);await started})
  act(()=>view.result.current.set(value=>({...value,nav_width:340})))
  expect(view.result.current.session.nav_width).toBe(340)
  await act(async()=>{release({data:original,etag:'"synthetic-full-r1"'});await reconnecting})
  expect(view.result.current.session.nav_width).toBe(340)
  expect(JSON.parse(readLocal(pendingKey('workspace_probe'))!).session.nav_width).toBe(340)
  expect(view.result.current.error).toMatch(/新改动|新修改/)
})

test('initial navigation cannot turn the unread placeholder into a conflicting local candidate',async()=>{
  const original={...emptySession(),revision:4,navigation:'textbook' as const,course_ref:{entity:'course' as const,id:'saved_course',revision:1,sha256:'a'.repeat(64)}}
  localStorage.setItem('learning-workbench.last-confirmed-workspace.v1','workspace_probe')
  calls.connect.mockResolvedValue('workspace_probe')
  let release!:(value:unknown)=>void, entered!:()=>void
  const started=new Promise<void>(resolve=>{entered=resolve})
  calls.read.mockImplementationOnce(()=>{entered();return new Promise(resolve=>{release=resolve})})
  const cache=new QueryClient({defaultOptions:{queries:{retry:false}}})
  const wrapper=({children}:{children:ReactNode})=><QueryClientProvider client={cache}>{children}</QueryClientProvider>
  const view=renderHook(()=>useWorkbench(),{wrapper})
  await act(async()=>{await started})
  act(()=>view.result.current.set(value=>({...value,navigation:'practice'})))
  expect(view.result.current.session.navigation).toBe('route')
  expect(readLocal(pendingKey('workspace_probe'))).toBeNull()
  expect(calls.save).not.toHaveBeenCalled()
  await act(async()=>{release({data:original,etag:'"synthetic-full-r4"'})})
  await waitFor(()=>expect(view.result.current.status).toBe('saved'))
  expect(view.result.current.session).toEqual(original)
  expect(view.result.current.comparison).toBeNull()
})

test('a failed first connection without a local session stays unavailable until a real read succeeds',async()=>{
  localStorage.setItem('learning-workbench.last-confirmed-workspace.v1','workspace_probe')
  calls.connect.mockRejectedValueOnce(new Error('temporarily unavailable'))
  const cache=new QueryClient({defaultOptions:{queries:{retry:false}}})
  const wrapper=({children}:{children:ReactNode})=><QueryClientProvider client={cache}>{children}</QueryClientProvider>
  const view=renderHook(()=>useWorkbench(),{wrapper})
  await waitFor(()=>expect(view.result.current.status).toBe('offline'))
  expect(view.result.current.uiReady).toBe(false)
  act(()=>view.result.current.set(value=>({...value,nav_width:340})))
  expect(readLocal(pendingKey('workspace_probe'))).toBeNull()
  const original={...emptySession(),revision:4,nav_width:320}
  calls.connect.mockResolvedValue('workspace_probe');calls.read.mockResolvedValue({data:original,etag:'"synthetic-full-r4"'})
  await act(async()=>{await view.result.current.reconnect()})
  expect(view.result.current.uiReady).toBe(true)
  expect(view.result.current.status).toBe('saved')
  expect(view.result.current.session).toEqual(original)
})

test('an actual offline candidate remains editable while its later reconnect is reading',async()=>{
  const original={...emptySession(),revision:4}, candidate={...original,nav_width:320}
  localStorage.setItem('learning-workbench.last-confirmed-workspace.v1','workspace_probe')
  localStorage.setItem(pendingKey('workspace_probe'),JSON.stringify({session:candidate,base:original,etag:'"synthetic-full-r4"'}))
  calls.connect.mockRejectedValueOnce(new Error('temporarily unavailable'))
  const cache=new QueryClient({defaultOptions:{queries:{retry:false}}})
  const wrapper=({children}:{children:ReactNode})=><QueryClientProvider client={cache}>{children}</QueryClientProvider>
  const view=renderHook(()=>useWorkbench(),{wrapper})
  await waitFor(()=>expect(view.result.current.status).toBe('offline'))
  expect(view.result.current.uiReady).toBe(true)
  expect(view.result.current.session).toEqual(candidate)
  calls.connect.mockResolvedValue('workspace_probe')
  let release!:(value:unknown)=>void, entered!:()=>void
  const started=new Promise<void>(resolve=>{entered=resolve})
  calls.read.mockImplementationOnce(()=>{entered();return new Promise(resolve=>{release=resolve})})
  let reconnecting!:Promise<void>
  await act(async()=>{reconnecting=view.result.current.reconnect();await started})
  expect(view.result.current.status).toBe('connecting')
  expect(view.result.current.uiReady).toBe(true)
  act(()=>view.result.current.set(value=>({...value,nav_width:340})))
  await act(async()=>{release({data:original,etag:'"synthetic-full-r4"'});await reconnecting})
  expect(view.result.current.session.nav_width).toBe(340)
  expect(view.result.current.comparison).toBeNull()
  expect(view.result.current.status).toBe('saving')
  expect(JSON.parse(readLocal(pendingKey('workspace_probe'))!)).toEqual({session:{...candidate,nav_width:340},base:original,etag:'"synthetic-full-r4"'})
})

test('an already read server session remains editable during a normal reconnect',async()=>{
  const original={...emptySession(),revision:4}
  calls.connect.mockResolvedValue('workspace_probe');calls.read.mockResolvedValue({data:original,etag:'"synthetic-full-r4"'})
  const cache=new QueryClient({defaultOptions:{queries:{retry:false}}})
  const wrapper=({children}:{children:ReactNode})=><QueryClientProvider client={cache}>{children}</QueryClientProvider>
  const view=renderHook(()=>useWorkbench(),{wrapper})
  await waitFor(()=>expect(view.result.current.status).toBe('saved'))
  let release!:(value:unknown)=>void, entered!:()=>void
  const started=new Promise<void>(resolve=>{entered=resolve})
  calls.read.mockImplementationOnce(()=>{entered();return new Promise(resolve=>{release=resolve})})
  let reconnecting!:Promise<void>
  await act(async()=>{reconnecting=view.result.current.reconnect();await started})
  expect(view.result.current.uiReady).toBe(true)
  act(()=>view.result.current.set(value=>({...value,nav_width:340})))
  await act(async()=>{release({data:original,etag:'"synthetic-full-r4"'});await reconnecting})
  expect(view.result.current.session.nav_width).toBe(340)
  expect(view.result.current.status).toBe('saving')
  expect(view.result.current.comparison).toBeNull()
  expect(JSON.parse(readLocal(pendingKey('workspace_probe'))!).base).toEqual(original)
})
