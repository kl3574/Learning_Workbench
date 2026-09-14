# 0007 PDF/DOCX 提取与受限执行

唯一规范为 `PRODUCT_DESIGN.md` 3.0.0 第10.1、17.3、20.3节及AC-06；本记录保存M2.3的工程选择，不增加产品需求。本记录对应M2.3实现；实际通过范围与准确提交以任务回执为准。

PDF采用锁定的pypdf 6.18.1，DOCX采用defusedxml 0.7.1解析OOXML。PDF以物理页码定位，DOCX按真实part及段落/表格节点定位，不推测页码。原始字节单独保存在blob；引用绑定原件SHA-256，候选Markdown的正文哈希独立计算。候选块提供类型化Citation列表供界面直接显示来源，不能用候选顺序猜来源。

提取结果是供核对的文本投影。PDF公式、阅读顺序、图片、表格，以及DOCX的OMML、浮动图片、复杂排版和被省略区域需要片段级诊断。扫描原件没有可提取文字时明确失败，保留原件；不自动OCR、不编造TeX、不创建假正文。全部预算按导入暂存时冻结的配置执行，超限不部分发布。

提取进程仅挂载可信运行时、解析模块和本次原件，原件与程序只读；隔离网络、限制系统调用和CPU/内存/输出/运行时间。缺少受支持的隔离能力时明确报告环境失败，不在宿主进程退回无保护的文档解析。临时探测曾证实`--as-pid-1`组合无法在父进程异常死亡时清理子孙；正式实现保留默认PID1 reaper，并验证API父进程、解析进程和沙盒的死亡链。临时探测记录不替代生产代码回归。

DOCX容器可能保存不在安全文本预览中的隐藏内容、注释、修订或嵌入部分。M2.3保守地将其原始附件保留为作者可读，安全候选预览权限单独处理；界面说明原件权限，不把原件读取403误显示为候选提取失败。外部关系不会触发下载、Office、宏或系统命令。未知内容保留在原件，并明确展示提取省略的边界；未知成员名不作为公开诊断，使用生成的成员序号。隐藏样式可能通过继承或默认规则影响正文，当前保守拒绝整件，未宣称支持完整样式级联。

失败任务没有候选时，现有固定ImportPreview契约没有可供发现的source_id。失败记录和原始SHA仍可回读，后台原件持久化另行验证。界面若提供重新选择并校验原文件的本机副本，必须明确标识其来源，不能宣称从服务器下载成功。

Python依赖由`uv.lock`固定分发哈希。本机bubblewrap与CI的Ubuntu发行包版本分别记录；CI固定官方noble的bubblewrap 0.9.0-1ubuntu0.1与libseccomp2 2.5.5-1ubuntu3.1，不修改本机AppArmor或系统策略。环境版本显示不代表隔离成功，功能与故障测试另行判定。

依赖来源：pypdf的[版本与BSD-3-Clause许可](https://pypi.org/project/pypdf/6.18.1/)、[文本提取与保真限制](https://pypdf.readthedocs.io/en/6.18.1/user/extract-text.html)；defusedxml的[发行版与PSFL许可](https://pypi.org/project/defusedxml/0.7.1/)、[XML保护参数](https://github.com/tiran/defusedxml/tree/v0.7.1)；[bubblewrap官方隔离模型](https://github.com/containers/bubblewrap)、[Ubuntu noble bubblewrap包](https://packages.ubuntu.com/noble/bubblewrap)、[libseccomp2包](https://packages.ubuntu.com/noble-updates/libseccomp2)。资料核验日期为2026-09-14；defusedxml在本项目Python3.12上的兼容性以实际测试为准。
