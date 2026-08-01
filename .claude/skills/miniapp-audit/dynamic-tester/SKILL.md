---
name: miniapp-audit-dynamic-tester
description: 动态漏洞验证 - 真实环境测试越权、注入、支付逻辑漏洞，严格安全边界（环境白名单、速率限制、审计日志）
metadata:
  version: 1.0.0
  category: security-audit
  author: WxRay
  input_format: "test_env_config=<path> findings_dir=<path> output_dir=<path> [test_mode=safe|aggressive]"
  output_schema: "../miniapp-audit-shared/schemas/dynamic-test-output.schema.json"
allowed-tools:
  - Bash
  - Read
  - Write
---

# Dynamic Tester - 动态漏洞验证

## 功能

在真实测试环境中验证静态分析发现的潜在漏洞：越权、注入、支付逻辑、会话管理。

**设计原则**：
- 验证驱动，非盲扫（只测试静态分析发现）
- 安全边界严格（环境白名单、速率限制、审计日志）
- 多用户场景模拟（管理员、普通用户、跨用户测试）

**配置模板**: `../miniapp-audit-shared/docs/test-env-template.json`  
**安全规则**: `../miniapp-audit-shared/docs/dynamic-testing-safety.md`

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

检查通过后，输出确认信息：`✓ 环境安全检查通过: {base_url}`

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

合并所有待验证发现，输出：`✓ 加载 {count} 个待验证发现`

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

输出：`✓ 完成 {count} 个测试`

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
✅ 动态测试完成
   - 已确认: {confirmed_count}
   - 很可能: {likely_count}
   - 总请求: {total_requests}
```

## 能力与限制

**能力**:
- ✅ 越权测试（水平/垂直）
- ✅ 注入测试（SQL/NoSQL）
- ✅ 支付逻辑测试
- ✅ 严格安全边界（白名单、速率限制、审计日志）

**限制**:
- ⚠️ **需要用户提供测试环境配置**：包含测试账号和白名单
- ⚠️ **safe 模式仅测试读操作**：aggressive 模式需要明确确认
- ⚠️ **不支持复杂业务逻辑**：需要人工设计测试用例
- ⚠️ **速率限制可能导致测试不完整**：大量发现时需要多次运行

## 输出文件

- `evidence/dynamic-test-results.json` - 测试结果
- `evidence/dynamic-test-audit.log` - 审计日志
