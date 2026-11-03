> Detailed checklist. Adapt it to the target; this is not a rigid sequence.

# Secret Scan - 凭证和敏感信息扫描

## 功能

扫描小程序源码中的：
- 硬编码凭证（API Key, Secret Key, Access Token）
- 数据库连接串
- 私钥（RSA, EC）
- 云服务密钥（阿里云、腾讯云、AWS）
- 个人信息（手机号、身份证号、邮箱）
- 微信 AppSecret（注意：小程序不应包含）

## 工具策略

1. **优先使用 Gitleaks**（如果存在）：
   ```bash
   gitleaks detect --source SOURCE_DIR --report-format json --report-path output.json --no-git
   ```

2. **备选 TruffleHog**（如果存在）：
   ```bash
   trufflehog filesystem SOURCE_DIR --json > output.json
   ```

3. **工具缺失时**：使用 ripgrep 配合规则库，或动态生成扫描脚本

## 执行流程

### 1. 检测工具

检查当前环境是否有 gitleaks 或 trufflehog：
```bash
command -v gitleaks
command -v trufflehog
```

### 2. 执行扫描

**有工具时**：
- 运行工具获取结果
- 解析 JSON 输出
- 转换为标准格式

**无工具时**：
- 读取 `../assets/rules/secret-patterns.yaml`
- 使用 ripgrep 搜索匹配
- 或动态生成 Node.js 扫描脚本

### 3. 上下文验证

对每个候选：
- 读取文件上下文（前后各 3 行）
- 检查是否在注释中
- 检查是否是测试/示例代码
- 检查是否是第三方库代码
- 排除明显的误报（如 `"your_api_key_here"`）

### 4. 脱敏处理

对确认的敏感值：
- 长密钥：保留前 4 位和后 4 位，例如 `sk_live_****xyz`
- 手机号：保留前 3 位和后 2 位，例如 `138******00`
- 身份证号：保留前 3 位和后 2 位
- 完整值记录到单独的敏感文件（不包含在报告中）

### 5. 输出结果

生成 `evidence/secrets.json`：
```json
{
  "skill": "secret-scan",
  "scanned_at": "2024-01-01T12:00:00Z",
  "source_dir": "...",
  "tool_used": "gitleaks",
  "tool_version": "8.18.0",
  "statistics": {
    "files_scanned": 150,
    "total_matches": 12,
    "after_filtering": 5
  },
  "secrets": [
    {
      "evidence_id": "EV-001",
      "type": "api_key",
      "value_masked": "sk_live_****xyz",
      "file": "utils/config.js",
      "line": 15,
      "severity": "CRITICAL",
      "confidence": "HIGH",
      "context": "const API_KEY = 'sk_live_...'",
      "recommendation": "将密钥移至环境变量或云函数配置"
    }
  ],
  "false_positives": [
    {
      "file": "node_modules/axios/README.md",
      "line": 42,
      "reason": "第三方库文档中的示例"
    }
  ]
}
```

## 扫描规则

见 `../assets/rules/secret-patterns.yaml`

## 常见模式

- **API Key**: `(api[_-]?key|apikey)[\\s]*[=:][\\s]*['\"][a-zA-Z0-9]{16,}['\"]`
- **AWS Key**: `AKIA[0-9A-Z]{16}`
- **私钥头**: `-----BEGIN (RSA |EC )?PRIVATE KEY-----`
- **数据库连接**: `(mongodb|mysql|postgres)://[^\\s]+`
- **手机号**: `1[3-9]\\d{9}`
- **身份证**: `[1-9]\\d{5}(18|19|20)\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\d|3[01])\\d{3}[\\dXx]`

## 误报过滤

- 注释中的示例：`// const key = "example"`
- 测试代码：`test/`, `__tests__/`, `*.test.js`
- 占位符：`your_key_here`, `xxx`, `placeholder`
- 第三方库：`node_modules/`, `miniprogram_npm/`
- 图片 Base64（长字符串）：排除图片扩展名或 `data:image/`

## 输出文件

- `evidence/secrets.json` - 标准输出
- `evidence/secrets-sensitive.json` - 完整值（不包含在报告中，仅供内部追溯）
