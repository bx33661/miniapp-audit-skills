---
name: miniapp-report
description: "整理微信小程序审计证据：归一化发现、确认门、风险决策、中文报告与复测。"
license: MIT
compatibility: "读取 JSON 证据，输出 Markdown 和 JSON。"
metadata:
  version: "2.0"
  category: security-audit
  author: WxRay
allowed-tools: Read Write Bash
---

# 微信小程序审计报告

## 目的

把可追溯证据整理为修复决策，明确已确认、待验证、已排除以及覆盖未知。可直接接收运行测试或已有证据，不要求材料盘点、解包和静态阶段先完成。

## 输入与字段映射

按本次实际执行的阶段读取 evidence 目录中的可用输入；缺少不相关阶段产物不阻塞报告，未执行阶段保留覆盖说明。

| 文件 | 读取内容 | 处理 |
| --- | --- | --- |
| `material-check.json` | 材料检查记录 | 材料可用性与限制，不能作为漏洞计数 |
| `attack-surface.json` | 攻击面记录 | 资产、入口与覆盖上下文 |
| `secret-scan.json` | `secrets[]` | 原始候选；脱敏后整理为待验证发现，不凭匹配确认泄露影响 |
| `authz-findings.json` | `findings[]` | 直接使用统一 finding 字段 |
| `payment-findings.json` | `findings[]` | 直接使用统一 finding 字段 |
| `dataflow-analysis.json` | `findings[]` | 直接使用统一 finding 字段，保留 `dataflow` |
| `privacy-compliance.json` | `sections.<section>.issues[]` | 直接使用统一 finding 字段；检查项通过不代表整个领域安全 |
| `dynamic-test-results.json` | `requests[]`、`findings[]`、`limitations` | 请求清单用于捕获/重放覆盖，按 finding_id 关联安全实验，不把成功重放当漏洞 |

状态仅为 `confirmed`、`needs_validation`、`rejected`，不设默认值。领域统一记录缺少状态或关键字段时记录输入错误，不猜测状态。原始 secret 候选首次归一化时分配稳定 `F-001` 编号并保存来源映射；已有编号不得重建。证据采用 `EV-001` 编号。

动态结果仅有 `CONFIRMED`、`INCONCLUSIVE`、`BLOCKED`、`FALSE_POSITIVE`，实验结果不等于最终发现状态或严重性。成功实验仍须满足确认门；受阻或不确定应记录缺失事实；排除必须给出针对原主张的反证理由。

可从 blackboard 导出的候选和证据关系作为输入；最终 findings/evidence 仍按本技能 schema 归一化，黑板 confidence 不是报告状态。

## 工作流

1. 按 `references/report-builder.md` 加载输入，区分缺失、解析失败、结构无效和成功读取的空数组。
2. 根据根因、失效边界和受影响资产去重，保留来源、证据和稳定编号。
3. 按 `assets/finding.schema.json`、`assets/evidence.schema.json` 校验单条记录；核对跨文件证据引用和事实。
4. 确认必须有具体 asset、E2/E3、severity 及 severity_reason、非空证据引用、根因、前置条件、复现、影响、修复、验证方法、预期/实际与复测标准。未满足时补证或明确降为待验证并去掉 severity，不能制造内容以过门。
5. 仅对 confirmed 分配严重性，按 `../miniapp-audit/references/severity.md` 解释已证明的影响及条件；候选和排除项仅可有 priority。
6. 写入数组形式的 `findings.json`、`evidence.json` 和简洁 `report.md`，使用 `assets/report-template.md`。按需要附清单，不强制输出无关专题或额外大文档。

## 证据与风险

E0 是线索，E1 是有根据的待验证路径，E2 是可复现或可独立核验的直接证据证明具体边界失效，E3 是授权测试数据上进一步证实影响范围。证据强度不由静态或动态手段决定；E2 足够后不追求更大影响。E2/E3 本身不自动决定状态。

最终风险计数只包含 confirmed 的 severity。待验证与排除项分别列数量、缺失事实或理由，不推高总体风险。总体判断需说明已证实影响、可达条件、现有控制和覆盖限制，不按最高标签自动计算。无确认发现时写“本次范围内未形成已确认发现”，并列未知，不能据此宣告安全。

## 交付与校验

`findings.json` 与 `evidence.json` 顶层均为数组；两个 schema 分别描述单条元素。仓库根目录的统一校验命令为 `python3 scripts/validate_outputs.py --evidence-dir <dir>`，由集成阶段执行。schema 不能代替证据内容审查、引用存在性和跨记录唯一性检查。

证据须脱敏，保留可定位来源、时间和实际摘录。HTTP 证据无需虚构源码行号。记录受限原始证据的保留与删除要求，不向授权范围外发布利用细节。

## 参考

- `references/report-builder.md`：归一化、去重、确认门和决策。
- `references/evidence-standard.md`：证据等级与追溯。
- `assets/report-template.md`：中文填写模板。
- `assets/finding.schema.json`、`assets/evidence.schema.json`：单条记录契约。
