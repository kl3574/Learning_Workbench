# 评分提交回执同步修复

验证代码 `2ab067b9d832c0aa64699a9a56e879d2ab6c6ac5`；唯一规范 PRODUCT_DESIGN.md 3.0.7。仅三份 E2E 文件改变，产品后端/前端实现未改。该修复不构成 M6.2 审核/发布功能验收。

## 已建立的因果边界

原评分恢复用例在两次点击后立即查询结果。保持真实 UI/API/SQLite，暂留实际提交 POST、未注入响应：两次完整用例和一次最小用例都在提交发出前取得真实 409 / ATTEMPT_NOT_SUBMITTED，原期望200失败。只增加等待精确 attempt 的 POST 202 回执，并校验 id/status=submitted 后，最小用例及恢复完整故障/重评/刷新流程各通过。原120000ms超时、结果202轮询/200断言、旧答案/成绩断言均保留。

这证明该用例存在可控的提交同步缺口；原89b9 CI没有保存409响应体，仍不能追认其唯一原因。Tutor的5秒完成标题超时与扫描PDF导入错误单独保留。

## 命令结果

| 阶段 | 结果 | 证据 |
| --- | --- | --- |
| 01/02 原完整流程受控 RED | 各1 FAIL；实际409 | controlled/01-controlled-red、02-controlled-red |
| 03 最小 RED | 1 FAIL；实际409 | controlled/03-minimized-red |
| 04 最小 ACK GREEN | 1 PASS / 8.4s | controlled/04-minimized-green |
| 05 完整 ACK GREEN | 1 PASS / 10.4s | controlled/05-original-controlled-green |
| 最终文件初验 | 2 PASS / 13.7s | final/01-focused |
| Promise失败路径复审修复后 | 2 PASS / 14.1s | final/02-reviewed-focused |
| release显式guard后最终验证 | 2 PASS / 13.7s；零retry | final/03-guarded-focused |
| 补充窄范围strict类型检查 | exit0；仅测试及依赖 | final/04-narrow-types |

新回归暂留真实提交请求，确认提交前结果409、Attempt active且revision不变；释放后读取真实ACK、评分worker结果、原作答保留。它不伪造HTTP/数据库结果。独立静态复审关闭两项Promise失败处理问题，追加guard复审保留在review/addendum-release-v1。947份最终工程文件的字节哈希逐一匹配验证提交，见final/fixed-commit-source-binding.json。

类型检查边界：最初直接调用strict tsc，现有相对Playwright index.mjs导入无相应.d.mts，导致TS7016和连锁隐式any；另发现新增release可空TS2722，已修。尝试旧TypeScript Compiler API路径时因当前7.0.2不含该路径而在检查前失败。这两次仅有工具返回，不伪造原始日志。最终检查使用私有派生副本，仅将index.mjs模块关联换为实际安装的index.js/index.d.ts，无any shim，原runtime源不改。完整派生来源hash与命令在回执中；不是标准frontend gate或全量浏览器通过。

初验清单把新未跟踪文件的内部零SHA哨兵输出到git_blob字段；原件保留，后续改null，说明见final/untracked-metadata-note.json。零值不是Git对象。实际提交绑定另有947文件真实Git blob。

## 继续保留的失败与限制

b90双CI的两个browser各98 PASS / 1 Tutor FAIL，push integration另有954 PASS / 1 FAIL / 1环境SKIP；PDF失败原因未知。其原日志与实际checkout见相邻M6.2-pr55-b90-ci包，不以此次本地通过覆盖。此次未重跑完整Python/前端/原生套件；此前b7候选基础2251 Python PASS/1环境SKIP独立保留。

没有生产DeepSeek调用、数学批准、隔离数值成功、Content发布或人类内容审校。生产完整输入proof仍缺，sealed数值环境仍EPERM。私有运行DB、profile和secret目录未进入公开包。verify.py可逐件核公开hash及明确的原件转换。
