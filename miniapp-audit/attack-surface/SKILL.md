---
name: miniapp-audit-attack-surface
description: 提取小程序攻击面 - HTTP/WebSocket API、云函数、权限声明、域名配置、敏感组件，支持 native/uni-app/Taro 框架
metadata:
  version: 1.0.0
  category: security-audit
  author: WxRay
  input_format: "source_dir=<path> output_dir=<path> [scope=full|api_only|sensitive_api_only]"
  output_schema: "../wxray-shared/schemas/attack-surface-output.schema.json"
allowed-tools:
  - Bash
  - Read
  - Write
---

# Attack Surface - 攻击面映射

## 目标

全面提取小程序的攻击面：
- HTTP/HTTPS API 调用
- WebSocket 连接
- 云函数调用
- 云数据库操作
- 上传/下载操作
- 隐私和敏感 API
- 权限声明
- 域名配置
- WebView 和插件

## 执行步骤

### 1. 提取项目元数据

读取配置文件 `app.json`、`project.config.json`、`package.json`，提取：
- AppID（脱敏处理）
- 项目名称
- 框架类型（原生/uni-app/Taro/Remax）
- 基础库版本
- 页面列表
- 分包列表
- 插件列表

### 2. 提取 HTTP/HTTPS API 调用

搜索所有网络请求调用模式，支持：
- 原生：`wx.request`、`wx.uploadFile`、`wx.downloadFile`
- uni-app：`uni.request`、`uni.uploadFile`
- Taro：`Taro.request`
- 第三方：`axios`、`fetch`
- 自定义封装：`request`、`http.get`、`api.post`

对每个调用提取：
- URL（完整地址或路径模式）
- HTTP 方法（GET/POST/PUT/DELETE）
- 参数列表（从代码推断）
- 请求头配置
- 认证方式（Bearer Token/Cookie/自定义）
- 调用位置（文件路径和行号）

### 3. 处理动态 URL

识别 BaseURL 配置：
- 查找 `BASE_URL`、`API_BASE`、`baseUrl` 等常量定义
- 追踪配置来源（硬编码/配置文件/环境变量）
- 拼接完整 URL 模式

识别统一请求封装：
- 查找 `utils/request.js`、`api/index.js` 等封装文件
- 提取封装函数位置
- 记录是否添加认证头
- 记录拦截器逻辑

### 4. 提取云函数调用

搜索 `wx.cloud.callFunction`、`wx.cloud.database()`、`wx.cloud.uploadFile` 调用，提取：
- 云函数名称
- 传入参数结构
- 调用位置

### 5. 提取隐私和敏感 API

搜索所有隐私 API 调用：
- 位置：`wx.getLocation`、`wx.chooseLocation`
- 用户信息：`wx.getUserProfile`、`wx.getUserInfo`、`getPhoneNumber`
- 相册相机：`wx.chooseImage`、`wx.chooseMedia`、`wx.chooseVideo`
- 剪贴板：`wx.getClipboardData`、`wx.setClipboardData`
- 存储：`wx.setStorage`、`wx.getStorage`、`wx.setStorageSync`
- 录音蓝牙：`wx.startRecord`、`wx.getRecorderManager`、`wx.startBluetoothDevicesDiscovery`

记录每个调用的位置和上下文。

### 6. 检查权限声明

从 `app.json` 提取 `permission` 和 `requiredPrivateInfos` 字段。

对比分析：
- 列出所有声明的权限
- 列出所有实际调用的 API
- 标记未声明但被使用的 API（合规风险）

### 7. 提取域名配置

从配置文件提取：
- `project.config.json` 中的 `urlCheck` 设置
- 请求域名白名单配置

从代码提取：
- 硬编码的完整 URL
- BaseURL 配置值
- WebSocket 地址

分类域名：
- HTTPS vs HTTP（标记 HTTP 为不安全）
- WSS vs WS
- 自有域名 vs 第三方域名

### 8. 提取 WebView 组件

搜索 `<web-view>` 标签，提取：
- WebView 的 src 属性（静态或动态）
- 判断 URL 是否用户可控（XSS 风险）
- 记录调用位置

### 9. API 去重和规范化

按 `method + 规范化端点` 去重：
- 提取 URL 路径模式（去除查询参数值）
- 合并相同端点的不同参数调用
- 保留所有调用位置引用

### 10. 生成输出

生成 `evidence/attack-surface.json`，包含：

主要字段：
- `skill`: "attack-surface"
- `scanned_at`: ISO 8601 时间戳
- `source_dir`: 源码目录路径
- `metadata`: 项目元数据（app_id、app_name、framework、pages_count、subpackages_count）
- `apis`: API 调用列表，每项包含：
  - `id`: API-001, API-002...
  - `type`: http/websocket/cloud
  - `method`: GET/POST/PUT/DELETE
  - `url`: 完整 URL
  - `url_pattern`: 路径模式
  - `params`: 参数列表
  - `auth`: 认证信息（type、source）
  - `locations`: 调用位置数组（file、line）
  - `wrapper`: 封装信息（type、interceptor）
  - `domain`: 域名
  - `protocol`: https/http/wss/ws
  - `risk_indicators`: 风险标记数组
- `cloud_functions`: 云函数列表
- `sensitive_apis`: 敏感 API 列表
- `permissions`: 权限对比（declared、used、undeclared）
- `domains`: 域名列表
- `webviews`: WebView 列表
- `statistics`: 统计信息（total_apis、http_apis、cloud_functions、sensitive_apis、third_party_domains）

## 工具使用

使用 `rg`（ripgrep）搜索代码模式：
- 搜索 API 调用：`rg "wx\.request\(" --type js --json`
- 搜索云函数：`rg "wx\.cloud\.callFunction" --type js -A 5`
- 搜索敏感 API：`rg "(getLocation|getUserProfile|chooseImage)" --type js`

可选：使用 `ast-grep` 进行 AST 级别精确搜索。

可选：动态生成 Node.js 脚本使用 @babel/parser 和 @babel/traverse 进行 AST 解析。

## 输出文件

- `evidence/attack-surface.json` - 完整攻击面报告
- `evidence/api-calls.json` - API 调用详细列表（可选，引用主输出）
