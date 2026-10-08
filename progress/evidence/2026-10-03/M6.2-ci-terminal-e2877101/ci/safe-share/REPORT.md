# e287 CI 终态只读归档

源码 head `e2877101d9c2bda0f793a460db63ef496350c6b4`；观察时间2026-10-03。两个既有run均run_attempt=1。未重跑、取消、修改工作流或推送/修改Issue。

- push run 37087115486：completed/success，6/6 job success；https://github.com/kl3574/Learning_Workbench/actions/runs/37087115486。
  - browser：841 modules transformed.；Running 126 tests using 1 worker；126 passed (30.9m)
  - spec-contracts：749 passed, 2 warnings in 225.69s (0:03:45)
  - frontend：Test Files  139 passed (139)；Tests  961 passed (961)；841 modules transformed.
  - integration：2093 passed, 2 skipped, 2 warnings in 1875.83s (0:31:15)
  - backend：Success: no issues found in 236 source files；751 passed, 2 warnings in 36.68s
  - security-publication：PASS: scanned 16630 staged/tracked files
- pull_request run 37087119424：completed/success，6/6 job success；https://github.com/kl3574/Learning_Workbench/actions/runs/37087119424。
  - frontend：Test Files  139 passed (139)；Tests  961 passed (961)；841 modules transformed.
  - backend：Success: no issues found in 236 source files；751 passed, 2 warnings in 40.16s
  - integration：2093 passed, 2 skipped, 2 warnings in 2942.65s (0:49:02)
  - security-publication：PASS: scanned 16630 staged/tracked files
  - browser：841 modules transformed.；Running 126 tests using 1 worker；126 passed (29.9m)
  - spec-contracts：749 passed, 2 warnings in 341.57s (0:05:41)

12个job都从其原始日志单独提取实际checkout：push为e2877101d9c2bda0f793a460db63ef496350c6b4；PR为merge commit 7b8c3c96f4c08c7f1554bf9ceb6829d466ff39af。两个Git commit API的tree均为ec42efa7d5e16f994d72dd4491a2f0bb1c67bf27。SOURCE_BINDING.json另核6个明确列出的本地Git blob；没有把该抽样称为逐文件下载整个源码树。原watch的6个push日志与本次新下载逐字相同。

每个integration job均保留两个真实数值环境skip，精确测试与原因见CI_TERMINAL.json。不同Python job测试范围有重叠，不把749/751/2093相加称完整Python套件。

四个GitHub ZIP均与API digest匹配，包含六个JSON。四个独立Single/Restore数值结果全为environment_unavailable / BLOCKED / exit1 / 空assertions / null output，numeric job本身failed；随后的真实发布请求全为HTTP409 PUBLISH_NUMERIC_REQUIRED，外部模型调用0。另两个Restore JSON是同次观察的重复响应，内容与主payload一致，不能计作额外执行。结果自身SHA、operation和job绑定均重新核验。Browser126 PASS只说明对应软件流程通过，不构成物理数值PASS。

原watch目录30件已逐字复制到inherited-watch并绑定INHERITED_WATCH.json；原首次读取失败及resume五次读取失败全部保留。后续API读取失败导致collector退出，只代表观察UNKNOWN，不能算CI失败。本次远端API成功读回两run终态，因此补齐观察，不改写旧记录。原stderr、API原包、12raw logs和4ZIP均私有，不打印/公开其认证头或原始内容。

只允许SAFE_SHARE.json的13项候选公开：安全终态/数值/来源/失败分类摘要、原件SHA目录，以及6个明确JSON。JSON唯一允许内容转换是精确$HOME→$HOME、$RUNNER_HOME→$RUNNER_HOME；原SHA保留。派生摘要只白名单选择字段，不冒称原始日志逐字转录。RAW_MANIFEST列出的路径不是允许公开其原始payload；所有未列候选包括API、stderr、rawlog、ZIP、collector和watch脚本均排除。
