import { createServer, type ServerResponse } from 'node:http'
import { writeFileSync } from 'node:fs'
import { test, expect, type Page } from '<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-codex-turn-event-ui-oct05/apps/web/node_modules/@playwright/test/index.mjs'
import type { CodexTurnEvent } from '<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-codex-turn-event-ui-oct05/packages/contracts/generated/codex-turn-types'
const frames: ServerResponse[]=[], requests: {method:string,path:string}[]=[], errors:string[]=[]
let actor='actor_event_native'
const server=createServer((req,res)=>{
 const path=req.url??'/',method=req.method??'';requests.push({method,path})
 if(method!=='GET'){res.writeHead(405);res.end();return}
 if(path==='/api/v1/session'){res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify({workspace_id:'workspace_event_native',actor_session_id:actor,role:'author',csrf_token:'synthetic-native-only',active_independent_attempt_id:null,active_open_book_attempt_id:null}));return}
 if(/^\/api\/v1\/codex\/turns\/turn_native\/events\?after_seq=\d+$/.test(path)){
  res.writeHead(200,{'Content-Type':'text/event-stream','Cache-Control':'no-store','Connection':'keep-alive'});res.flushHeaders();frames.push(res);return
 }
 res.writeHead(404);res.end()
})
test.beforeAll(async()=>{await new Promise<void>(resolve=>server.listen(9187,'127.0.0.1',resolve))})
test.afterEach(async({},info)=>{writeFileSync(info.outputPath('diagnostic.json'),JSON.stringify({page_errors:errors,requests},null,2))})
test.afterAll(async()=>{for(const stream of frames)stream.end();server.closeAllConnections();await new Promise<void>(resolve=>server.close(()=>resolve()))})
const value=(seq:number,payload:CodexTurnEvent['payload']):CodexTurnEvent=>({turn_id:'turn_native',run_id:'job_native',seq,occurred_at:'2026-10-05T00:00:00Z',payload})
const send=(event:CodexTurnEvent)=>frames.at(-1)!.write(`id: job_native:${event.seq}\nevent: ${event.payload.type}\ndata: ${JSON.stringify(event)}\n\n`)
const html=`<!doctype html><html lang="zh"><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{font:16px system-ui;margin:16px}button{max-width:100%;overflow-wrap:anywhere;margin:4px}pre{border:1px solid #aaa;padding:8px}</style></head><body><main id="root"></main><script type="module">
import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;
await import('/.local_data/event-harness.tsx');</script></body></html>`
async function open(page:Page){page.on('pageerror',error=>errors.push(error.message));await page.route('**/__event_reader__',route=>route.fulfill({status:200,contentType:'text/html',body:html}));await page.goto('/__event_reader__');await expect(page.getByRole('button',{name:'明确连接回合事件 turn_native',exact:true})).toBeEnabled()}
test('actual browser stream preserves raw bytes and reconnect cursor, isolates fresh actor, and only issues GET',async({page},info)=>{
 await open(page);expect(requests).toEqual([])
 await page.getByRole('button',{name:'明确连接回合事件 turn_native',exact:true}).click()
 await expect.poll(()=>frames.length).toBe(1)
 send(value(1,{type:'status',job:{id:'job_native',status:'running'},run_revision:2}))
 const first='  α\n中文😀\t\n  '
 send(value(2,{type:'answer_delta',text:first}));send(value(3,{type:'approval_required',approval_id:'approval_native'}));send(value(4,{type:'manifest_ready',manifest_id:'manifest_native',manifest_sha256:'a'.repeat(64)}))
 await expect.poll(()=>page.getByLabel('Codex 事件原文',{exact:true}).textContent()).toBe(first)
 await expect(page.getByText(/产物清单 ID manifest_native/)).toBeVisible()
 await page.getByRole('button',{name:'断开此事件连接',exact:true}).click()
 await expect(page.getByText(/连接中断，任务状态未知/)).toBeVisible();expect(frames).toHaveLength(1)
 await page.getByRole('button',{name:'从原游标明确重连 job_native:4',exact:true}).click()
 await expect.poll(()=>frames.length).toBe(2)
 send(value(5,{type:'answer_delta',text:'tail\n '}));send(value(6,{type:'usage',usage:{input_tokens:12,output_tokens:4}}));send(value(7,{type:'terminal',outcome:'completed',error_code:null}));frames.at(-1)!.end()
 const answer=first+'tail\n '
 await expect.poll(()=>page.getByLabel('Codex 事件原文',{exact:true}).textContent()).toBe(answer)
 await expect(page.getByText(/已观察终态事件：completed/)).toBeVisible()
 const bounds=[]
 for(const width of [1440,390]){await page.setViewportSize({width,height:900});bounds.push(await page.evaluate(()=>({width:innerWidth,document:document.documentElement.scrollWidth})));expect(bounds.at(-1)!.document).toBeLessThanOrEqual(width);await page.screenshot({path:info.outputPath(`events-${width}.png`),fullPage:true})}
 expect(requests.filter(v=>v.path.includes('/events'))).toEqual([{method:'GET',path:'/api/v1/codex/turns/turn_native/events?after_seq=0'},{method:'GET',path:'/api/v1/codex/turns/turn_native/events?after_seq=4'}])
 const beforeReload=requests.length;await page.reload();await expect(page.getByRole('button',{name:'明确连接回合事件 turn_native',exact:true})).toBeEnabled();expect(frames).toHaveLength(2);expect(requests).toHaveLength(beforeReload)
 await page.getByRole('button',{name:'明确连接回合事件 turn_native',exact:true}).click();await expect.poll(()=>frames.length).toBe(3)
 send(value(1,{type:'answer_delta',text:'synthetic protected answer'}));await expect.poll(()=>page.getByLabel('Codex 事件原文',{exact:true}).textContent()).toBe('synthetic protected answer')
 actor='actor_event_changed';send(value(2,{type:'answer_delta',text:'late answer must be isolated'}))
 await expect(page.getByText(/事件显示已清除/)).toBeVisible();await expect(page.getByLabel('Codex 事件原文',{exact:true})).toHaveCount(0)
 expect(requests.every(v=>v.method==='GET')).toBe(true);expect(errors).toEqual([])
 writeFileSync(info.outputPath('codex-events-actual.json'),JSON.stringify({scope:'Real Chrome and production React event component/typed fetch client; synthetic loopback session and six-variant SSE. No production backend owner, CLI, model, account, tools, or approval/import execution.',raw_answer:answer,events_seen:7,reconnect_after_seq:4,remount_auto_requests:0,fresh_actor_denial_clears:true,requests,viewport_bounds:bounds,page_errors:errors},null,2))
})
