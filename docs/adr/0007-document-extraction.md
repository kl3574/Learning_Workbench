# 0007 PDF/DOCX 提取与受限执行

唯一规范为 `PRODUCT_DESIGN.md` 3.0.0 第10.1、17.3、20.3节及AC-06；本记录保存M2.3的工程选择，不增加产品需求。本记录对应M2.3实现；实际通过范围与准确提交以任务回执为准。

PDF采用锁定的pypdf 6.18.1，DOCX采用defusedxml 0.7.1解析OOXML。PDF以物理页码定位，DOCX按真实part及段落/表格节点定位，不推测页码。原始字节单独保存在blob；引用绑定原件SHA-256，候选Markdown的正文哈希独立计算。候选块提供类型化Citation列表供界面直接显示来源，不能用候选顺序猜来源。

提取结果是供核对的文本投影。PDF公式、阅读顺序、图片、表格，以及DOCX的OMML、浮动图片、复杂排版和被省略区域需要片段级诊断。扫描原件没有可提取文字时明确失败，保留原件；不自动OCR、不编造TeX、不创建假正文。全部预算按导入暂存时冻结的配置执行，超限不部分发布。

提取进程仅挂载可信运行时、解析模块和本次原件，原件与程序只读；隔离网络、限制系统调用和CPU/内存/输出/运行时间。缺少受支持的隔离能力时明确报告环境失败，不在宿主进程退回无保护的文档解析。临时探测曾证实`--as-pid-1`组合无法在父进程异常死亡时清理子孙；正式实现保留默认PID1 reaper，并验证API父进程、解析进程和沙盒的死亡链。临时探测记录不替代生产代码回归。

DOCX容器可能保存不在安全文本预览中的隐藏内容、注释、修订或嵌入部分。M2.3保守地将其原始附件保留为作者可读，安全候选预览权限单独处理；界面说明原件权限，不把原件读取403误显示为候选提取失败。外部关系不会触发下载、Office、宏或系统命令。未知内容保留在原件，并明确展示提取省略的边界；未知成员名不作为公开诊断，使用生成的成员序号。隐藏样式可能通过继承或默认规则影响正文，当前保守拒绝整件，未宣称支持完整样式级联。

失败任务没有候选时，现有固定ImportPreview契约没有可供发现的source_id。失败记录和原始SHA仍可回读，后台原件持久化另行验证。界面若提供重新选择并校验原文件的本机副本，必须明确标识其来源，不能宣称从服务器下载成功。

Python依赖由`uv.lock`固定分发哈希。需要文档隔离的CI作业使用官方Ubuntu26.04镜像及固定发行包：bubblewrap0.11.1-1ubuntu0.3、apparmor/libapparmor1 5.0.2-0ubuntu1~26.04.1、libseccomp2 2.6.0-2ubuntu5，使用其已有的bwrap用户命名空间配置。24.04实际探针曾报RTM_NEWADDR权限错误；相同二进制的不同执行路径对照排除了仅凭版本推断原因。26.04独立探针及64项真实安全/提取测试通过后才迁移完整作业，不关闭全局AppArmor限制，不削弱namespace/cap-drop。完整CI结果以任务回执为准。

依赖来源：pypdf的[版本与BSD-3-Clause许可](https://pypi.org/project/pypdf/6.18.1/)、[文本提取与保真限制](https://pypdf.readthedocs.io/en/6.18.1/user/extract-text.html)；defusedxml的[发行版与PSFL许可](https://pypi.org/project/defusedxml/0.7.1/)、[XML保护参数](https://github.com/tiran/defusedxml/tree/v0.7.1)；[bubblewrap官方隔离模型](https://github.com/containers/bubblewrap)、[Ubuntu发行包目录](https://packages.ubuntu.com/resolute/bubblewrap)、[官方runner镜像](https://github.com/actions/runner-images)。资料核验日期为2026-09-14；defusedxml在本项目Python3.12上的兼容性以实际测试为准。

2026-09-28，push 36365995687 / pull_request 36365997123 的六个实际作业在旧 bubblewrap 精确版本安装阶段退出100，后续后端、集成和浏览器测试未启动。当前官方签名 APT 索引仅提供上游基线与0.11.1-1ubuntu0.3；独立空状态解析复现旧 pin 失败，仅改该 pin 后四项精确依赖解析通过。InRelease、Packages、Sources 与下载包的签名/哈希链均已核验。本机实际 bwrap、AppArmor parser/profile 及两库字节与认证发行包一致；已有文档运行探针通过，原有安全/提取/数值运行器测试70通过、1跳过。跳过的是封装数值运行器被 AppArmor 拒绝启动，未完成算术执行。原始失败和本地证据保存在任务回执中；更新后的完整远程 CI 仍须按实际提交另行回读。

本次包选择保留已知安全边界：[USN-8779-2](https://ubuntu.com/security/notices/USN-8779-2) 说明0.3为恢复 Flatpak 兼容性撤回了0.2的 symlink 修复，[Ubuntu CVE-2026-87766](https://ubuntu.com/security/CVE-2026-87766) 仍将26.04标为 Vulnerable。认证源码补丁列表保留 CVE-2026-41163；0.1也未含后来的87766修复。[上游说明](https://github.com/containers/bubblewrap/security/advisories/GHSA-pxhw-h44j-8pfx) 将触发条件限定于在攻击者控制的文件树中创建沙箱路径。当前文档入口仅向固定位置挂载密封原件字节，目录来自可信运行时；数值入口用可信闭包的密封文件与固定逻辑路径，没有用户提供的挂载根或目标路径。此静态适用性判断与实际隔离检查仅覆盖当前两个入口，不能宣称第三方漏洞已修复；未来引入不可信目录挂载或可变目标路径时必须重新评估，并继续跟踪官方完整修复。核验日期2026-09-28。
