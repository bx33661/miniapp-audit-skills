---
name: miniapp-audit-authz-analyzer
description: 权限控制缺陷分析 - 识别越权风险（水平/垂直）、权限绕过、角色混淆，生成测试用例
metadata:
  version: 1.0.0
  category: security-audit
  author: WxRay
  input_format: "source_dir=<path> output_dir=<path> attack_surface=<path>"
  output_schema: "../miniapp-audit-shared/schemas/authz-findings.schema.json"
allowed-tools:
  - Bash
  - Read
  - Write
---

# Authz Analyzer - 鉴权和越权分析

## 功能

深度分析小程序的鉴权机制和越权风险：
- 认证流程分析
- 身份识别和分类
- 资源清单构建
- 身份-资源权限矩阵
- 越权风险识别
- 测试用例生成

## 执行流程

### 1. 认证机制分析

#### 1.1 识别登录流程

搜索微信登录 API 调用：`wx.login`, `wx.getUserProfile`, `wx.getUserInfo`

提取关键信息：
- 登录入口（页面路径、函数名）
- code 换 token 的后端 API
- token 存储位置（`setStorageSync('token')` / `globalData.token`）
- token 刷新机制

#### 1.2 Token 管理分析

搜索 token 读写操作：`setStorageSync`, `getStorageSync`, `globalData.token`

检查项：
- Token 存储方式的安全性
- Token 过期处理逻辑
- Token 刷新机制是否存在
- 登出时是否清理 token

搜索请求头中 token 的使用：`Authorization`, `Bearer`, `token` header

### 2. 身份识别

#### 2.1 提取身份角色

执行正则搜索：`rg "(role|userType|type|level|permission|isAdmin|isMember)" --type js`

识别并分类身份类型：
- **匿名用户**：未登录状态
- **普通用户**：基础已登录用户
- **VIP/会员**：付费特权用户
- **商户/员工**：业务特定角色
- **管理员**：高权限管理角色
- **租户**：多租户系统的租户身份

#### 2.2 确定身份信息来源

检查身份数据来源：
- 服务端返回（登录响应）
- 本地存储（storage）
- 全局变量（globalData）
- 客户端硬编码（标记为高危）

### 3. 资源清单构建

从 attack-surface 数据和代码中提取资源，按类型分类：

**用户私有资源**：个人信息、订单、地址、收藏夹等（需归属验证）
**共享资源**：商品列表、文章、评论等（公开或半公开）
**敏感资源**：支付记录、优惠券、积分余额等（需强认证）
**管理资源**：用户管理、统计报表、系统配置等（需角色权限）

记录每个资源的：
- API 路径
- HTTP 方法
- 敏感参数（userId, orderId, id 等）

### 4. 身份-资源矩阵构建

构建权限期望矩阵：

| 资源 \ 身份 | 匿名 | 用户A | 用户B | VIP | 管理员 |
|------------|------|-------|-------|-----|--------|
| 用户A信息   | ❌   | ✅    | ❓    | ❓  | ✅     |
| 用户A订单   | ❌   | ✅    | ❓    | ❓  | ✅     |
| 商品列表    | ✅   | ✅    | ✅    | ✅  | ✅     |
| VIP内容    | ❌   | ❌    | ❌    | ✅  | ✅     |
| 用户管理    | ❌   | ❌    | ❌    | ❌  | ✅     |

标记：✅ 预期允许，❌ 预期拒绝，❓ 需验证（可能越权）

### 5. 越权风险识别

#### 5.1 水平越权（Horizontal Privilege Escalation）

检测模式：同级别用户访问其他用户资源

搜索危险参数：API 请求中包含 `userId`, `orderId`, `id`, `uid` 等身份标识参数

识别风险特征：
- 参数值来自客户端输入（页面参数 `options.userId`、用户输入）
- 参数直接传递给 API，未见服务端归属验证
- 缺少当前用户身份验证逻辑

标记为 HIGH 风险：资源为订单、支付、个人信息等敏感数据

#### 5.2 垂直越权（Vertical Privilege Escalation）

检测模式：普通用户访问高权限接口

搜索管理接口：URL 包含 `/admin/`, `/manager/`, `/system/`, `/backend/`

识别风险特征：
- 普通用户代码中调用了管理接口
- 客户端代码可指定 `userType`, `role` 等角色参数
- 缺少客户端的角色检查逻辑
- 管理接口未见明确的权限验证

检查请求封装函数是否统一添加了角色验证

#### 5.3 认证绕过

检测模式：敏感接口缺少认证

检查请求是否缺少 `Authorization` header

检查统一请求封装函数是否遗漏了 token 添加逻辑

搜索直接调用 `wx.request` 而未使用统一封装的情况

#### 5.4 客户端角色信任

检测模式：角色信息由客户端控制

搜索请求中传递的角色参数：`role`, `isAdmin`, `isVip`, `userType`

检查这些参数是否：
- 从客户端传入而非服务端返回
- 可被用户篡改
- 用于权限判断

标记为 CRITICAL：服务端可能信任客户端角色声明

### 6. 数据流深度追踪

对高风险 API，使用 dataflow-tracer 追踪参数来源：

追踪敏感参数（userId, orderId）从源头到 API 的完整数据流
检查路径中是否存在验证 guard（if 条件、函数调用）
确认是否有服务端验证逻辑

若数据流无验证 guard，提升风险置信度为 HIGH

### 7. 生成测试用例

为每个越权风险生成可执行测试用例，包含：
- `test_case_id`：唯一标识
- `type`：越权类型（horizontal/vertical/auth_bypass）
- `description`：测试描述
- `prerequisites`：前置条件（测试账号、测试数据）
- `steps`：操作步骤（登录、获取资源ID、发起越权请求）
- `expected`：预期响应（403/401 拒绝访问）
- `vulnerable_if`：漏洞判定条件（200 返回其他用户数据）

每个步骤包含：
- HTTP 方法和 URL
- Headers（含 token）
- 参数（正常参数 + 篡改参数）

### 8. 输出结果

生成 `evidence/authz-findings.json`，结构：

```json
{
  "skill": "authz-analyzer",
  "scanned_at": "ISO8601时间戳",
  "source_dir": "扫描路径",
  "auth_mechanism": {
    "login_flow": {
      "entry": "登录入口文件:行号",
      "token_exchange_api": "换取token的API",
      "token_storage": "token存储位置",
      "refresh_mechanism": "刷新机制"
    },
    "token_usage": {
      "type": "bearer/custom",
      "added_by": "request_wrapper/manual",
      "location": "添加token的代码位置"
    }
  },
  "identities": [
    {
      "id": "IDENTITY-ID",
      "type": "anonymous/authenticated/admin/vip",
      "description": "身份描述",
      "source": "身份来源",
      "trust_client": true/false
    }
  ],
  "resources": [
    {
      "id": "RES-ID",
      "type": "user_data/order/payment/admin",
      "api": "API路径",
      "params": ["参数列表"],
      "sensitive_params": ["敏感参数"]
    }
  ],
  "matrix": [
    {
      "resource_id": "资源ID",
      "identity": "身份ID",
      "expected": "allow/deny/allow_own_only",
      "actual": "unknown/needs_verification",
      "risk": "风险描述"
    }
  ],
  "findings": [
    {
      "finding_id": "AUTHZ-XXX",
      "type": "horizontal_privilege_escalation/vertical_privilege_escalation/auth_bypass/client_role_trust",
      "severity": "CRITICAL/HIGH/MEDIUM/LOW",
      "confidence": "HIGH/MEDIUM/LOW",
      "api": "HTTP方法 API路径",
      "vulnerable_param": "漏洞参数名",
      "description": "漏洞描述",
      "locations": ["代码位置"],
      "evidence_refs": ["证据ID"],
      "dataflow": {
        "source": {"file": "源文件", "line": 行号, "type": "来源类型"},
        "sink": {"file": "目标文件", "line": 行号, "type": "sink类型"},
        "guards": ["验证逻辑"]
      },
      "test_case": {
        "id": "测试用例ID",
        "steps": "测试步骤",
        "expected": "预期结果",
        "vulnerable_if": "漏洞判定条件"
      }
    }
  ],
  "statistics": {
    "total_findings": 数量,
    "by_type": {
      "horizontal_privilege_escalation": 数量,
      "vertical_privilege_escalation": 数量,
      "auth_bypass": 数量,
      "client_role_trust": 数量
    },
    "by_severity": {
      "CRITICAL": 数量,
      "HIGH": 数量,
      "MEDIUM": 数量,
      "LOW": 数量
    }
  }
}
```

## 置信度判定

- **HIGH**：发现明确代码证据（客户端可控参数 + 无验证逻辑）
- **MEDIUM**：发现可疑模式但缺少完整数据流确认
- **LOW**：理论风险，需动态测试验证

## 严重性评级

- **CRITICAL**：客户端角色信任、管理接口无认证
- **HIGH**：敏感资源水平越权（订单、支付、个人信息）
- **MEDIUM**：一般资源水平越权、低敏感度垂直越权
- **LOW**：公开资源的认证缺失

## 关键能力

- ✅ 智能身份识别：从代码推断角色类型
- ✅ 资源清单自动构建：从 API 提取资源分类
- ✅ 权限矩阵生成：可视化权限关系
- ✅ Sub-agent 协作：复杂数据流交给 dataflow-tracer
- ✅ 测试用例生成：可直接用于动态测试
- ✅ 置信度评估：区分"确认"和"需验证"

## 输出文件

- `evidence/authz-findings.json` - 完整分析结果（必需）
- `evidence/authz-test-cases.json` - 测试用例列表（可选，可内嵌于 findings）
