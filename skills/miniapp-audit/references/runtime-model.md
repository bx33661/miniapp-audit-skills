# 小程序开发与运行结构

在定位业务入口、解释流量或决定需要哪些材料时阅读。先建立运行模型，再决定是否需要源码或解包。

平台语义有疑点时按 [平台案例索引](platform-cases.md) 按需阅读：身份/业务授权与多通道会话见 [身份案例](platform-identity-session.md)，Page/Component、分包、构建和 rich-text/web-view 见 [运行案例](platform-render-build.md)，可导入项目的工具能力与纯黑盒代理边界见 [取证案例](platform-tools-evidence.md)。案例提供定位方法和官方依据，不要求安装 Nightly、默认使用云开发或先取得完整源码。

## 从业务动作追踪

| 层次 | 开发结构 | 审计中要追踪什么 |
|---|---|---|
| 应用 | App、app.json、全局状态与本地存储 | 启动/前台恢复、环境选择、登录交换、会话初始化与失效 |
| 页面 | Page、页面路由、onLoad/onShow、页面事件 | 入口参数、scene、页面切换、刷新与具体用户动作 |
| 组件 | Component、properties、事件、Behavior | 参数传递、复用行为、组件事件到业务处理函数的链路 |
| 视图 | WXML、WXSS、WXS、数据绑定 | 展示值和事件绑定如何连接逻辑；不能套用浏览器 DOM/XSS 结论 |
| 请求层 | wx.request、上传下载、WebSocket、云 SDK、业务封装 | base URL、认证注入、签名、拦截器、参数转换和响应处理 |
| 可信服务 | 自建后端、云函数、数据库/存储规则、支付服务 | 身份来源、归属与租户、业务状态和最终安全决策 |

记录一条最短实际链路：用户动作 → 页面/组件事件 → 请求封装 → 实际传输 → 服务端结果。只有流量时先记录动作、请求和响应；没有源码不补造中间函数名。

## 页面、分包与插件

- 源码中 app.json 描述页面、分包、组件和插件等入口；页面/组件的同名 JS、WXML、JSON、WXSS 各有职责，并非每种文件都必需。
- 页面 onLoad 参数、二维码/分享 scene、组件 properties 与存储都可能参与请求构造。onShow 等生命周期可重复触发刷新，不能把多条相同请求自动当重放漏洞。
- 分包按实际访问流程加载；未进入的业务页面可能没有被下载或触发请求。独立分包和插件可能有不同初始化、依赖与上下文边界，不能假定主包全局状态始终可用。
- 插件 provider、AppID、云环境 ID 是标识；是否存在越权要看实际身份与授权规则。插件的内部材料不可见时按可观察行为记录限制。

## 源码、构建产物与框架

源码目录和发布包不是相同布局。原包可能包含 app-config.json、app-service.js、页面 HTML 或 bundle 模块；不能用开发目录的逐页文件要求判断所有构建产物。

uni-app 的 pages.json、App.vue、uni.request 和 Taro 的页面配置、Taro.request 是源码线索；发布后可能转成微信原生调用和压缩模块。先核对真实框架与构建入口，再定位请求封装；不能因看不到 wx.request 字面量就断定没有请求。

source map 和重命名只帮助定位，必须能回到原始制品。解包用于补充调用、签名或隐含参数信息，不能作为抓包和接口测试的先决条件。

## 登录与业务请求

wx.login 产生临时 code，应用通常通过服务端交换并建立自己的会话。OpenID/UnionID 是身份标识，业务 Token、Cookie、云 SDK 上下文和 web-view 会话可能分别工作；AppID 或 User-Agent 不等于业务登录身份。

观察登录前后、切换账号、退出后失效与请求头/body 的实际变化。记录账号角色与资源归属，不凭 token 字段名判断认证成功。签名可能绑定 body、时间、nonce 和会话；重放失败先分辨构造与认证问题。

## 运行环境与可见性

记录实际设备/客户端、基础库（可获得时）、开发/体验/正式环境和后端地址；名称中有 test 不能证明环境安全。开发者工具设置与发布平台控制、后端授权是不同事实。

小程序请求、web-view、上传下载、WebSocket 和云 SDK 可能经过不同传输路径。代理中没有记录时先核对进程、host、证书、协议与操作时间；不要认定没有流量。能读取请求详情、成功实际重放、证明安全边界失效是三个不同完成条件。

## 官方依据

- [目录结构](https://developers.weixin.qq.com/miniprogram/dev/framework/structure.html)
- [框架文档](https://developers.weixin.qq.com/miniprogram/dev/framework/)
- [API 文档](https://developers.weixin.qq.com/miniprogram/dev/api/)
