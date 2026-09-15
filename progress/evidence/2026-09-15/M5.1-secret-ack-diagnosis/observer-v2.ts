import { writeFileSync } from 'node:fs'
import type { Page } from '<REPO>/apps/web/node_modules/@playwright/test/index.mjs'
let events: object[] = [], pending = new Set<Promise<void>>()
export async function installObservation(page: Page) {
  events = []; pending = new Set()
  const mark = (data: object) => events.push({at_ms:Date.now(),...data})
  let wrote = false, configReads = 0, release!: () => void
  const gate = new Promise<void>(resolve=>{release=resolve})
  page.on('request', request=>{if(request.method()==='POST' && request.url().endsWith('/provider_native_independent/secret')) wrote=true})
  page.on('response', response=>{if(response.request().method()==='DELETE' && response.url().endsWith('/provider_native_independent/secret')) {mark({kind:'release-parent-read-after-delete-response',status:response.status()});release()}})
  await page.route('**/api/v1/providers/provider_native_independent/config', async route=>{
    if(route.request().method()!=='GET'||!wrote){await route.continue();return}
    const ordinal=++configReads, response=await route.fetch(), body=await response.json()
    mark({kind:'upstream-config',ordinal,status:response.status(),revision:body.revision??null,config_sha256:body.config_sha256??null})
    if(ordinal===2 && process.env.SECRET_PARENT_READ_DELAY!=='off') {mark({kind:'hold-parent-read',ordinal});await gate}
    try{await route.fulfill({response});mark({kind:'delivered-config',ordinal})}catch{mark({kind:'closed-before-config-delivery',ordinal})}
  })
  page.on('request', request => {
    const path = new URL(request.url()).pathname
    if (!/^\/api\/v1\/providers\/provider_native_independent\/(config|secret)$/.test(path)) return
    let expected: unknown = null
    try { expected = JSON.parse(request.postData() ?? '{}').expected_revision ?? null } catch {}
    mark({kind:'request',path,method:request.method(),expected_revision:expected,config_if_match:request.headers()['if-match']??null})
  })
  page.on('response', response => {
    const path = new URL(response.url()).pathname
    if (!/^\/api\/v1\/providers\/provider_native_independent\/(config|secret)$/.test(path)) return
    const task = (async () => { try {
      const body = await response.json()
      mark({kind:'response',path,method:response.request().method(),status:response.status(),revision:body.revision??null,config_sha256:body.config_sha256??null,secret_present:body.secret_present??null,error_code:body.error?.code??null})
    } catch { mark({kind:'response-unobserved',path,status:response.status()}) } })()
    pending.add(task); void task.finally(()=>pending.delete(task))
  })
  await page.exposeFunction('__secretAckSafeObservation', (data: object)=>mark(data))
  await page.addInitScript(() => {
    let last = ''
    const inspect = () => {
      const region = document.querySelector('[aria-label="秘密控制"]')
      const text = region instanceof HTMLElement ? region.innerText : ''
      const parent = [...document.querySelectorAll('p')].map(p=>p.innerText).filter(s=>s.startsWith('提供商 provider_native_independent：当前读回'))
      const value = JSON.stringify({kind:'dom',text,parent})
      if(value===last) return
      last=value
      const emit = (window as unknown as {__secretAckSafeObservation:(data: object)=>void}).__secretAckSafeObservation
      emit({kind:'dom',text,parent})
    }
    new MutationObserver(inspect).observe(document,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['disabled']})
  })
}
export async function saveObservation(path: string) {
  await Promise.race([Promise.allSettled([...pending]),new Promise(resolve=>setTimeout(resolve,100))])
  writeFileSync(path,JSON.stringify({scope:'Real upstream messages and safe DOM; no request secret, headers, session or CSRF recorded. Original test body/assertion preserved.',events,pending_body_observers:pending.size},null,2)+'\n')
}
