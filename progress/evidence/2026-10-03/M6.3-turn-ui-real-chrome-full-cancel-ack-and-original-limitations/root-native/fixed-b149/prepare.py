from pathlib import Path

B = Path('$HOME/.cache/learning-workbench-acceptance')
old = B / 'm63-turn-ui-root-native-oct04/fixed-db5-04'
out = Path(__file__).parent
tree = 'm63-codex-turn-ui-cancel-binding-owner-oct04'
source = (old / 'native.mjs').read_text()
source = source.replace('m63-codex-turn-ui-restore-owner-oct04', tree).replace('db5a6bceaeadf099de9b3a9e6d6a7ce786071db2', 'b149fda25f4b007ffb4858a9b327c536a462c065')
old_cancel = """ const cancelled=await clickPost(page,control.getByRole('button',{name:`明确取消回合 Job ${lost.value.job.id}`,exact:true}),`/api/v1/jobs/${lost.value.job.id}/cancel`,200)
 assert.equal(cancelled.value.status,'cancelled');assert.equal(cancelled.body.expected_revision,1)
"""
new_cancel = """ const cancelPath=`/api/v1/jobs/${lost.value.job.id}/cancel`;let lostCancel
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
"""
assert source.count(old_cancel) == 1
source = source.replace(old_cancel, new_cancel)
# The control region is reconstructed after reload; retain the live locator.
source = source.replace('const control=p.getByRole', 'let control=p.getByRole')
needle = "await p.getByRole('button',{name:`读取回合控制 ${lost.value.turn_id}`,exact:true}).click();await expect(control).toContainText('cancelled')"
assert source.count(needle) == 1
source = source.replace(needle, "await p.getByRole('button',{name:`读取回合控制 ${lost.value.turn_id}`,exact:true}).click();control=p.getByRole('region',{name:`当前回合控制 ${lost.value.turn_id}`,exact:true});await expect(control).toContainText('cancelled')")
source = source.replace("facts.status='NATIVE_TURN_UI_CONTROLLED_BOOTSTRAP_PASS'", "facts.status='NATIVE_TURN_UI_FULL_CANCEL_ACK_CONTROLLED_BOOTSTRAP_PASS'")
source = source.replace('actual safe GET/page supplies revision for actual cancel200;', 'actual safe GET/page supplies revision for actual cancel200 with original full ACK replay/persistence;')
(out / 'native.mjs').write_text(source)
(out / 'controlled_api.py').write_bytes((old / 'controlled_api.py').read_bytes())
runner = (old / 'run.py').read_text().replace('m63-codex-turn-ui-restore-owner-oct04', tree)
runner = runner.replace('Independent root native fixed-db5-03 actual execution; original02 FAIL and original preflightNOT_RUN retained, no model/CLI', 'Independent root native fixed-b149 actual execution; original db5 preflight/02/03 FAIL and04 limitedPASS retained. Includes full durable cancel ACK, loss/reload and exact original replay; explicit synthetic bootstrap, no model/CLI')
(out / 'run.py').write_text(runner)
print('PREPARED_FIXED_B149_NATIVE_FULL_CANCEL_ACK_CHECK_NOT_YET_EXECUTED')
