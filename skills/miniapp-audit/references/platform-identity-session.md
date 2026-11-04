# 身份、授权与多通道会话案例

阅读范围：2026-11-04 仅读取末尾官方文档；以下是定位方法，未对项目、云环境或业务接口执行验证。目录：[I1](#i1-自建后端登录交换)、[I2](#i2-云开发上下文与业务授权)、[I3](#i3-跨通道会话)。

## I1 自建后端登录交换

- **适用条件**：观察到 `wx.login`、临时 code 上传、业务登录接口或自建 Token/Cookie；先证实调用链，不默认项目使用云开发。
- **实际语义**：`wx.login` 获取临时登录凭证，服务端使用 `auth.code2Session` 换取 OpenID、session_key，以及满足条件时的 UnionID；业务服务端可据此生成自己的登录态。code 一次性使用，session_key 不应下发客户端或对外提供。[S1]
- **观察与验证**：在受控测试账号 A/B 上分别记录登录动作、交换请求、脱敏后的会话建立响应和首次业务请求。源码可见时追踪 code → 服务端交换结果 → 业务账号映射 → 会话签发 → 资源授权；仅凭客户端代码无法确认服务端真的调用了交换接口。验证时使用新 code，区分凭证复用失败、业务会话过期、签名错误与对象授权拒绝。
- **预期证据**：对应动作与时间、账号别名、环境/AppID、请求/响应关联、业务资源归属标记；可获得时补服务端交换及账号映射的脱敏日志或代码位置。避免保存原始 code、session_key、Token 或 Cookie。
- **易错推断**：拿到 OpenID 不表示拥有某订单；UnionID 不保证总会返回；`wx.login` 成功不表示业务登录成功；code 复用失败不证明业务请求具备抗重放能力。AppSecret 与 session_key 的暴露要分别追踪真实来源和可见范围。
- **缺权限边界**：没有服务端/日志时，只描述可见交换与会话行为；没有第二个获授权测试账号时不能声称跨账号授权已验证。不要为了补证向微信接口提交发现的密钥或他人 code。
- **来源**：[S1 小程序登录](https://developers.weixin.qq.com/miniprogram/dev/framework/open-ability/login.html)，含 `wx.login`、`auth.code2Session` 官方入口与一次性 code、session_key 约束。

## I2 云开发上下文与业务授权

- **适用条件**：实际存在 `wx.cloud.callFunction`、`wx-server-sdk`、CloudBase 数据访问或可见云权限配置；环境 ID、AppID 字符串本身不足以确定后端形态。
- **实际语义**：小程序端 `callFunction.data` 进入云函数 `event`；因而调用者提交的 `event.openid` 仍是参数，不能只因字段名称就视为可信身份。[S2] `cloud.getWXContext()` 在云函数调用上下文中提供 OPENID、APPID、SOURCE 等，字段随触发方式/跨账号调用变化；不能在 `exports.main` 外获取本次调用身份。[S3]
- **观察与验证**：定位实际调用环境与函数名，分别追踪 `event.openid/userId/tenantId` 和上下文 OPENID 的去向。对授权测试数据保持调用账号 A 不变，只改业务资源标识或声明的 openid，观察是否得到 B 的私有资源；有后台权限时用 requestID 关联日志，核对实际身份、归属/租户判断及数据访问路径。
- **预期证据**：脱敏函数参数、requestID、触发来源、上下文身份别名、授权判断代码/日志、对象真实归属及前后响应。要能证明身份经过哪个可信边界，不能只截图 `getWXContext` 返回值。
- **易错推断**：可信 OPENID 解决调用者身份，不自动解决业务授权；`event.openid` 的出现也不自动构成漏洞，它可能只是查询参数并受到归属校验。无 OPENID 的触发方式不能回退相信 event。SOURCE 要按实际调用链解释，不能将 IDE 或本地调试结果直接等同正式客户端。
- **权限路径**：区分客户端数据库规则与服务端 SDK/云函数处理路径，不能用其中一条路径的拒绝证明另一条安全。CloudBase 当前安全规则页限定传统模式，区分 `auth.openid`/`auth.uid`；PG 模式采用 GRANT/RLS，不套用传统规则结论。[S4]
- **缺权限边界**：不能查看部署代码、规则或日志时，记录这些事实未知；只有一次客户端拒绝不能断言规则配置完整。无法调用函数的入口不冒充已执行，可继续审计获授权的可见 HTTP 接口。
- **来源**：[S2 callFunction](https://developers.weixin.qq.com/miniprogram/dev/wxcloudservice/wxcloud/reference-sdk-api/functions/Cloud.callFunction.html)、[S3 getWXContext](https://developers.weixin.qq.com/miniprogram/dev/wxcloudservice/wxcloud/reference-sdk-api/utils/Cloud.getWXContext.html)、[S4 CloudBase 安全规则](https://docs.cloudbase.net/database/security-rules)。

## I3 跨通道会话

- **适用条件**：同一业务横跨 `wx.request`、云 SDK 或 `web-view`，出现登录不同步、Cookie/Token 混用或退出后仍可访问。
- **实际语义**：自建 Token/Cookie 是业务协议；`wx.request` 可设置请求头并返回响应头/cookies。[S5] 云调用具有自己的参数与平台上下文。[S2/S3] `web-view` 承载网页，仅通过规定 JSSDK 接口与小程序通信，`postMessage` 在文档规定时机触发，不能假定实时回调。[S6] 这些文档不能证明业务会话、Cookie 容器或退出行为自动共享。
- **观察与验证**：为每条通道单独列出登录入口、实际携带的凭据、身份绑定和退出动作。核对 web-view 初始 src、跳转/单点登录交换、网页 Cookie 与网页请求，再关联小程序请求；使用同一受控账号做登录前后与退出后比较，跨账号测试使用隔离会话。明确缓存展示和真实服务端读取的区别。
- **预期证据**：脱敏 URL/跳转链、请求通道、凭据载体名称、账号别名、Set-Cookie 更新、消息触发时间和实际业务响应；共享/交换会话的结论须有观测或服务端依据。
- **易错推断**：web-view User-Agent/AppID、`getEnv` 或页面能打开不等于服务端认证；`wx.request` 返回 cookies 不证明后续自动携带；小程序退出不必然注销网页会话，是否为缺陷要看产品明确的会话约定与实际影响。
- **缺权限边界**：无法调试网页或查看云流量时只覆盖可见通道，标注缺少哪段会话交换；不得复制 A 的凭据充当 B 后宣称 B 越权，也不得猜测网页 Cookie 隔离行为。
- **来源**：[S5 wx.request](https://developers.weixin.qq.com/miniprogram/dev/api/network/request/wx.request.html)、[S6 web-view](https://developers.weixin.qq.com/miniprogram/dev/component/web-view.html)，及 I2 的 S2/S3。
