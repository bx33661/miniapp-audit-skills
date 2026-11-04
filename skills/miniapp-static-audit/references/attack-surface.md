# 攻击面映射的判断依据

产物为 `evidence/attack-surface.json`，遵循 [attack-surface-output.schema.json](../assets/attack-surface-output.schema.json) 及其中引用的 [api-call.schema.json](../assets/api-call.schema.json)，`skill` 为 `miniapp-static-audit`。攻击面是材料目录，不是漏洞结论。

## 识别实际调用

- 从已有源码、配置与提取结果定位 `wx.request`、上传/下载、WebSocket、`wx.cloud.callFunction`、云数据库，以及 uni-app、Taro 和真实存在的自定义封装。
- 先确认导入、别名和封装定义，再将名为 `request`、`http` 或 `api` 的符号认定为网络调用。字符串、注释和死代码单独注明。
- 沿调用点追踪 URL、method、headers、参数、环境配置与拦截器。动态值无法还原就保留原表达式与未知部分，不拼接虚构域名、请求体或认证方式。
- `wx.login` 返回临时 code；检查实际 code 交换接口、会话保存及请求注入位置。看到 token 名字不等于已认证，没见 Authorization 也不等于匿名。
- 云调用区分客户端 SDK、云函数实现和云数据库规则；小程序材料没有后端实现时，记录服务端覆盖缺口。

## 微信特有边界

- 从实际配置记录 AppID、页面、分包、插件、基础库与框架。区分 `app.json`、`app-config.json`、bundle 模块与 source map；框架不明使用 `unknown`。
- 隐私相关调用包括位置、手机号事件、用户资料、相册/相机、剪贴板、录音、蓝牙与本地存储。记录真实调用位置和行为；获取、展示、保存和上传是不同操作。
- `permission`、`requiredPrivateInfos` 和平台隐私保护指引的作用不同。只有核实具体 API、基础库及平台规则适用性后，才能记录声明差异；不能把所有隐私接口都塞入 `requiredPrivateInfos`。
- `urlCheck` 是开发工具设置，不能证明发布环境域名校验被关闭。服务端配置的域名白名单不一定随包提供。
- 对 `<web-view>` 追踪 src 的实际来源、跳转约束、消息处理与 native 操作。用户可控 URL 是待查边界，不直接等于 XSS。
- 导航、插件、云环境 ID、集合名和下载文件地址都是后续核实入口；公开标识本身不是密钥或越权。

## 域名与规范化

- 记录实际协议、域名、用途和位置。HTTP/WS 需要结合运行环境、是否到达及承载数据核实影响；不能仅凭 URL 字面量确认泄露。
- 自有服务、受托处理者、独立第三方与微信平台需按主体材料核实。非微信域名不自动代表第三方；未核实 `is_third_party` 时不填 `false`。
- 按 method、实际环境/域名、路径语义归并调用，保留所有位置与参数差异。查询参数可以影响路由或权限，不可一律丢弃后合并。
- 同路径不同主体、云环境、请求签名或身份分支应保留区别。API 编号不替代发现的稳定 `F-001` 编号。

## 输出范围

必需字段是 `skill`、`scanned_at`、`source_dir`、`metadata`、`apis`、`statistics`、`limitations`。只按实际分析填充 `cloud_functions`、`cloud_database`、`sensitive_apis`、`permissions`、`domains`、`webviews` 等 schema 支持的目录。

机械提取器可能只覆盖静态 URL、参数或部分配置；它没有分析的 `cloud_database`、`sensitive_apis`、`request_wrappers`、`permissions.used/undeclared` 及相应统计可以缺失。读取 `limitations`，随后按本参考核实；字段缺失不代表零调用、零风险或检查通过。只有实际完成该项检查才报告零数量。

把可验证的边界疑点交给鉴权、支付、隐私或数据流分析，引用原始调用位置，显式记录 `needs_validation`。`confirmed` 需要 E2/E3 直接证据及完整根因、复现、影响、修复、预期与实际、复测和非空证据引用；`rejected` 保留排除依据。目录命中不直接进入最终风险计数。
