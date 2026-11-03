# Changelog

## 2.0.1 - 2026-11-03

### Fixed

- `inventory.py` now supports raw wxapkg unpack layout (`app-config.json`, `app-service.js`, page `.html`) in addition to source layout.
- `extract_endpoints.py` no longer collapses distinct dynamic URL expressions into a single record.
- Verified both fixes against a real mini program package and the local fixture.

## 2.0.0 - 2026-11-03

### Changed

- 将 11 个按漏洞类型拆分的技能重组为 6 个按审计阶段组织的技能。
- 新增 `miniapp-threat-model`，补上业务建模、信任边界和滥用用例阶段。
- 主技能文件改为原则、决策点、质量门和参考指针，细节移入 `references/`。
- README 重写，安装方式改为 skills CLI、Claude Code 插件市场和手动复制。

### Added

- 共享审计方法论：信任边界、六问透镜、E0–E3 证据分级和覆盖矩阵。
- 质量门：材料、覆盖、证据、报告和合规。
- 确定性脚本：材料清单、端点提取、请求归一化、发现校验和覆盖校验。
- `evals/trigger-queries.csv`：24 条触发测试，包含 6 条负样本。
- GitHub Actions 验证工作流。
- Claude Code 插件市场清单。
- `CONTRIBUTING.md` 和 `SECURITY.md`。

### Fixed

- 修正 `name` 与目录不一致、`allowed-tools` 类型和 `metadata` 列表值。
- 删除不存在的 `@wechat/unveilr` 安装建议。
- 修复断链和不平衡代码围栏。
- 删除表情、营销语言和过时的共享路径引用。
- 对齐 `finding.schema.json` 与发现校验脚本。

## 1.0.0

- 初始版本：11 个按漏洞类型组织的技能。
- 材料完整性闸门、JSON Schema 和报告模板。
- 初步的 Reqable 抓包集成。
