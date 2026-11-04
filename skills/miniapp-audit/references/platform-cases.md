# 平台案例按需索引

本组参考用于解释微信平台语义、定位实际调用和界定证据，按当前疑点阅读对应案例；不增加主流程门槛，也不定义输出 schema。

| 当前疑点 | 阅读位置 | 需要回答的问题 |
|---|---|---|
| wx.login、code2Session、自建登录态 | [身份与会话 I1](platform-identity-session.md#i1-自建后端登录交换) | 微信身份如何绑定业务账号和后续凭据？ |
| 云函数 OPENID、event.openid、数据库权限 | [身份与会话 I2](platform-identity-session.md#i2-云开发上下文与业务授权) | 身份来自受信上下文还是调用参数，谁执行资源授权？ |
| Token、Cookie、云 SDK、web-view 身份混淆 | [身份与会话 I3](platform-identity-session.md#i3-跨通道会话) | 每条通道实际携带什么身份，是否存在明确交换？ |
| Page/Component 找不到请求或重复请求 | [运行与构建 R1](platform-render-build.md#r1-页面组件与构建产物定位) | 当前材料是源码、框架产物还是实际发布制品？ |
| 分包入口遗漏、独立分包初始化差异 | [运行与构建 R2](platform-render-build.md#r2-普通分包与独立分包) | 当前启动路径是否经过主包初始化？ |
| rich-text、HTML 字符串、web-view | [运行与构建 R3](platform-render-build.md#r3-rich-text-与-web-view) | 实际组件、renderer 和基础库提供什么能力？ |
| Nightly、wechatide、CLI 能否辅助定位 | [工具与取证 T1](platform-tools-evidence.md#t1-可导入项目的工具能力发现) | 当前工具实际支持什么，项目和账号是否具备使用条件？ |
| 纯黑盒、代理无流量、工具成功与业务成功 | [工具与取证 T2](platform-tools-evidence.md#t2-黑盒代理与请求证据) | 请求是否真实发送、收到完整响应、影响目标业务边界？ |

案例中的“观察与验证”是具备对应授权和材料时的操作建议，不表示已经执行。身份识别不代替对象归属、租户、角色和业务状态校验；发现结论必须落到实际边界与影响，不给 API 或组件名称预设漏洞等级。

编写依据范围：2026-11-04 仅读取各篇末尾列出的官方页面/仓库说明，未导入项目、启动微信或开发者工具、运行 wechatide/CLI、构建、测试、代理或发送业务请求。资料阅读不等于真机兼容性或部署权限已验证。官方页面会更新，实际定位时记录所依据的版本和可见材料。
