# Changelog

## Unreleased

### Changed

- 支持从运行流量、代码或已有证据独立开始；解包按需进行，补充小程序开发与运行结构模型。
- 动态技能增加独立代理抓包、实际请求重放与流量发现入口，分别记录捕获、重放、安全对照和阻塞。
- 统一发现状态、证据等级、稳定 ID 和领域输出；移除旧状态/字段别名、默认确认、候选最终严重性和 JS 报告模板。
- 删除伪数据流算法、关键词风险评分、质量分数触发全面还原、非微信域名即第三方共享等机械规则。
- 材料盘点核对分包页面与插件，未知元数据用 null；端点提取保留顶层属性、动态表达式、全部调用位置和实际协议。

### Added

- 离线输出契约与证据引用校验器、开发依赖和行为回归，接入 CI。
- 八个有官方来源的平台案例，覆盖自建/云身份、多通道会话、页面与构建、分包、原生富文本和开发者工具权限。
- 显式请求计划与真实 HTTP/HTTPS 执行器，支持 HTTP 转发/CONNECT、受信 CA、账号 Cookie 隔离、会话失效，以及规定格式的 HMAC-SHA256/AES-GCM。
- 独占证据目录、真实尝试回执、字节摘要与 --verify-artifacts 制品完整性检查；收到状态后正文截断仍保留实际状态并标记失败。
- 本地服务端独立观测的 21 组网络/业务场景、长驻目标和独立 Agent 评测入口。

新输出契约不兼容旧状态与字段别名，已有产物需要按当前 schema 重新整理。

### Validation

- 本地通过六个技能的严格检查、链接检查与 53 项行为回归，回归会校验实际场景制品。
- 21 组 native 场景通过；20 个生成证据的 bundle 通过 schema、引用与 SHA256 检查，另一组在计划超预算时于发送前拒绝。
- 三个独立 Agent 分别识别归属拒绝、跨账号返回测试记录和会话受阻；8 次实际请求及 1 个未发送探测与服务端观察一致，三个 bundle 通过严格校验。
- 上述结果仅证明本地夹具与所执行任务，不是总体准确率；未进行真实微信客户端、Reqable、Nightly 或 wechatide 现场兼容性评测。


## 2.0.2 - 2026-11-03

### Changed

- Reduced audit scripts to `inventory.py` and `extract_endpoints.py`.
- Removed `normalize_request.py`, `check_findings.py` and `check_coverage.py`; normalization, redaction and quality checks are instruction-led.
- Rewrote `dynamic-testing.md` as a hypothesis matrix with `CONFIRMED / INCONCLUSIVE / BLOCKED / FALSE_POSITIVE`.
- Merged severity guidance into `miniapp-audit/references/severity.md` and aligned terminology on `INFO`.
- Decoupled capture wording from a single vendor; removed `proxy_set` from allowed tools.
- Removed edition-specific pricing and history claims from the Reqable reference.

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
