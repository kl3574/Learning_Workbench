# Review 延迟路由生命周期诊断与两行测试修复

原完整 `make test-e2e` 在源码412实际132 PASS、1 FAIL，24.1分钟。唯一失败是 `tests/e2e/review.spec.ts:76`，第80行受控延迟回调 `route.fulfill` 报 `Route is already handled!`。原失败、所有回执和五项实际生成输出差异永久保留；没有reset或复制回原工作树。

失败时浏览器快照已经进入独立测试限制页，未见完整评分历史或学科复盘上下文。这仅是当时快照，不能证明回调或全部断言完成。原源码在独立隔离目录只执行原失败用例，实际1 PASS，全部1512输入不变。原完整运行没有回调/清理次序记录，唯一原因仍是UNKNOWN，不归因于旧CI。

静态loopback HTTP与真实Chrome的有界机制观测说明：先移除待处理路由再fulfill可产生同样的错误；fulfill完成后移除则无错误。这两个机制用例不计作产品验收。已安装同版本Playwright源码确认默认unroute不等待active callback，移除当前handler可能继续该route；没有修改依赖。

修复提交d69的parent是最终GenericApproval43，只有原Review测试文件两行2+/2-：release后等待 `page.unrouteAll({behavior:'wait'})` 完成，再做原隐藏断言；finally先release保证gate释放，再wait后close。没有ignoreErrors、生产/规范/配置修改，也没有改变原locators、权限断言、30秒测试预算、retry或两项原Review业务用例。

修复后实际原生选择器 `review.spec.ts` 匹配原Review2项及draft-review1项，原件准确是3 PASS、38.4秒测试/38.866秒wrapper，1522输入完全不变。现行Webstrict与diffcheck通过。两次额外独立e2e类型命令失败原件保留：第一缺app node typeRoots，第二暴露原相对.mjs imports声明映射。第三仅私有精确官方声明桥的有界Review strict通过；不是规范必需门禁或全e2e覆盖，不引入canonical声明/config修改。

这些结果没有关闭原完整FAIL，也没有完成整个M6.3/AC21、实际Codex CLI/生产Provider或物理工具验收。本诊断模型请求0。最终组合完整原生测试由root独立运行。

公开候选仅包含明确文档、源差异、完整Git映射、命令、回执、限定原失败摘录与新有界日志。原完整native.log、数据库、profile、浏览器runtime和其他产物未纳入。每份候选仅以精确`$HOME`到`$HOME`路径替换，保留原/候选哈希；scanner只是有界补充，仍须root独立读回。
