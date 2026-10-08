固定1e7ad7a8656c0dc8373d4181fa3002f385ed1847只读源码结论：NO REPRODUCIBLE DEFECT ESTABLISHED；旧两CI唯一原因仍UNKNOWN。

INPUT_ALLOWLIST.json绑定21个已读source file的Git blob/size/SHA和实际覆盖段落。初始批量输出截断及仅symbol discovery文件明确区分；完整文件字节hash不代表完整语义审阅。仅seal既有分析，不读原CI raw或本轮runtime，不新增诊断或观测。

确证源码链：

- ReviewMaterialLinks.tsx:8-20 + reader/contentClient.ts:9-24：course→lesson→block metadata→body四次existing GET及父链/ETag/ref/SHA核验，owner/access改变则不open。
- Shell.tsx:120-133 + reader/navigation.ts:10-15：canLeave/引用无冲突/实际session update后才push reader URL。useWorkbench.ts:29-36同步调用functional update，无确证React异步opened旗标缺陷。
- ReaderDocument.tsx:38-54：URL-ready后还有并行course/lesson/current/progress、串行全部lesson blocks，完成才Reader-visible。
- Shell.tsx:142-149,204 + assessment/target.ts:12-20 + model.ts:18-28：返回Review保留view review/attempt/tab identity；AssessmentView.tsx:42打开复盘pinned。preview replacement规则不是该case已证明的缺陷。
- GradingHistory.tsx:7-16 + AssessmentResult.tsx:40 + uiCache.ts:6-7：workspace/tab revision本机key保存和remount恢复；写失败alert；不可读保存revision不会静默换最新。原CI storage/tab状态NOT_CAPTURED。
- useAssessmentAttempt.ts:57-61 + AssessmentView.tsx:46-49 + useGradingResult.ts:28-41：Review回tab还有attempt/access/result读取及render边界。
- Shell.tsx:187-190,232-237 + review.css:12 + PreserveReaderViewport.tsx:25-41：resize变width/drawer，main位置/key保持，mobile CSS减padding；没有直接关闭page/browser或清空selected revision路径。

旧PR reader route poll false、push mobile context-closed按父agent已有症状保留UNKNOWN；未回填旧fixture/page.request/body JSON/React时间或认定运行分支。父agent提供的当前one-only原budgetPASS未在此重读，不能替换原FAIL，也不产生产品修复理由。

下一观测仅NOT_RUN候选：existing fixture起止/page.request/bodyparse完成时间；原URLpoll false的parameter absent/parse failed/ref predicate false分类，时间+布尔/类别，不采URL/ref/payload/secret，不增请求/预算/retry。Root已要求现在不再fixturemeasurement/business重跑，未调度或instrument。

本轮0source修改/产品测试/business重跑/API/observer/listener扫描/hostprobe/model/remote写；不读progress/runtime/DB/profile/PNG/ZIP/secret/payload。仅三份私有candidate供主agent finite SAFE seal，HOME-only不是general PII保证。
