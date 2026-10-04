创作入口增加本地 Codex 会话准备、一次批准或拒绝、受限建 thread 和当前元数据读回。刷新或同数据库 API 重启后，原 actor/key/body 可显式回放原 ACK，避免再次启动。依据现行唯一 PRODUCT_DESIGN.md v3.0.15；已实现的bootstrap仍遵循§20.16原合同；三项 capability 仍为 false、active_turn_id=null，建会话不授予模型、工具或正文访问权限。

同时实现 §6.6 的离线需求下载：只复制当前作者的主题、先修、学习目标与证明策略，下载前重核真实会话和权限，并保留未保存表单保护。用户可另行选择下载文件进入普通 Import 的未审预览；此路径不证明 Codex 来源或生成质量。修复 root UI 静态挂载拦截 API 方法的问题，构建前后都返回受控 JSON 错误，API 不读取同名静态 HTML。

实际验证按源码分别记录：

- 固定00cb完整 backend824 PASS/0 FAIL/2既有warnings、Ruff/mypy252 PASS，覆盖无静态目录和有 API 同名 HTML 的两种环境；整合后 Python runtime 字节未变。
- 固定83daf完整 Web1058 PASS/146文件；最终066与当前整合的整个 apps/web tree一致。strict与build850 PASS。
- 最终066新 browser2 PASS/0retry：实际390bytes下载、角色撤权拒绝第二次下载、dirty guard；另一次382bytes文件明确上传后，input/source/artifact SHA一致，15候选全部未审draft，未commit/publish/Codex。
- 早期196b完整 native129 PASS单独绑定。当前4ecc两次CI的完整native各130 PASS，包含最终新增Import case；不把旧129重标为130。当前组合结构80 PASS、1386工程输入前后不变。
- 本地bootstrap既有固定184完整Python3686 PASS/2物理数值环境SKIP、f321 Web1038 PASS、bd3 native128 PASS各保留原来源。固定045实际受限零模型控制HTTP201/r2 ready，1CLI、0 replay starts；三个原v2 unknown未升级或重跑。
- 旧e913 push37140042060与PR37140046223均完整FAIL：各仅backend旧路由断言失败822 PASS/1 FAIL，其他五job SUCCESS；各integration2143 PASS/2真实数值环境SKIP、native128 PASS。原完整失败及局部RED、静态P2、封包预检FAIL保留。

M6.3 / AC-21 仍在实施。本PR依赖未合并的 draft PR #55，保持draft；无merge/release/deploy。turn、多轮、通用审批、产物清单与受控回导、完整M7恢复和学术质量未验收。实际物理数值结果仍BLOCKED，发布409；真实生产Provider缺完整输入计量ProofRegistry而NOT_RUN，未把它记为key认证失败。自动审查中止的扩展安全审阅及旧诊断仍NOT_RUN，未重试。

Refs #32


实际新CI：push37165685426与pull_request37165687627均completed/success，各六job成功。12完整日志核实际checkout：push4ecc，PR merge339d5a61（tree同b97103e9，父级e287/4ecc）。每套backend824PASS、contract808PASS、integration2143PASS/2实际数值环境SKIP、Web1058PASS/146files、native130PASS；Ruff/mypy252及构建通过。

四个新数值artifact仅允许的6原JSON已核metadata/上传ID/transport digest/size/原bytes；全部BLOCKED/environment_unavailable，发布409/PUBLISH_NUMERIC_REQUIRED，Single仍draft/published_ref=null、外部模型调用0。CI成功不升级数值、生产Provider、实际Codex turn或教学质量。所有者已批准4e8d4f79 turn/逐操作审批/manifest/普通Import草稿回导补充及实施。7820199b仅补既有安全控制GET的减权基准，不新增接口或权限；原两P2静态闭合、原OPEN报告保留。合同已纳唯一v3.0.15 §20.17（SHA256 b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec）。


当前修订69029bc1只新增已批准规范、派生目录/路由归属和审阅/验收证据。固定50ec2738结构80generated/54core PASS、168合同/单元 PASS、Ruff与Web TypeScript PASS，1386工程输入前后同Git。147个操作为规范声明，运行时仍严格116个、31个未实现；未将声明当实现。旧bootstrap DTO/ACK、普通Provider、54core和0001不变。ee905c5仅本地整合原提案历史，无GitHub PR合并。

两个隔离工作树正实施新的strict DTO以及真实准备Job、状态读回与取消；尚未整合验收。新turn完整输入许可、逐操作执行和manifest回导仍待完成。每turn至多一次模型请求、工具默认禁用；工具后第二模型请求必须停止并要求新turn和新许可。没有完整ProofRegistry时保持零外发。当前修订完整CI尚未读回；4ecc十二个成功job只绑定4ecc，不重标为当前源码。
