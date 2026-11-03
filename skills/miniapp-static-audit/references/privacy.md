> Detailed checklist. Adapt it to the target; this is not a rigid sequence.

# Privacy Compliance - 隐私合规检查

检查小程序隐私合规性，覆盖《个人信息保护法》(PIPL) 和微信小程序隐私规范。

## 法规参考

详细条款见：
- PIPL 完整条款：https://www.npc.gov.cn/npc/c30834/202108/a8c4e3672c74491a80b53a172bb753fe.shtml
- 微信小程序用户隐私保护指引：https://developers.weixin.qq.com/miniprogram/dev/framework/user-privacy/

## 执行流程

### 1. 隐私政策检查

#### 1.1 检查配置项
读取 `app.json`，检查：
- `__usePrivacyCheck__` 是否为 `true`（未启用 → CRITICAL 问题，引用微信2023规范）
- `privacyUrl` 或 `privacy.url` 是否配置（缺失 → CRITICAL 问题，引用 PIPL 第13条）

#### 1.2 检查弹窗实现
读取 `app.js`，检查代码中是否使用：
- `wx.getPrivacySetting()`
- `wx.openPrivacyContract()`
- `wx.requirePrivacyAuthorize()`

若未检测到且 `__usePrivacyCheck__` 为 false → HIGH 问题，建议使用 `wx.getPrivacySetting()` 实现弹窗。

#### 1.3 验证隐私政策可访问性
若配置了 `privacyUrl`：
- 使用 `curl` 检查 HTTP 状态码
- 非 200 → HIGH 问题，记录 URL 和状态码

### 2. 权限声明一致性检查

#### 2.1 加载数据
- 从 `attack_surface.json` 读取 `permissions` 字段（实际使用的 API）
- 从 `app.json` 读取 `requiredPrivateInfos` 字段（已声明的隐私接口）

#### 2.2 定义隐私接口映射
建立隐私接口到数据类型的映射表：
- 位置类：`chooseAddress`, `chooseLocation`, `choosePoi`, `getLocation`, `onLocationChange`, `startLocationUpdate`
- 用户信息类：`getUserInfo`, `getUserProfile`
- 通讯录类：`chooseContact`, `addPhoneContact`
- 相册类：`chooseImage`, `chooseMedia`, `chooseVideo`, `saveImageToPhotosAlbum`, `saveVideoToPhotosAlbum`, `writePhotosAlbum`
- 麦克风类：`startRecord`, `getRecorderManager`
- 摄像头类：`camera`
- 蓝牙类：`bluetooth`
- 其他：`chooseInvoiceTitle`, `getWeRunData`

#### 2.3 交叉验证
对每个实际使用的隐私接口：
- 检查是否在 `requiredPrivateInfos` 中声明
- 未声明 → CRITICAL 问题，记录 API 名称、数据类型、使用位置（文件:行号），引用微信2023规范

对每个声明但未使用的接口：
- MEDIUM 问题，引用 PIPL 最小必要原则，建议移除

### 3. 数据收集分析

#### 3.1 识别收集的数据类型
定义数据收集 API 映射：
- `getUserInfo/getUserProfile` → 用户昵称、头像（敏感，身份信息）
- `getPhoneNumber` → 手机号（敏感，联系方式）
- `getLocation/chooseAddress` → 地理位置（敏感，位置信息）
- `getWeRunData` → 运动数据（非敏感，健康数据）
- `chooseInvoiceTitle` → 发票抬头（敏感，财务信息）
- `wx.login` → OpenID/UnionID（非敏感，身份标识）

遍历实际使用的 API，提取收集的数据类型、敏感性、类别和使用位置。

#### 3.2 标记敏感数据收集
对每个敏感数据：
- 生成 INFO 级别问题，标记为 `review_required: true`
- 问题描述：收集 [数据类型] 是否业务必需？
- 引用 PIPL 第6条（最小必要原则）

#### 3.3 检查数据传输安全
从 `attack_surface.json` 读取 `api_calls` 字段，对每个 API 调用：
- 检查 URL 是否以 `http://` 开头（明文传输）
  - 是 → HIGH 问题，记录 URL、方法、位置，引用 PIPL 第51条，建议使用 HTTPS
- 检查 URL 域名是否非微信官方（不包含 `api.weixin.qq.com`）
  - 是 → MEDIUM 问题，标记为第三方数据共享，引用 PIPL 第23条，标记 `review_required: true`

### 4. 第三方 SDK 合规检查

#### 4.1 识别第三方依赖
检查 `package.json` 是否存在，若存在：
- 读取 `dependencies` 和 `devDependencies`
- 识别常见数据收集 SDK：
  - `umeng-wxapp` → 友盟统计（MEDIUM 风险，设备信息+使用行为）
  - `tencent-analytics` → 腾讯移动分析（MEDIUM 风险）
  - `talkingdata-wxapp` → TalkingData（MEDIUM 风险）
  - `sensors-data` → 神策数据（MEDIUM 风险）
  - `jpush-wxapp` → 极光推送（MEDIUM 风险）

#### 4.2 检查插件声明
从 `app.json` 读取 `plugins` 字段，对每个插件：
- 生成 INFO 级别问题，标记为 `review_required: true`
- 问题：插件的数据处理是否在隐私政策中说明？
- 引用 PIPL 第23条

#### 4.3 生成第三方 SDK 清单
汇总：
- `packages` 列表（包名、版本、风险级别、收集的数据类型）
- `plugins` 列表（插件名、provider、version）
- `total_count` 总数

### 5. 用户权利检查

#### 5.1 检查账号注销功能
查找所有 JS 文件（排除 `node_modules`），搜索注销相关模式：
- 中文：`注销账号|注销账户|删除账号|账号注销`
- 英文：`deleteAccount|removeAccount|cancelAccount`
- API：`/user/delete|/account/cancel`

未找到 → HIGH 问题，引用 PIPL 第47条（用户注销权），建议在个人中心添加账号注销功能。

找到 → 生成 INFO 级别问题，标记为 `review_required: true`，提供检查清单：
- 服务端是否删除用户数据？
- 本地存储是否清理？
- 第三方平台数据是否同步删除？
- 是否有注销确认流程？
- 注销是否在15天内完成？

#### 5.2 检查数据导出功能
搜索数据导出相关模式：
- 中文：`导出数据|下载数据|个人信息副本`
- 英文：`exportData|downloadUserData|getPersonalData`

未找到 → MEDIUM 问题，引用 PIPL 第45条（数据可携带权），建议提供用户数据导出功能（JSON、CSV 等格式）。

### 6. 儿童保护检查

#### 6.1 判断是否面向儿童
定义儿童关键词：`儿童|少儿|小孩|宝宝|幼儿|kids|children|baby`

检查：
- `app.json` 的 `window.navigationBarTitleText`
- `project.config.json` 的 `description`

包含关键词 → 标记为面向儿童。

#### 6.2 儿童应用特殊检查
若面向儿童：
- 生成 HIGH 级别问题，引用 PIPL 第31条
- 列出要求：
  - 必须设置专门的儿童个人信息保护规则
  - 收集儿童信息需征得监护人同意
  - 不得超出目的范围收集儿童个人信息
  - 停止服务时应删除儿童个人信息
  - 不得向儿童推送商业广告

#### 6.3 检查监护人同意机制
搜索所有 JS 文件，查找模式：
- `监护人|家长同意|parental.*consent`（正则，忽略大小写）

未找到 → CRITICAL 问题，引用 PIPL 第31条，要求添加监护人同意流程。

### 7. 生成合规报告

#### 7.1 构建报告结构
创建 JSON 报告：
```
{
  skill: "privacy-compliance",
  checked_at: ISO时间戳,
  source_dir: 源码目录,
  regulations: ["PIPL", "WeChat Privacy Specification 2023"],

  summary: {
    total_issues: 总问题数,
    critical: CRITICAL 级别数,
    high: HIGH 级别数,
    medium: MEDIUM 级别数,
    review_required: 需人工审查的数量
  },

  sections: {
    privacy_policy: {
      status: "PASS"/"FAIL",
      issues: [...]
    },
    permissions: {
      status: "PASS"/"FAIL",
      declared: [...],
      actual_used: [...],
      issues: [...]
    },
    data_collection: {
      collected_data_types: [...],
      third_party_sharing: [...],
      issues: [...]
    },
    third_party_sdks: {
      catalog: {...},
      issues: [...]
    },
    user_rights: {
      account_deletion: true/false,
      data_export: true/false,
      issues: [...]
    },
    child_protection: {
      targets_children: true/false,
      issues: [...]
    }
  },

  compliance_checklist: {...}
}
```

#### 7.2 生成合规检查清单
构建 `compliance_checklist`：

**PIPL 合规项**：
- 第13条（明确告知）：根据 privacy_policy 问题判定 COMPLIANT/NON_COMPLIANT
- 第14条（规则公开）：根据 requiredPrivateInfos 是否配置判定
- 第17条（撤回同意）：标记为 NEEDS_REVIEW（需人工审查权限撤回功能）
- 第23条（第三方告知）：根据 SDK 总数判定 NEEDS_REVIEW/COMPLIANT
- 第45-47条（用户权利）：根据账号注销和数据导出功能判定 COMPLIANT/PARTIAL

**微信合规项**：
- 隐私保护指引：根据 `__usePrivacyCheck__` 判定
- requiredPrivateInfos 声明：根据未声明 API 数量判定
- 用户信息使用描述：标记为 NEEDS_REVIEW

#### 7.3 写入输出文件
将完整报告写入 `${outputDir}/evidence/privacy-compliance.json`。

## 问题分级标准

- **CRITICAL**：必须修复，否则无法通过审核（如未声明隐私接口、缺少监护人同意）
- **HIGH**：严重合规风险（如缺少注销功能、明文传输数据、隐私政策不可访问）
- **MEDIUM**：中等风险（如过度声明权限、第三方数据共享未说明）
- **INFO**：需人工审查（如敏感数据必要性、第三方插件说明）

## 输出文件

- `evidence/privacy-compliance.json` - 完整合规检查报告

## 报告示例结构

```json
{
  "skill": "privacy-compliance",
  "summary": {
    "total_issues": 12,
    "critical": 1,
    "high": 3,
    "medium": 5,
    "review_required": 6
  },
  "sections": {
    "privacy_policy": {
      "status": "FAIL",
      "issues": [
        {
          "type": "missing_privacy_check",
          "severity": "CRITICAL",
          "issue": "未启用隐私保护检查",
          "regulation": "WeChat 2023规范",
          "fix": "在 app.json 中添加 \"__usePrivacyCheck__\": true"
        }
      ]
    },
    "permissions": {
      "status": "FAIL",
      "declared": ["chooseLocation"],
      "actual_used": ["chooseLocation", "getUserProfile"],
      "issues": [
        {
          "type": "undeclared_privacy_api",
          "severity": "CRITICAL",
          "api": "getUserProfile",
          "data_type": "用户信息",
          "used_in": ["pages/profile/index.js:45"],
          "issue": "使用了隐私接口但未在 requiredPrivateInfos 中声明",
          "regulation": "WeChat 2023规范",
          "fix": "在 app.json 的 requiredPrivateInfos 中添加 \"getUserProfile\""
        }
      ]
    },
    "data_collection": {
      "collected_data_types": [
        {
          "api": "getUserProfile",
          "data_type": "用户昵称、头像",
          "sensitive": true,
          "category": "身份信息",
          "locations": [{"file": "pages/profile/index.js", "line": 45}]
        }
      ],
      "issues": []
    },
    "third_party_sdks": {
      "catalog": {
        "packages": [],
        "plugins": [],
        "total_count": 0
      },
      "issues": []
    },
    "user_rights": {
      "account_deletion": false,
      "data_export": false,
      "issues": [
        {
          "type": "missing_account_deletion",
          "severity": "HIGH",
          "issue": "未提供账号注销功能",
          "regulation": "PIPL 第47条 - 用户注销权",
          "fix": "在个人中心添加账号注销功能"
        }
      ]
    },
    "child_protection": {
      "targets_children": false,
      "issues": []
    }
  },
  "compliance_checklist": {
    "pipl_compliance": [
      {
        "article": "第13条",
        "requirement": "明确告知个人信息处理目的",
        "status": "NON_COMPLIANT",
        "evidence": [...]
      }
    ],
    "wechat_compliance": [
      {
        "requirement": "隐私保护指引",
        "status": "NON_COMPLIANT"
      }
    ]
  }
}
```
