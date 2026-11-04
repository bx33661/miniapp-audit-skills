# 材料完整性与来源判断

本参考用于判断材料能够支持哪些审计结论。产物为 `evidence/material-check.json`，结构以 [material-check-output.schema.json](../assets/material-check-output.schema.json) 为准，`skill` 为 `miniapp-recon`。不在此重复入口技能的主流程。

## 确定材料类型和来源

- 区分 `wxapkg`、`wechat_cache`、`decompiled_source`、`unknown`；记录原始输入路径，解包目录另行记录，不能用解包结果覆盖来源事实。
- 从实际内容识别格式，扩展名只能作为线索。记录原包哈希、获取方式、解包工具及版本、命令、输出路径与错误；保留原包不变。
- 工具缺失、包加密或格式不支持时说明阻塞原因。不要猜测工具参数、把 ZIP 当成全部 wxapkg 格式，或将工具失败写成目标缺陷。
- 配置可能来自 `app.json`、`app-config.json` 或 bundle 内模块；先识别布局，再选检查方式。加密包与 bundle 见 [obfuscated-bundle.md](obfuscated-bundle.md)。

## 检查覆盖范围

| 检查对象 | 能支持缺失判断的依据 | 需要保留的不确定性 |
|---|---|---|
| 主包与页面 | 配置中的页面声明与实际模块、模板对应关系 | 页面逻辑可能在 `app-service.js` 的 `define` 模块中，模板可能是 HTML；缺少独立 JS/WXML 不足以证明缺失 |
| 分包 | 配置 root、页面声明、包索引、实际文件或模块 | 按需下载的分包可能未包含在缓存；说明受影响页面与业务路径 |
| 插件 | provider、版本、声明位置、交付方式与实际包 | 插件可由平台交付，未在 `miniprogram_npm` 找到不能证明插件缺失 |
| 云函数/后端 | 实际提供的服务端目录、环境与配置 | 仅有小程序包通常不包含这些材料，不能写“后端未校验” |
| 配置与源码映射 | 实际读取的配置、source map 与 bundle 对应关系 | 开发配置可能未随发布包交付；source map 可能不完整或过期 |

每项记录已检查对象、依据、未覆盖范围及其对审计结论的影响。计数只反映实际观察；未核实不能写成零、正常或不存在。

## 一致性与可读性

- AppID、版本号、编译标识、包索引、来源记录、对应文件哈希之间存在可引用的矛盾，才支持版本冲突判断。写出冲突双方及受影响路径。
- 文件 mtime 受复制、解包与构建影响，只能记录为文件属性，不能用时间差或文件数量阈值推断版本混杂。
- 解析失败、截断、模块缺失、未恢复的动态代码分别记录。短变量名、压缩行或嵌套深度本身不代表反编译失败。
- 不计算主观质量总分，不按分数启动全面重构。只有具体分支不可读且阻碍审计时，按 [code-restoration.md](code-restoration.md) 做最小辅助。

## 输出决策

- `COMPLETE`：已核对本次声明范围内的必要材料；不代表整个系统安全或所有后端材料齐全。
- `PARTIAL`：可继续部分审计，明确缺失或未核实项、受影响检查与补充材料需求。
- `CONFLICTED`：有直接材料证明来源或版本不一致；引用具体冲突，不用 mtime 推断。
- `BLOCKED`：没有足以开展目标检查的可用材料；写明真实阻塞与恢复条件。

这些是材料完整性状态，不替代发现状态 `confirmed`、`needs_validation`、`rejected`。

按 schema 填写 `scanned_at`、`input_path`、`material_type`、`completeness`、`metadata`、`main_package`、`subpackages`、`plugins`、`quality` 与 `coverage_notes`，有依据时补充 `next_actions`。各材料问题分别进入对应 `issues`；问题描述应说明证据和覆盖影响，不给缺文件机械定漏洞严重性。未核实的包状态或质量使用 `UNKNOWN` 并说明原因；未知 AppID、页面数、分包数或插件数使用 schema 允许的 `null`，未知不等于零，不填虚构 AppID 或版本。

材料问题不能直接进入最终漏洞计数。若发现真实边界失效，交由对应静态领域记录稳定 `F-001` 编号、证据和状态；只有 E2/E3 的已确认发现可有最终 `severity`。
