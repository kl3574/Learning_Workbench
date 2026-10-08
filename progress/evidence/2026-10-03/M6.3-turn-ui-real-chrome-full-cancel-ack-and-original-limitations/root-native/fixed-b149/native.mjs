import { spawn, execFileSync } from 'node:child_process'
import { createServer } from 'node:net'
import { mkdtempSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { createHash } from 'node:crypto'
import { setTimeout as pause } from 'node:timers/promises'
import assert from 'node:assert/strict'
import { chromium, expect } from '$HOME/.cache/learning-workbench-acceptance/m62-public-safe-oct02/apps/web/node_modules/@playwright/test/index.mjs'

const root = '$HOME/.cache/learning-workbench-acceptance/m63-codex-turn-ui-cancel-binding-owner-oct04'
const out = import.meta.dirname, head = 'b149fda25f4b007ffb4858a9b327c536a462c065'
const sha = b => createHash('sha256').update(b).digest('hex')
const git = (...args) => execFileSync('git', args, { cwd: root, encoding: 'utf8' }).trim()
function inputs() {
 assert.equal(git('rev-parse', 'HEAD'), head); assert.equal(git('status', '--porcelain'), '')
 const files = {}
 for (const row of execFileSync('git', ['ls-tree','-rz',head], {cwd:root,maxBuffer:16*1024*1024}).toString().split('\0').filter(Boolean)) {
  const [metadata,name] = row.split('\t'); if (name.startsWith('progress/')) continue
  const data = readFileSync(resolve(root,name)), oid = metadata.split(' ')[2]
  assert.equal(createHash('sha1').update(`blob ${data.length}\0`).update(data).digest('hex'),oid)
  files[name] = {git_blob:oid,sha256:sha(data),bytes:data.length}
 }
 return {head,count:Object.keys(files).length,files}
}
const before = inputs(); writeFileSync(resolve(out,'before.json'),JSON.stringify(before,null,2)+'\n')
mkdirSync(resolve(out,'tmp'), {mode:0o700})
const data = mkdtempSync(resolve(out,'tmp/data-')), profile = mkdtempSync(resolve(out,'tmp/profile-'))
async function port() { const s=createServer(); await new Promise((ok,no)=>{s.once('error',no);s.listen(0,'127.0.0.1',ok)}); const n=s.address().port;await new Promise((ok,no)=>s.close(e=>e?no(e):ok()));return n }
const apiPort=await port();let uiPort=await port();while(apiPort===uiPort)uiPort=await port()
const origin=`http://127.0.0.1:${uiPort}`
const env={...process.env,TMPDIR:resolve(out,'tmp'),LEARNING_DATA_DIR:data,LEARNING_UI_ORIGIN:origin,LEARNING_HOST:'127.0.0.1',LEARNING_PORT:String(apiPort),PYTHONPATH:`${out}:${root}`}
let api,ui,browser;const generations=[],calls=[],errors=[],timings=[],pendingRequests=new Map()
function start(cmd,args) { const child=spawn(cmd,args,{cwd:root,env,detached:true,stdio:['ignore','pipe','pipe']});let tail='';for(const stream of [child.stdout,child.stderr])stream.on('data',b=>{tail=(tail+b).slice(-4096)});return {child,tail:()=>tail,exit:new Promise(ok=>child.once('close',ok))} }
async function stop(p) {if(!p?.child.pid)return;try{process.kill(-p.child.pid,'SIGTERM')}catch(e){if(e.code!=='ESRCH')throw e}let timer;await Promise.race([p.exit,new Promise(ok=>{timer=setTimeout(()=>{try{process.kill(-p.child.pid,'SIGKILL')}catch(e){if(e.code!=='ESRCH')throw e}ok()},5000)})]);clearTimeout(timer);await p.exit}
async function ready(url,p) {for(let n=0;n<400;n++){if(p.child.exitCode!==null)throw Error('Owned server exited before readiness');try{if((await fetch(url,{signal:AbortSignal.timeout(500)})).ok)return}catch{}await pause(50)}throw Error('Owned server readiness timeout')}
async function startApi() {api=start(`${root}/.venv/bin/python`,['-B','-m','uvicorn','controlled_api:create_app','--factory','--host','127.0.0.1','--port',String(apiPort),'--no-access-log']);await ready(`http://127.0.0.1:${apiPort}/health`,api);generations.push(api.child.pid)}
async function open() {browser=await chromium.launchPersistentContext(profile,{executablePath:'/usr/bin/google-chrome',headless:true,baseURL:origin,viewport:{width:1440,height:900}});const page=browser.pages()[0];page.setDefaultTimeout(15000);page.on('pageerror',()=>errors.push('PAGE_ERROR'));page.on('request',req=>{if(new URL(req.url()).pathname.startsWith('/api/'))pendingRequests.set(req,performance.now())});page.on('response',res=>{const req=res.request(),t=pendingRequests.get(req);if(t!==undefined){timings.push({method:req.method(),path:new URL(req.url()).pathname,status:res.status(),elapsed_ms:Math.round(performance.now()-t)});pendingRequests.delete(req)}});page.on('request',r=>{const path=new URL(r.url()).pathname;if(path.startsWith('/api/v1/codex/')||/^\/api\/v1\/jobs\/[^/]+\/cancel$/.test(path))calls.push(`${r.method()} ${path}`)});return page}
async function headers(page,key) {const s=await page.request.get('/api/v1/session').then(r=>r.json());return {Origin:origin,'X-CSRF-Token':s.csrf_token,'Idempotency-Key':key}}
async function clickPost(page,button,path,status) {const wait=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname===path);await button.click();const r=await wait;assert.equal(r.status(),status);return {value:await r.json(),bytes:await r.body(),body:r.request().postDataJSON(),key:await r.request().headerValue('idempotency-key'),path}}
async function stored(page,name) {return page.evaluate(name=>new Promise((ok,no)=>{const req=indexedDB.open(name,1);req.onerror=()=>no(Error('IDB open failed'));req.onsuccess=()=>{const db=req.result,tx=db.transaction('drafts','readonly'),get=tx.objectStore('drafts').getAll();get.onerror=()=>no(Error('IDB read failed'));get.onsuccess=()=>{ok(JSON.stringify(get.result.sort((a,b)=>a.objectId.localeCompare(b.objectId))));db.close()}}}),name)}
const bootstrapDb='learning-workbench.codex-bootstrap-commands.v1',commandsDb='learning-workbench.codex-turn-commands.v1',formsDb='learning-workbench.codex-turn-forms.v1'
async function panels(page) {await page.getByRole('button',{name:'创作',exact:true}).click();return {bootstrap:page.getByRole('region',{name:'本地控制会话',exact:true}),turn:page.getByRole('region',{name:'Codex 回合准备与安全控制',exact:true})}}
async function readBootstrap(p,id) {await p.getByRole('button',{name:`读取准备当前状态 ${id}`,exact:true}).click();await expect(p.getByRole('region',{name:'当前冻结准备',exact:true})).toBeVisible()}
async function readTurn(p) {await p.getByRole('button',{name:'读取回合记录与权限',exact:true}).click();await expect(p.getByText('已读取本机记录；当前 session、回合与准备须分别显式读取。',{exact:true})).toBeVisible()}
async function select(p,sid) {await p.getByLabel('已建立的 session ID',{exact:true}).fill(sid);await p.getByRole('button',{name:'独立读取当前 session',exact:true}).click();await expect(p.getByRole('region',{name:'独立 GET 当前 session',exact:true})).toBeVisible()}
const facts={source:head,controlled_bootstrap:true,actual_Codex_CLI:'NOT_RUN',actual_external_model:'NOT_RUN',actual_external_requests:0,assertions:[]}
try {
 await startApi();ui=start('bash',['scripts/node.sh','npm','--prefix','apps/web','run','dev','--','--port',String(uiPort)]);await ready(origin,ui);let page=await open()
 // Authentication stays private/in memory, never in evidence or logs.
 const code=execFileSync(`${root}/.venv/bin/python`,['-B','-c','from services.api.app.config import Settings; from services.api.app.database import Database; from services.api.app.security import issue_bootstrap_code; d=Database(Settings.from_env()); d.initialize(); print(issue_bootstrap_code(d))'],{cwd:root,env,encoding:'utf8'}).trim()
 await page.goto(`${origin}/#bootstrap=${code}`);await expect(page.getByText('✓ UI 会话已保存',{exact:true})).toBeVisible();assert.equal(page.url(),`${origin}/`)
 assert.equal((await page.request.post('/api/v1/session/role',{data:{role:'author'},headers:await headers(page,'native-turn-author')})).status(),200)
 await page.reload();await expect(page.getByText('✓ UI 会话已保存',{exact:true})).toBeVisible()
 assert.equal((await page.request.put('/api/v1/providers/codex_local/config',{data:{expected_revision:0,adapter:'compatible_chat',base_url:'https://example.invalid',model:'synthetic-model',embedding_model:null,endpoint_policy:'public_https',pricing:null},headers:await headers(page,'native-turn-config')})).status(),200)
 let {bootstrap:b,turn:p}=await panels(page)
 await b.getByRole('button',{name:'读取本地会话记录',exact:true}).click()
 const prepared=await clickPost(page,b.getByRole('button',{name:'准备本地控制会话',exact:true}),'/api/v1/codex/session-preparations',201)
 await readBootstrap(b,prepared.value.id)
 await clickPost(page,b.getByRole('button',{name:'仅批准这一次本地建会话',exact:true}),`/api/v1/codex/session-preparations/${prepared.value.id}/decision`,200)
 await readBootstrap(b,prepared.value.id)
 const created=await clickPost(page,b.getByRole('button',{name:'明确创建这次本地会话',exact:true}),'/api/v1/codex/sessions',201),sid=created.value.id
 assert.equal(created.value.status,'ready');assert.equal(created.value.revision,2)
 await readBootstrap(b,prepared.value.id);const oldBootstrap=await stored(page,bootstrapDb)
 await b.getByRole('button',{name:`用于回合准备 ${sid}`,exact:true}).click();await readTurn(p)
 await p.getByRole('button',{name:`选择已核验会话 ${sid}`,exact:true}).click()
 const message=' 原始中文 α🙂\n第二行保留空格  '
 await p.getByLabel('回合原文',{exact:true}).fill(message);await p.getByLabel('Provider ID',{exact:true}).fill('codex_local')
 await expect(p.getByRole('button',{name:'明确准备回合并预约 Job',exact:true})).toBeDisabled()
 await p.getByRole('button',{name:'独立读取当前 session',exact:true}).click();await expect(p.getByRole('region',{name:'独立 GET 当前 session',exact:true})).toBeVisible()
 const path=`/api/v1/codex/sessions/${sid}/turn-preparations`;let lost
 await page.route(`**${path}`,async route=>{
  const request=route.request(),body=request.postDataJSON(),key=await request.headerValue('idempotency-key')
  const durable=JSON.parse(await stored(page,commandsDb)).map(v=>JSON.parse(v.text));const original=durable.find(v=>v.command_id===key)
  assert.ok(original);assert.equal(original.ack,null);assert.deepEqual(original.body,body);assert.equal(original.basis.revision,2)
  const result=await route.fetch();assert.equal(result.status(),202);lost={body,key,bytes:await result.body(),value:await result.json(),path}
  await route.abort('failed')
 },{times:1})
 await p.getByRole('button',{name:'明确准备回合并预约 Job',exact:true}).click()
 await expect(p.getByText('操作结果或本机保存尚未确认；原命令和表单保留，不自动重发。',{exact:true})).toBeVisible()
 assert.equal(lost.body.message,message);assert.deepEqual(lost.body.context_refs,[]);assert.deepEqual(lost.body.tools,{max_tool_calls:0,wall_seconds:30});assert.equal(lost.value.validity,'unavailable')
 assert.equal(await stored(page,bootstrapDb),oldBootstrap)
 const firstPostCount=calls.filter(v=>v===`POST ${path}`).length;assert.equal(firstPostCount,1)
 await page.reload();await expect(page.getByText('✓ UI 会话已保存',{exact:true})).toBeVisible();({bootstrap:b,turn:p}=await panels(page));await readTurn(p)
 assert.equal(calls.filter(v=>v===`POST ${path}`).length,1)
 const replay=await clickPost(page,p.getByRole('button',{name:`显式回放回合原 key ${lost.key}`,exact:true}),path,202)
 assert.deepEqual(replay.body,lost.body);assert.equal(replay.key,lost.key);assert.deepEqual(replay.bytes,lost.bytes)
 await expect(p.getByText('准备原 ACK 已保存；只预约 Job，未执行。当前状态须独立 GET。',{exact:true})).toBeVisible()
 const recorded=JSON.parse(await stored(page,commandsDb)).map(v=>JSON.parse(v.text));assert.deepEqual(recorded.find(v=>v.command_id===lost.key).ack,lost.value)
 const drafts=JSON.parse(await stored(page,formsDb)).map(v=>JSON.parse(v.text));const final=drafts.filter(v=>v.fields.message===message&&v.fields.provider_id==='codex_local').sort((a,b)=>b.sequence-a.sequence)[0];assert.ok(final)
 const restoreStarted=performance.now();await p.getByRole('button',{name:`恢复原表单 ${final.draft_id} · ${final.sequence}`,exact:true}).click();await p.getByText('原表单已核验并恢复为独立本机分支；未发送准备或取消请求。',{exact:true}).waitFor({state:'visible',timeout:15000});facts.restore_locator_diagnostic={exact_label_count:await p.getByLabel('回合原文',{exact:true}).count(),accessible_role_count:await p.getByRole('textbox',{name:'回合原文',exact:true}).count(),dom:await p.evaluate(e=>{const a=e.querySelector('textarea');return {wrapping_label_text:a?.parentElement?.textContent,value:a?.value}})};await expect(p.getByRole('textbox',{name:'回合原文',exact:true})).toHaveValue(message,{timeout:15000});facts.restore_completion_ms=Math.round(performance.now()-restoreStarted)
 await p.getByRole('button',{name:`独立读取准备详情 ${lost.value.id}`,exact:true}).click();await expect(p.getByRole('region',{name:'当前回合准备详情',exact:true})).toContainText('unavailable')
 await select(p,sid);await expect(p.getByRole('region',{name:'独立 GET 当前 session',exact:true})).toContainText(`r3 · 活动回合 ${lost.value.turn_id}`)
 facts.assertions.push('real UI persists original actor/key/body/GET basis before POST; actual HTTP202 response deliberately lost; reload sends zero POST; explicit same-key replay returns byte-exact original ACK; Unicode unsent form recovered; unavailable detail honest')
 const formsBeforeRole=await stored(page,formsDb)
 assert.equal((await page.request.post('/api/v1/session/role',{data:{role:'learner'},headers:await headers(page,'native-turn-learner')})).status(),200)
 await page.reload();await expect(page.getByText('✓ UI 会话已保存',{exact:true})).toBeVisible();({bootstrap:b,turn:p}=await panels(page));await readTurn(p)
 assert.equal(await stored(page,formsDb),formsBeforeRole);await expect(p.getByLabel('回合原文',{exact:true})).toHaveCount(0);assert.ok(!(await p.innerText()).includes(message))
 await select(p,sid);await p.getByRole('button',{name:'读取安全回合分页',exact:true}).click();await p.getByRole('button',{name:`读取回合控制 ${lost.value.turn_id}`,exact:true}).first().click()
 let control=p.getByRole('region',{name:`当前回合控制 ${lost.value.turn_id}`,exact:true});await expect(control).toContainText('awaiting_approval')
 const cancelPath=`/api/v1/jobs/${lost.value.job.id}/cancel`;let lostCancel
 await page.route(`**${cancelPath}`,async route=>{
  const request=route.request(),body=request.postDataJSON(),key=await request.headerValue('idempotency-key')
  const durable=JSON.parse(await stored(page,commandsDb)).map(v=>JSON.parse(v.text));const original=durable.find(v=>v.command_id===key)
  assert.ok(original);assert.equal(original.kind,'cancel');assert.equal(original.ack,null);assert.deepEqual(original.body,body)
  assert.equal(original.basis.job.id,lost.value.job.id);assert.equal(original.basis.job_revision,1)
  const result=await route.fetch();assert.equal(result.status(),200)
  lostCancel={body,key,bytes:await result.body(),value:await result.json(),path:cancelPath,original}
  await route.abort('failed')
 },{times:1})
 await control.getByRole('button',{name:`明确取消回合 Job ${lost.value.job.id}`,exact:true}).click()
 await expect(p.getByText('操作结果或本机保存尚未确认；原命令和表单保留，不自动重发。',{exact:true})).toBeVisible()
 assert.equal(lostCancel.value.status,'cancelled');assert.equal(lostCancel.value.kind,'codex_turn');assert.equal(lostCancel.value.revision,2)
 assert.equal(lostCancel.body.expected_revision,1)
 assert.deepEqual(Object.keys(lostCancel.value).sort(),['id','workspace_id','kind','status','revision','created_at','updated_at','progress','result_refs','warnings','error'].sort())
 assert.equal(JSON.parse(await stored(page,commandsDb)).map(v=>JSON.parse(v.text)).find(v=>v.command_id===lostCancel.key).ack,null)
 assert.equal(calls.filter(v=>v===`POST ${cancelPath}`).length,1)
 await page.reload();await expect(page.getByText('✓ UI 会话已保存',{exact:true})).toBeVisible();({bootstrap:b,turn:p}=await panels(page));await readTurn(p)
 assert.equal(calls.filter(v=>v===`POST ${cancelPath}`).length,1)
 const cancelled=await clickPost(page,p.getByRole('button',{name:`显式回放回合原 key ${lostCancel.key}`,exact:true}),cancelPath,200)
 assert.equal(cancelled.key,lostCancel.key);assert.deepEqual(cancelled.body,lostCancel.body);assert.deepEqual(cancelled.bytes,lostCancel.bytes)
 await expect(p.getByText('取消原 ACK 已保存；当前控制须独立 GET，取消请求不证明远端已停止。',{exact:true})).toBeVisible()
 const cancelSaved=JSON.parse(await stored(page,commandsDb)).map(v=>JSON.parse(v.text)).find(v=>v.command_id===lostCancel.key)
 assert.deepEqual(cancelSaved,{...lostCancel.original,ack:lostCancel.value})
 assert.equal(calls.filter(v=>v===`POST ${cancelPath}`).length,2)
 await page.reload();await expect(page.getByText('✓ UI 会话已保存',{exact:true})).toBeVisible();({bootstrap:b,turn:p}=await panels(page));await readTurn(p)
 assert.equal(calls.filter(v=>v===`POST ${cancelPath}`).length,2)
 assert.deepEqual(JSON.parse(await stored(page,commandsDb)).map(v=>JSON.parse(v.text)).find(v=>v.command_id===lostCancel.key),cancelSaved)
 await expect(p.getByText('取消回合 Job · 原 ACK 已记录，不是当前状态',{exact:true})).toBeVisible()
 await select(p,sid)
 facts.cancel_ack={original_http_ack_sha256:sha(lostCancel.bytes),replayed_http_ack_sha256:sha(cancelled.bytes),original_complete_command_sha256:sha(JSON.stringify(lostCancel.original)),saved_complete_ack_sha256:sha(JSON.stringify(cancelSaved.ack)),complete_ack_fields:Object.keys(cancelSaved.ack).sort(),post_count:2,refresh_automatic_post_count:0,original_command_fields_unchanged:true}
 facts.assertions.push('real cancel HTTP200 deliberately lost; original full command durable beforePOST; refresh zeroautomaticPOST; explicit samekey/fullbody replay byteexact original fullJobSnapshot; full ACK persisted with original actor/key/body/basis unchanged; another refresh retains complete ACK withoutPOST')
 await p.getByRole('button',{name:'独立读取当前 session',exact:true}).click();await expect(p.getByRole('region',{name:'独立 GET 当前 session',exact:true})).toContainText('r5 · 活动回合 无')
 await p.getByRole('button',{name:'读取安全回合分页',exact:true}).click();await p.getByRole('button',{name:`读取回合控制 ${lost.value.turn_id}`,exact:true}).click();control=p.getByRole('region',{name:`当前回合控制 ${lost.value.turn_id}`,exact:true});await expect(control).toContainText('cancelled')
 assert.equal(await stored(page,bootstrapDb),oldBootstrap)
 for(const width of [1440,390]){await page.setViewportSize({width,height:900});await control.scrollIntoViewIfNeeded();const geometry=await page.getByRole('dialog',{name:'创作',exact:true}).evaluate(e=>({client:e.clientWidth,scroll:e.scrollWidth,viewport:innerWidth,document:document.documentElement.scrollWidth}));assert.ok(geometry.scroll<=geometry.client+1&&geometry.document<=geometry.viewport);writeFileSync(resolve(out,`learner-cancel-${width}-geometry.json`),JSON.stringify(geometry,null,2));await page.screenshot({path:resolve(out,`learner-cancel-${width}.png`)})}
 facts.assertions.push('learner fresh page has no prompt/form/preparation delivery; original IndexedDB form bytes preserved; actual safe GET/page supplies revision for actual cancel200 with original full ACK replay/persistence; terminal GET r5/null; old bootstrap records unchanged; 1440/390 no horizontal overflow')
 const oldCommands=await stored(page,commandsDb),posts=calls.filter(v=>v.startsWith('POST ')).length
 await browser.close();browser=undefined;await stop(api);api=undefined;await startApi();page=await open();await page.goto(origin);await expect(page.getByText('✓ UI 会话已保存',{exact:true})).toBeVisible();({bootstrap:b,turn:p}=await panels(page));await readTurn(p);await select(p,sid)
 await expect(p.getByRole('region',{name:'独立 GET 当前 session',exact:true})).toContainText('r5 · 活动回合 无');assert.equal(await stored(page,commandsDb),oldCommands);assert.equal(await stored(page,bootstrapDb),oldBootstrap);assert.equal(calls.filter(v=>v.startsWith('POST ')).length,posts)
 assert.equal(new Set(generations).size,2);assert.equal(readFileSync(resolve(data,'synthetic-bootstrap-count.txt'),'utf8'),'synthetic-bootstrap\n');assert.deepEqual(errors,[])
 const after=inputs();assert.deepEqual(after,before);writeFileSync(resolve(out,'after.json'),JSON.stringify(after,null,2)+'\n')
 facts.assertions.push('actual browser close, API process restart, reopen retains actor/IDB/current terminal facts; zero automatic prepare/cancel/model/CLI restart')
 facts.status='NATIVE_TURN_UI_FULL_CANCEL_ACK_CONTROLLED_BOOTSTRAP_PASS';facts.recorded_at=new Date().toISOString();facts.browser=await browser.browser()?.version();facts.complete_nonprogress_git_inputs=before.count;facts.before_after_git_exact=true;facts.bootstrap_ack_sha256=sha(created.bytes);facts.preparation_ack_sha256=sha(lost.bytes);facts.bootstrap_records_sha256=sha(oldBootstrap);facts.calls=calls;facts.safe_http_timings=timings
 facts.boundary='Native Chrome + real app HTTP/SQLite/IndexedDB with explicit synthetic bootstrap only. Actual Codex CLI/model/tools/turn dispatch NOT_RUN; production proof unavailable. Whole M6.3 and academic quality not accepted.'
 writeFileSync(resolve(out,'receipt.json'),JSON.stringify(facts,null,2)+'\n');console.log(facts.status)
} catch(e) {writeFileSync(resolve(out,'failure.json'),JSON.stringify({status:'NATIVE_CHECK_FAIL',source:head,name:e.name,safe_http_timings:timings,message:String(e.message).replace(/#bootstrap=[^\s]*/g,'#bootstrap=REDACTED')},null,2)+'\n');throw e}
finally {await browser?.close();await stop(ui);await stop(api)}
