# 开发者工具、原生执行与代理取证案例

阅读范围：2026-11-04 仅读取所列官方文档，未安装/启动 Nightly、执行 wechatide/CLI、导入项目、运行构建或检查，也未进行业务请求。目录：[T1](#t1-可导入项目的工具能力发现)、[T2](#t2-黑盒代理与请求证据)。

## T1 可导入项目的工具能力发现

- **适用条件**：已有可导入的获授权项目和相应账号/项目权限，需要在开发者工具中关联页面、SDK 调用、真实请求或模拟器行为。Nightly 仅在目标能力明确需要且现有工具无法提供时作为选项，不强制安装或升级。
- **实际语义**：官方 CLI 文档描述安装目录内 `cli`/`cli.bat`、开启服务端口及按命令查看帮助；打开项目会自动编译刷新，预览、上传、云管理和自动化分别是具体操作。[S1] 本机称作 `wechatide` 的可执行文件或包装器不能仅凭名称认定等同该 CLI，也不能假定其具备某个子命令。
- **观察与验证**：在具备执行授权时，先记录已安装工具版本、渠道、实际路径和本地帮助，再按需要发现能力；分别确认能否导入、账号能否访问、基础库/renderer 是否支持目标功能。仅在实际帮助或对应版本官方说明支持时使用命令，保留真实退出码、错误与操作范围；不要编造 `wechatide` 抓包、hook、登录或云操作接口。
- **原生执行边界**：DevTools/SDK 中发起获授权测试调用能补平台上下文、参数转换和页面行为证据；HTTP 重放器不能自动合成这些上下文。若工具缺少权限，只阻塞依赖该能力的步骤，已有黑盒代理和获授权接口测试仍成立。
- **预期证据**：工具版本/渠道/能力帮助摘要、项目根与有效配置、账号权限状态、页面动作和请求关联、真实错误；云调用可保存脱敏 requestID 关联授权日志。工具登录成功不等于业务会话有效。
- **易错推断**：Nightly 不保证具备目标能力；能打开目录不等于能预览真实 AppID；模拟器成功不证明真机、正式包或后端授权相同。项目私有配置可覆盖公共配置中的部分设置，开发域名/TLS 校验设置不代表生产策略。[S2/S3]
- **缺权限边界**：没有源码、导入配置、开发者身份、云权限或可用工具时，明确缺少哪一项及哪条证据无法取得；不要求获取他人权限，不把 Nightly/云开发/完整源码设为全流程门槛。不自动执行 upload/deploy 等发布操作补证。
- **来源**：[S1 命令行 V2](https://developers.weixin.qq.com/miniprogram/dev/devtools/cli.html)、[S2 项目配置](https://developers.weixin.qq.com/miniprogram/dev/devtools/projectconfig.html)、[S3 网络说明](https://developers.weixin.qq.com/miniprogram/dev/framework/ability/network.html)。
- **Nightly 来源限制**：[rich-text 官方页](https://developers.weixin.qq.com/miniprogram/dev/component/rich-text.html) 当前提示 Skyline 使用最新 Nightly 调试；其链接的 [Nightly 页面](https://developers.weixin.qq.com/miniprogram/dev/devtools/nightly.html) 在本次读取返回 404，未据此宣称已读版本能力或验证 wechatide。执行时以可获取的对应版本官方说明与本地帮助为准。

## T2 黑盒代理与请求证据

- **适用条件**：只有已安装小程序、测试账号和获授权范围，或源码/DevTools 无法使用；也适用于工具网络面板与代理观察不一致。
- **实际语义**：小程序请求、网页、云 SDK 是不同调用路径。`wx.request` 文档包含请求头、data 转换、状态码与 cookies，平台/版本可能使用 HTTP2/QUIC 等能力；其 success 回调表示收到了响应，不代表 HTTP 或业务成功。[S3/S4] 云 callFunction 的 data/event、requestID 与 getWXContext 是平台语义，不可用改写 JSON 的 openid 冒充可信调用身份。[S5/S6]
- **观察与验证**：以一个已知业务动作建立时间窗口与基线，记录设备/客户端/基础库、账号、前后台状态和实际 host；代理无流量时核对代理覆盖进程、设备证书信任、协议及 SDK/网页路径。保留真实 TLS/超时/协议错误，不用关闭校验制造成功；没有可读明文时说明可见范围。
- **请求定位**：保留实际 URL 编码、重复 query/form 键、Content-Type、body 字节以及会话和签名依赖。对受控账号 A/B 分开管理 Token、Cookie 和刷新状态；先确认各自基线身份与资源归属，再改变最少业务参数比较响应/状态变化。请求协议正确与业务授权正确分别判断。
- **HTTP 执行边界**：已有可重放流量时可使用执行器发送获授权 HTTP 请求，无需源码。计划中明确 `scope.origins/methods/max_requests/timeout_seconds/max_response_bytes` 和账号 `origins`、凭据环境变量；这些字段约束本次发送范围，不代表原生 SDK 权限或服务端授权。实际发送前仍需匹配目标协议，原生云调用不能未经适配改成任意 HTTP。
- **签名与加密**：内置 HMAC-SHA256 适配的规范串仅为大写 method、原始 path/query、Unix 秒时间、fresh nonce、最终线上 body 的 SHA256 小写 hex，逐项以换行连接；AES-GCM 适配仅为 base64(12 字节 nonce || ciphertext || 16 字节 tag)，密钥/AAD 需匹配已知协议。它们不是微信通用协议。未知 scheme、密钥或 SDK 语义只阻塞对应重放，不自动套用；也可保留原始密文字节而不声称可修改内部字段。
- **预期证据**：动作/账号/资源归属与实际 request/response 的关联、发送字节摘要、状态码及业务结果、代理路径、签名/解密处理说明；未发送、收到响应但校验失败、超时、会话失效、解密失败分别记录，不能生成虚构线上证据。对签名仅记录算法/载体，不留密钥或凭据值。
- **易错推断**：代理能查看不表示已成功重放；HTTP 200/SDK success 不表示越权；403 不自动等于会话过期；A 凭据配 B 的 openid 参数不表示执行身份已经变为 B。修改后签名无效不能证明服务端对象授权安全。缺流量不证明没有请求，规则/域名校验也不代替业务授权。
- **缺权限边界**：无第二账号时保留跨账号验证缺口；无法解密/签名或读取云上下文时，只陈述已观察响应与缺失条件。仍可测试范围内其他接口/账号；不因为一个步骤失败而宣布全流程阻塞或安全。
- **来源**：[S3 网络说明](https://developers.weixin.qq.com/miniprogram/dev/framework/ability/network.html)、[S4 wx.request](https://developers.weixin.qq.com/miniprogram/dev/api/network/request/wx.request.html)、[S5 callFunction](https://developers.weixin.qq.com/miniprogram/dev/wxcloudservice/wxcloud/reference-sdk-api/functions/Cloud.callFunction.html)、[S6 getWXContext](https://developers.weixin.qq.com/miniprogram/dev/wxcloudservice/wxcloud/reference-sdk-api/utils/Cloud.getWXContext.html)。计划字段与加密适配是本仓库执行器约定，不归因于官方 SDK。
