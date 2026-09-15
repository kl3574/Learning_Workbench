# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: controlled.spec.ts >> actual independent assessment policy keeps settings controls available and denies subject consent reads
- Location: ../../../.cache/learning-workbench-acceptance/m51-secret-ack-diagnosis/controlled.spec.ts:112:1

# Error details

```
Error: route.fetch: socket hang up
Call log:
  - → GET http://127.0.0.1:41535/api/v1/providers/provider_native_independent/config
    - user-agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/153.0.0.0 Safari/537.36
    - accept: */*
    - accept-encoding: gzip,deflate,br
    - accept-language: en-US
    - content-type: application/json
    - cookie: learning_session=<REDACTED_RUNTIME_SESSION>
    - referer: http://127.0.0.1:41535/?assessment=%7B%22assessment_ref%22%3A%7B%22entity%22%3A%22assessment%22%2C%22id%22%3A%22assessment_providerpolicynative%22%2C%22revision%22%3A1%2C%22sha256%22%3A%2261e5d7dadbb6f64acb117b8a88d00c2f79857b733322c0fa867dd0aa9a32885e%22%7D%2C%22course_ref%22%3A%7B%22entity%22%3A%22course%22%2C%22id%22%3A%22course_providerpolicynative%22%2C%22revision%22%3A1%2C%22sha256%22%3A%22cef373d703adb0440f455563f1153dcb44e310f79b1e6e87d6802653a62419ac%22%7D%2C%22attempt_id%22%3A%22attempt_2e1191a65a704ec5921d1871202830f6%22%7D
    - x-csrf-token: <REDACTED_RUNTIME_CSRF>
    - sec-ch-ua: "Google Chrome";v="153", "Not_A Brand";v="8", "Chromium";v="153"
    - sec-ch-ua-mobile: ?0
    - sec-ch-ua-platform: "Linux"

```

# Test source

```ts
  1  | import { writeFileSync } from 'node:fs'
  2  | import type { Page } from '<REPO>/apps/web/node_modules/@playwright/test/index.mjs'
  3  | let events: object[] = [], pending = new Set<Promise<void>>()
  4  | export async function installObservation(page: Page) {
  5  |   events = []; pending = new Set()
  6  |   const mark = (data: object) => events.push({at_ms:Date.now(),...data})
  7  |   let wrote = false, configReads = 0, release!: () => void
  8  |   const gate = new Promise<void>(resolve=>{release=resolve})
  9  |   page.on('request', request=>{if(request.method()==='POST' && request.url().endsWith('/provider_native_independent/secret')) wrote=true})
  10 |   page.on('response', response=>{if(response.request().method()==='DELETE' && response.url().endsWith('/provider_native_independent/secret')) {mark({kind:'release-parent-read-after-delete-response',status:response.status()});release()}})
  11 |   await page.route('**/api/v1/providers/provider_native_independent/config', async route=>{
  12 |     if(route.request().method()!=='GET'||!wrote){await route.continue();return}
> 13 |     const ordinal=++configReads, response=await route.fetch(), body=await response.json()
     |                                                       ^ Error: route.fetch: socket hang up
  14 |     mark({kind:'upstream-config',ordinal,status:response.status(),revision:body.revision??null,config_sha256:body.config_sha256??null})
  15 |     if(ordinal===2 && process.env.SECRET_PARENT_READ_DELAY!=='off') {mark({kind:'hold-parent-read',ordinal});await gate}
  16 |     try{await route.fulfill({response});mark({kind:'delivered-config',ordinal})}catch{mark({kind:'closed-before-config-delivery',ordinal})}
  17 |   })
  18 |   page.on('request', request => {
  19 |     const path = new URL(request.url()).pathname
  20 |     if (!/^\/api\/v1\/providers\/provider_native_independent\/(config|secret)$/.test(path)) return
  21 |     let expected: unknown = null
  22 |     try { expected = JSON.parse(request.postData() ?? '{}').expected_revision ?? null } catch {}
  23 |     mark({kind:'request',path,method:request.method(),expected_revision:expected,config_if_match:request.headers()['if-match']??null})
  24 |   })
  25 |   page.on('response', response => {
  26 |     const path = new URL(response.url()).pathname
  27 |     if (!/^\/api\/v1\/providers\/provider_native_independent\/(config|secret)$/.test(path)) return
  28 |     const task = (async () => { try {
  29 |       const body = await response.json()
  30 |       mark({kind:'response',path,method:response.request().method(),status:response.status(),revision:body.revision??null,config_sha256:body.config_sha256??null,secret_present:body.secret_present??null,error_code:body.error?.code??null})
  31 |     } catch { mark({kind:'response-unobserved',path,status:response.status()}) } })()
  32 |     pending.add(task); void task.finally(()=>pending.delete(task))
  33 |   })
  34 |   await page.exposeFunction('__secretAckSafeObservation', (data: object)=>mark(data))
  35 |   await page.addInitScript(() => {
  36 |     let last = ''
  37 |     const inspect = () => {
  38 |       const region = document.querySelector('[aria-label="秘密控制"]')
  39 |       const text = region instanceof HTMLElement ? region.innerText : ''
  40 |       const parent = [...document.querySelectorAll('p')].map(p=>p.innerText).filter(s=>s.startsWith('提供商 provider_native_independent：当前读回'))
  41 |       const value = JSON.stringify({kind:'dom',text,parent})
  42 |       if(value===last) return
  43 |       last=value
  44 |       const emit = (window as unknown as {__secretAckSafeObservation:(data: object)=>void}).__secretAckSafeObservation
  45 |       emit({kind:'dom',text,parent})
  46 |     }
  47 |     new MutationObserver(inspect).observe(document,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['disabled']})
  48 |   })
  49 | }
  50 | export async function saveObservation(path: string) {
  51 |   await Promise.race([Promise.allSettled([...pending]),new Promise(resolve=>setTimeout(resolve,100))])
  52 |   writeFileSync(path,JSON.stringify({scope:'Real upstream messages and safe DOM; no request secret, headers, session or CSRF recorded. Original test body/assertion preserved.',events,pending_body_observers:pending.size},null,2)+'\n')
  53 | }
  54 | 
```