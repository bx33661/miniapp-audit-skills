---
name: miniapp-dynamic
description: "当在运行中的微信小程序里验证发现时使用：用 Reqable 抓包，重放与改参，测试多账号鉴权、支付和竞态条件。触发词：小程序抓包, Reqable, 重放, 越权验证, 支付测试, 动态验证."
license: MIT
compatibility: "需要 Bash 和 HTTP 客户端。Reqable 可选，但推荐作为抓包层。手机测试可能需要 Reqable 协同模式。"
metadata:
  version: "2.0"
  category: security-audit
  author: WxRay
allowed-tools: Bash Read Write mcp__reqable_capture_live_filter mcp__reqable_capture_live_get_by_id mcp__reqable_capture_live_generate_curl mcp__reqable_capture_live_set_enabled mcp__reqable_proxy_set
---

# 微信小程序动态验证

## 目的

把静态假设转化为可复现、影响最小的证据。动态工作只回答一个问题：在受控请求下，疑似失效的边界是否真的失效。

## 传感器与执行器

- **Reqable 是传感器。** 它解密和记录流量，提供请求详情和过滤。免费 MCP 接口足以完成抓包和读取。
- **Agent 是执行器。** 它归一化抓到的请求，重放，逐个改变变量，并比较响应。
- 不依赖 Reqable 的 rewrite、breakpoint 或 script。它们是可选能力；改参可以由 Agent 的 HTTP 客户端完成。

## 工作流

1. **确认范围。** 目标域名、账号、环境、速率限制和停止条件。
2. **抓取新请求。** 优先使用测试期间由小程序现场发出的请求。旧请求可能因 timestamp、nonce 或会话校验失败。
3. **归一化请求。** 记录方法、URL、请求头、请求体、Cookie 和易变字段（`sign`、`timestamp`、`nonce`、Token）。删除由客户端重算的 hop-by-hop 头。
4. **回放基线。** 先确认未修改的请求成功，再评估改参结果。
5. **单变量改参。** 每次只改对象标识、租户标识、角色、价格、数量、状态、请求头或方法之一。
6. **多账号矩阵。** 鉴权测试对比匿名、用户 A、用户 B 和特权账号对同一资源的访问。
7. **测试状态与资金流。** 检查订单、支付、退款、优惠券、积分和库存是否可由客户端控制，是否存在竞态。
8. **记录证据。** 保存状态码、响应头、响应体、时间和完整请求；脱敏密钥和个人信息。
9. **出现影响立即停止。** 如果测试暴露真实用户数据、改变资金或状态、或导致服务不稳定，停止并记录最小证据。

脚本：`python scripts/normalize_request.py --record record.json --output template.json --redact` 生成回放模板。脚本不发送请求；回放和改参由审计者控制。

## 防重放与签名

一次回放成功，不代表后续一定成功；timestamp 窗口、nonce、会话绑定或请求签名都可能变化。

- 优先现场抓取，并在观察到的窗口内回放。
- 对比失败请求与原始请求，区分时间戳、签名、会话或 IP 绑定。
- 如果 `sign` 覆盖了要测试的字段，需要静态分析或 Hook；不要暴力破解签名。
- 回放失败不等于接口安全，只能说明测试链路不完整。

## 质量门

- 改参前基线请求成功。
- 每个确认发现都有可复现的请求和响应，证据至少为 E2。
- 改参是单变量的，对比是明确的。
- 没有超出证明问题所需的最小范围访问他人数据，且数据已脱敏。
- 没有破坏性写操作、真实支付或生产状态变更。
- 签名绑定、速率限制或缺少账号等限制已记录。

## 输出

- 请求模板和回放记录。
- 基线与改参响应及差异。
- 多账号鉴权矩阵。
- 可供报告技能使用的证据记录。
- 限制和未测试路径。

## 参考

- `references/dynamic-testing.md` — 详细动态测试清单。
- `references/reqable.md` — Reqable 抓包配置和边界。
- `references/replay.md` — 请求归一化、回放和改参。
- `references/safety.md` — 授权、速率限制和停止条件。
- `assets/dynamic-test-output.schema.json` — 输出契约。

## 安全边界

- 只测试授权目标和账号。
- 默认使用只读请求。
- 不执行真实支付、退款、删除或权限变更。
- 遵守速率限制；出现错误或不稳定时停止。
- 在所有证据中脱敏 Token、个人信息和密钥。
