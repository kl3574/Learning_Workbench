# M3.2 导入策略回归修复：开发证据

主代理的首次完整门禁出现54通过、3失败，本包只保留前端随后定向复现/修复的原始记录派生版，不复制那份完整门禁或把它改写成成功。它们是开发检查，最终完整提交门禁另行绑定。

已证实的主因是 Shell 把暂时未知的测试策略当成卸载 ImportWorkflow 的条件。角色变更已成功，但 active 导入 ID、本机 File 和界面状态随组件重建消失，只剩手动恢复入口。现在组件继续挂载；暂停期间不渲染材料、警告或下载入口。安全占位只显示明确标注为上次确认的角色/流程枚举，角色回执到达后可显示重新核验的角色，不能用旧私件正文满足状态等待。

访问 generation 或暂停变化会使旧读投影、异步回执和下载 URL 失效；恢复须重新读取当前 session/import/draft/source。独立提交后的 private pending guard 仍返回真实409，当前导入 ID 保留但旧内容不重现。原件下载完成校验后再读当前来源权限并比较 source ID/hash/size 与 artifact ID/hash/size；跨 profile 没有广播也不能仅靠旧200直接下载。后端 guard 未放宽。

已上传以及失败任务中重新选择的本机 File 归属持续挂载的 hook，仅留内存；暂停后派生正文和确认需要重新核验。上传表单自身暂停时不输出 DOM，但保留选择的 File/格式。晚上传回执遇到访问变化仍保存导入 ID 和本机文件，并给出显式重读入口。

| 原日志 | 实际结果 | 范围与说明 |
| --- | --- | --- |
| m32-import-regression-red.log | 3 FAIL | Original three existing import tests, unchanged; role succeeded but workflow was remounted into upload/recovery state |
| m32-import-regression-fixed-first.log | 2 PASS / 1 FAIL / 17.0s | First fix hid all status during the held role response; DOCX test could no longer see the safe last-confirmed role/status |
| m32-import-regression-fixed-second.log | 2 PASS / 1 FAIL / 17.1s | Last-confirmed metadata restored; current learner role was still hidden while import refresh was held |
| m32-import-regression-boundary-first.log | 1 PASS / 1 FAIL / 16.2s | Original DOCX case passed. New boundary reached actual protected409, but new assertion expected 测试 while actual error said 测验 |
| m32-import-regression-final.log | 5 PASS / 21.5s | Three unchanged original tests plus two real isolated-runtime scenarios: active→submit pending protection and reselected failed original across role pause |
| m32-import-pause-unit.log | 3 PASS / 1 file | Real UploadForm component retains File and parse choice while suspended DOM is empty |
| m32-import-regression-lint-first.log | PASS | Initial pause implementation type/unused checks |
| m32-import-regression-lint-second.log | PASS | New native test and safe operation metadata compile |
| m32-import-regression-lint-third.log | PASS | Original-source reread and failed-file ownership compile |
| m32-import-regression-lint-final.log | PASS | After late-upload retry message |
| m32-import-regression-units-final.log | 162 PASS / 23 files / 2.97s | Full frontend unit suite after late-upload retry message |
| m32-import-regression-build-final.log | PASS with chunk-size warning | main575.90kB / MathMarkdown2939.32kB;249ms; before final source.id equality predicate |
| m32-import-regression-lint-frozen.log | PASS | After final source.id equality predicate; no claim of rerunning full native afterward |

两个既有 native 测试文件逐字节未改，三项原期待全部保留。新增 imports-policy.spec.ts 使用原创 fixture、真实上传/worker/201创建/202提交/当前409权限，不模拟解析响应；每例单独临时数据库和浏览器运行时。新边界第一次失败仅是自己写的文案断言用词与真实服务端不一致，改成实际“仍受策略保护”，没有降低保护要求。

最终5native之后有两项小改动，freeze-v2 逐项说明：晚 upload 分支补充缓存错误与显式重读提示；最后来源回读增加 current.id === source.id。162unit/lint/build在前一项之后执行；最终lint在后一项之后执行。本包不声称5native已覆盖这两项修改后的全源码，也不声称跨profile末端来源复核在本包新增了独立native场景；主代理随后精确门禁负责最终交付状态。

source-before.json 是修前已有7文件指纹；source-freeze-first.json 和 source-freeze-final.json 是已有后续捕获。保留它们的原始与公开SHA，不补造更完整的历史绑定。本包没有新增截图；此前测验开发图另包明确绑定旧源码，最终截图由主代理在精确源码上复核。

日志脱敏规则、错误块限定提取、SHA清单和逐文件 publication.inspect 结果见 manifest.json/inspection.json。原始材料留原位置；没有复制DOM、浏览器profile、数据库或运行授权值。本包仅准备公开审查，不表示已经发布。
