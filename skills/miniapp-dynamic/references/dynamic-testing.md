> Detailed checklist. Adapt it to the target; this is not a rigid sequence.

# Dynamic Tester - 动态漏洞验证

## 功能

在真实测试环境中验证静态分析发现的潜在漏洞：越权、注入、支付逻辑、会话管理。

**设计原则**：
- 验证驱动，非盲扫（只测试静态分析发现）
- 安全边界严格（环境白名单、速率限制、审计日志）
- 多用户场景模拟（管理员、普通用户、跨用户测试）

**抓包层（可选）**：先用 Reqable 作为代理抓取真实小程序请求，Agent 通过 Reqable MCP 读取请求模板，再用自己的 HTTP 客户端重放/改参。Reqable 只做“传感器”，不依赖其付费的 rewrite/breakpoint/script。

**配置模板**: `../assets/test-env-template.json`
**安全规则**: `../references/safety.md`

## 前置：Reqable 代理抓包（Agent 自动化）

### 定位

- **Reqable = 传感器层**：系统代理或手机协同 VPN，负责 TLS 解密、抓包、过滤、请求详情。
- **Agent = 执行层**：通过 Reqable MCP 读取请求，归一化模板，用自己的 HTTP 客户端重放/改参/对比。
- **不依赖**：Reqable 的 rewrite / breakpoint / script（GUI 免费版 3 条/类，MCP 创建为订阅功能）；本 Skill 的改包由 Agent 完成。

### 适用场景

- 静态分析已有 endpoint，但缺少真实参数、token、签名。
- 需要复现越权/支付逻辑，手工构造请求成本高。
- 小程序绕过系统代理，需要 VPN/协同/网关才能看见流量。

### 工作流

```text
小程序（Mac 微信 / 手机微信）
  → Reqable 代理（127.0.0.1:9000 / 协同 VPN）
  → Reqable MCP（只读）
  → Agent 归一化请求模板
  → Agent HTTP 客户端重放 / 改参
  → 对比响应，写入 evidence/
```

### 免费版边界

| 能力 | 免费版 | 本 Skill 是否依赖 |
|---|---|---|
| 抓包、解密、过滤、详情、生成 curl | 可用 | 是 |
| MCP 读接口 | 可用 | 是 |
| rewrite / breakpoint / script | GUI 免费版 3 条/类；MCP 创建为订阅 | 否，改包由 Agent 完成 |
| 历史记录 | 30 天 | 重要模板由 Agent 落盘 |
| 远程设备 | 1 台 | 手机协同够单设备 |

> 没有 Reqable MCP 时，可用 GUI 导出 curl/请求，Agent 解析后重放，流程不变。

### Mac 微信

- Reqable 桌面端系统代理默认 `127.0.0.1:9000`。
- 应用名是 **“微信”**，bundle id 为 `com.tencent.flue.WeChatAppEx`；用 “WeChat” 过滤会漏。
- 小程序容器 `WeChatAppEx` 可能走系统代理，即使微信主进程走 TUN；先抓一轮，没流量再上 Proxifier。
- 过滤示例：`application.name="微信"` 或 `application.id="com.tencent.flue.WeChatAppEx"`。

### 手机微信

- 桌面端出二维码 → 手机 Reqable 选协同 → 扫码 → 装证书 → 开调试（VPN）。
- 免费版 1 台远程设备；iOS 无应用归因，按 host/UA 过滤；Android 可按应用过滤。
- 兜底：手机热点 + Linux 网关 mitmproxy 透明代理；Reqable 继续做桌面分析。

### 请求模板归一化

`capture_live_get_by_id` 取到记录后，转成以下结构再重放：

```json
{
  "source": "reqable",
  "application": {"name": "微信", "id": "com.tencent.flue.WeChatAppEx"},
  "captured_at": "2026-11-03T21:21:24+08:00",
  "request": {
    "method": "POST",
    "url": "https://target.example/app/getMyList",
    "headers": {"User-Agent": "...", "Referer": "https://servicewechat.com/..."},
    "body": "sign=...&timestamp=...&userCode=..."
  },
  "volatile_fields": ["sign", "timestamp"],
  "notes": "去掉 Host/Content-Length/Connection/Accept-Encoding，由 HTTP 客户端重算"
}
```

重放时保留 UA、Referer、`xweb_xhr` 等小程序特征头；去掉 hop-by-hop 头。请求体是 form 时用 `parse_qsl` 保序，不要直接字符串拼接。

### 防重放（实测坑）

- 原样回放旧请求可能返回 `{"msg":"异常用户004！","status":0}`；补 `JSESSIONID` 也不一定通过。
- 优先让小程序现场发新请求，Agent 在 timestamp 窗口内立即重放。
- 仍失败则说明 `sign` 绑定了 session/一次性 token：转静态分析 wxapkg 或 Frida hook；Reqable 订阅不解决这个问题。
- 只做只读、最小化验证；不要在未授权目标上遍历他人 `userCode`/学号。

### 安全与清理

- 只测授权目标；支付/写操作仅限测试环境。
- 抓包得到的 host 也必须通过第 2 步的环境白名单校验；不在白名单的目标只做只读观察，不重放/改参。
- 抓到的个人信息脱敏；测试结束关闭系统代理、停止抓包、清理 Reqable 历史。

## 执行流程

### 1. 参数解析与验证

解析输入参数，提取以下必需字段:
- `test_env_config`: 测试环境配置文件路径
- `findings_dir`: 静态分析发现目录路径
- `output_dir`: 测试结果输出目录路径
- `test_mode`: 测试模式（默认 `safe`，可选 `aggressive`）

如果缺少必需参数，立即终止并报告错误信息。

### 2. 环境安全检查

读取测试环境配置文件，执行以下安全检查:

**CRITICAL 级别检查（任何失败必须终止）**:
- 检测 `base_url` 是否包含生产环境关键字（`prod`, `production`, `api.example.com`, `www.`）
- 验证目标域名是否在 `whitelist.domains` 白名单内
- 提取 `base_url` 的 hostname，检查是否匹配白名单中任一域名

**HIGH 级别检查（警告但可继续）**:
- 确认 `accounts` 至少包含 2 个测试账号（越权测试需要多用户）

如果存在 CRITICAL 级别问题，终止执行并输出完整的安全检查结果。

检查通过后，输出确认信息：` 环境安全检查通过: {base_url}`

### 3. 加载待验证发现

依次尝试读取以下文件:
- `{findings_dir}/authz-findings.json`
- `{findings_dir}/payment-findings.json`
- `{findings_dir}/dataflow-analysis.json`

对每个文件:
- 如果文件不存在，输出警告并跳过
- 解析 JSON 内容，提取 `findings` 或 `vulnerabilities` 数组
- 筛选需要验证的发现（满足以下条件之一）:
  - `severity` 为 `CRITICAL` 或 `HIGH`
  - `status` 为 `server_confirmation_needed`

合并所有待验证发现，输出：` 加载 {count} 个待验证发现`

**3.1 获取真实请求模板（可选）**

如果 finding 缺少真实参数、token 或签名，先用 Reqable 抓取同端点的真实请求：

1. 调用 `mcp__reqable_capture_live_set_enabled` 确保抓包开启；
2. 让用户在小程序中触发对应页面；
3. 调用 `mcp__reqable_capture_live_filter`，按 `application` / `host` 过滤；
4. 调用 `mcp__reqable_capture_live_get_by_id` 取完整请求，归一化为请求模板；
5. 后续测试用模板重放，不依赖 Reqable rewrite。

### 4. 执行动态测试

初始化测试状态:
- 测试结果列表
- 审计日志列表
- 请求计数器（初始值 0）
- 最大请求限制（从 `test_env.rate_limit.max_total_requests` 读取，默认 1000）

遍历每个待验证发现:

**4.1 速率限制检查**

如果请求计数器已达到最大限制，输出警告并停止测试循环。

**4.2 测试类型路由**

根据发现的类型分派到对应测试方法:
- `category === 'authz'` 或 `type === 'privilege_escalation'` → 越权测试
- `vulnerability === 'SQL Injection'` 或 `NoSQL Injection` → 注入测试
- `type === 'payment_logic'` → 支付逻辑测试
- 其他类型 → 标记为 SKIPPED

**4.3 越权测试流程**

1. 从 `test_env.accounts` 中查找两个测试用户（role 为 `user`，name 包含 'a' 和 'b'）
2. 如果账号不足，返回 SKIPPED 状态
3. 提取 API 端点（从 `finding.api_endpoint` 或 `finding.locations[0].file`）
4. 检查端点是否在 `test_env.blacklist.paths` 黑名单内，如果是则跳过
5. 构造测试 URL：`{base_url}{endpoint}?order_id={test_resources.user_b_order_id}`
6. 使用用户A的 token 发送 GET 请求（使用 curl）
7. 解析响应状态码和响应体
8. 判定逻辑:
   - 如果状态码 200 且响应体包含用户B的 `user_id` 或 `success: true` → CONFIRMED
   - 否则 → FALSE_POSITIVE
9. 记录测试结果（包含证据、复现步骤、请求数量）

**4.4 注入测试流程**

1. 如果 `test_mode === 'safe'`，返回 SKIPPED（safe 模式不执行注入 Payload）
2. 提取 API 端点和参数名称（从 `finding.sink.file` 或 `finding.source.variable`）
3. 准备注入 Payload 列表：
   - `1' OR '1'='1`
   - `1; SELECT * FROM users--`
   - `1 UNION SELECT NULL--`
4. 对每个 Payload:
   - 构造测试 URL：`{base_url}{endpoint}?{param}={encoded_payload}`
   - 发送 GET 请求
   - 检查响应体是否包含 SQL 错误关键字（`SQL`, `syntax error`）或状态码 500
   - 如果匹配 → 返回 CONFIRMED，记录证据
5. 如果所有 Payload 均未触发 → 返回 FALSE_POSITIVE

**4.5 支付逻辑测试流程**

1. 如果 `test_mode === 'safe'`，返回 SKIPPED
2. 提取 API 端点（从 `finding.api_endpoint` 或默认 `/order/create`）
3. 构造负数价格 Payload：`{"product_id": "123", "quantity": 1, "price": -0.01}`
4. 使用测试账号的 token 发送 POST 请求
5. 判定逻辑:
   - 如果状态码 200/201 且响应体包含 `success: true` 或 `order_id` → CONFIRMED
   - 否则 → FALSE_POSITIVE
6. 记录测试结果（包含 Payload、响应状态码、复现步骤）

**4.6 记录与限速**

对每个测试结果:
- 添加到测试结果列表
- 记录审计日志（时间戳、finding_id、测试类型、结果、请求数）
- 更新请求计数器
- 根据 `test_env.rate_limit.max_requests_per_second` 计算延迟（默认 200ms），暂停执行

输出：` 完成 {count} 个测试`

### 5. 生成测试报告

统计测试结果:
- 已确认漏洞（status === 'CONFIRMED'）
- 很可能存在（status === 'LIKELY'）
- 误报（status === 'FALSE_POSITIVE'）
- 跳过（status === 'SKIPPED'）

构造输出 JSON 对象，包含:
- `skill`: `'dynamic-tester'`
- `tested_at`: 当前时间戳（ISO 8601 格式）
- `test_env`: 测试环境的 `base_url`
- `test_mode`: 使用的测试模式
- `summary`: 测试统计摘要
- `confirmed_vulnerabilities`: 已确认漏洞的详细列表（包含 finding_id、vulnerability、severity、test_type、evidence、reproduction_steps）
- `all_tests`: 所有测试结果的完整列表
- `audit_log`: 审计日志

写入以下输出文件:
- `{output_dir}/evidence/dynamic-test-results.json` - 完整测试报告（JSON 格式，缩进 2 空格）
- `{output_dir}/evidence/dynamic-test-audit.log` - 审计日志（每行一个 JSON 对象）

输出最终摘要:
```
 动态测试完成
   - 已确认: {confirmed_count}
   - 很可能: {likely_count}
   - 总请求: {total_requests}
```

## 能力与限制

**能力**:
- 越权测试（水平/垂直）
- 注入测试（SQL/NoSQL）
- 支付逻辑测试
- 严格安全边界（白名单、速率限制、审计日志）
- Reqable 代理抓包：获取真实请求模板（免费 MCP 只读）

**限制**:
- **需要用户提供测试环境配置**：包含测试账号和白名单
- **safe 模式仅测试读操作**：aggressive 模式需要明确确认
- **不支持复杂业务逻辑**：需要人工设计测试用例
- **速率限制可能导致测试不完整**：大量发现时需要多次运行
- **Reqable 的 rewrite/breakpoint/script**：GUI 免费版 3 条/类，MCP 创建为订阅功能；本 Skill 不依赖，改包由 Agent 完成
- **服务端可能有防重放/签名校验**：旧请求重放可能返回“异常用户”，需现场抓新请求或分析 sign

## 输出文件

- `evidence/dynamic-test-results.json` - 测试结果
- `evidence/dynamic-test-audit.log` - 审计日志
- `evidence/reqable-capture.json` - 归一化请求模板（可选，脱敏；不改变 dynamic-test-results.json 的 schema）
- `evidence/replay-results.json` - Agent 重放/改参结果（可选）
