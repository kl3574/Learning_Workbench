# M3.4 公共评分历史与前端复盘限定静态审阅

本轮未发现新的可证实阻断。它只检查当前代码的数据路径与权限机制，没有新跑独立组件测试、浏览器、真实迟到响应注入或服务重启。前端 agent 明确短冻结后读取，18 个生产源文件 before/after 全部相同；哈希见 receipt.json。未改仓库文件、Git、规范或进度。

- assessment_dto.py:199–244 的 GradeHistoryItem/Entry 为严格摘要，未定义 feedback/solution/私有答案字段；274–315 核验完整题序、所有真实评分版本、最新摘要与实际结果一致，以及 202 previous 无标准答案。额外字段由核心 StrictModel 拒绝。
- grading.py:48–91 在读取前验证当前 attempt 权限、真实提交、原资格与绑定历史；释放当前参考解答前再次调用 solution_read。202 的 previous 使用 release=False。current_review_policy:32–44 由当下 workspace/题目策略重算，未直接复用冻结 mode 作为复盘权限。
- evidence.py:173–186 逐真实 grade revision 构造历史，无 Markdown；assessment_http.py:57–65 保持无 revision query 的既有路由，同时限定完整实际 JSON 响应预算，超限明确报错且 no-store，没有静默截断旧评分。
- reviewModel.ts:17–44 核验每个历史条目的精确 question ref、顺序、满分、概念 ref、冻结课程范围及当前结果对应关系；ReviewMaterialLinks.tsx 在实际导航前重新读取精确 course/lesson/block 父链，未换成 current 引用。
- AssessmentResult.tsx:23–35 使用所选真实历史版本；只有 selectedEntry.revision 等于当前 result.revision 时，才向 ReviewTutorContext 传入当前 feedback/solution。39 的 summaryOnly 隐藏选旧版时的当前逐题正文；人工复核单独明确基于最近完成的实际版本，不改选中历史。
- GradingHistory.tsx:7–16 只缓存选中版本号。缓存版本不存在时明确提示，不自动换成最新。Tutor 展示来自当前 context，Provider 发送仍 disabled；本轮不声称真实 Agent 外发链已实现。
- useGradingResult.ts:9–20、32–35、47、55–57 同时绑定 workspace/attempt/full refs、access generation 和 effect epoch；身份/代数改变时旧数据不可见，旧异步返回不能写入新 reading。api/client.ts:18–24 在权限相关请求的开始与完成广播变更；Shell.tsx:151–154 额外核对 currentReview generation。
- Shell.tsx:174 根据 workspace 当前独立测试隐藏非本人的旧 Review。useWorkspacePolicy.ts:20–25 通过本浏览器广播、focus 及 2 秒轮询观察其他配置的服务端状态。静态证据不能证明跨独立浏览器配置的瞬时同步，也不承诺抹除之前已经合法展示或下载的数据。

唯一定义来源是当前 PRODUCT_DESIGN.md §13.2 / §20.2、M3.4 与附录既有结果接口和核心模型；没有引用其它设计包或历史项目。源码快照仅为可追踪静态审阅输入，不包含数据库、浏览器 profile、运行时秘密或新截图。此目录的 public 指公共 API 投影审查；尚未作为公开证据包执行完整发布流程。
