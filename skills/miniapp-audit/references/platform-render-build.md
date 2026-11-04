# 页面、分包、构建与渲染案例

阅读范围：2026-11-04 仅读取所列官方页面/仓库说明，未编译或运行项目，未在模拟器/真机测试。目录：[R1](#r1-页面组件与构建产物定位)、[R2](#r2-普通分包与独立分包)、[R3](#r3-rich-text-与-web-view)。

## R1 页面组件与构建产物定位

- **适用条件**：已有源码/获授权制品，但找不到页面动作、请求入口或框架封装；观察到原生、uni-app 或 Taro 线索。
- **实际语义**：`Page` 定义页面数据、生命周期和事件，`onLoad` 接收打开路径参数，`onShow` 可再次触发；页面也可以使用 `Component` 构造，Definition 形式的页面生命周期可位于 methods，不能仅搜索 `Page(`。[S1/S2] 跨端框架支持多个目标，源码语言不决定当前运行端。[S4/S5]
- **观察与验证**：先识别当前材料与目标：原生开发目录、框架源码、编译后的微信小程序目录、解包制品或 H5。读取现有项目配置的 `miniprogramRoot`、compileType、构建目标和依赖版本；从实际页面路径/事件绑定找到处理函数，再沿请求封装/拦截器定位最终网络调用。uni-app 的页面配置和 Taro 的应用/页面配置只作为线索，以项目内真实文件为准。
- **预期证据**：制品版本/摘要、项目根与实际小程序根、目标平台、页面路径、事件/生命周期、请求封装及实际请求之间的定位记录；source map 必须能关联当前制品。
- **易错推断**：看不到 `wx.request` 不表示没有请求，框架可经包装生成调用；React/Vue 源码不能证明运行在浏览器；重复 onShow 刷新不能单独证明重放漏洞；`Component` 注册不排除它是页面。不能拿源码开发目录布局去否定压缩/解包产物。
- **缺权限边界**：没有匹配源码、构建映射或发布制品时，止于已知调用点/流量，不补造文件名、函数名或构建参数；可从黑盒动作与代理请求继续定位。项目配置可能含预处理脚本，仅读取不代表允许执行。[S3]
- **来源**：[S1 Page](https://developers.weixin.qq.com/miniprogram/dev/reference/api/Page.html)、[S2 组件脚本](https://developers.weixin.qq.com/miniprogram/dev/framework/component-framework/scripting.html)、[S3 项目配置](https://developers.weixin.qq.com/miniprogram/dev/devtools/projectconfig.html)、[S4 uni-app 官方跨端说明](https://uniapp.dcloud.net.cn/)、[S5 Taro 官方 README](https://github.com/NervJS/taro/blob/main/README.md)。S4/S5 仅支持跨端定位原则，不证明某项目的输出目录或编译实现。

## R2 普通分包与独立分包

- **适用条件**：某页面首次进入才有请求、直接打开分享路径与从首页进入行为不同，或材料只有部分包。
- **实际语义**：app.json 的 `subPackages`/`subpackages` 定义 root、pages 等，独立包通过 `independent` 声明。普通分包与独立分包的主包依赖不同；独立分包可不下载主包直接启动，此时 App 尚未注册，普通 `getApp()` 可能为 undefined，主包 App 的 onLaunch/首次 onShow 延后。[S6/S7]
- **观察与验证**：读取实际包配置、入口与依赖；分别记录冷启动直接进入独立包、主包跳入独立包、首次进入普通分包的动作，比较会话初始化、环境选择和请求头生成。若配置了分包 entry，沿其注入时执行的入口继续追踪；异步分包能力按实际配置解释，不能套用绝对依赖禁令。
- **预期证据**：入口路径/scene、冷启动状态、已加载包、independent 配置、初始化调用顺序及对应请求差异；缺包时列出未覆盖的 root/页面。
- **易错推断**：独立分包不是另一个可信身份或业务租户；主包没有请求不表示子包没有接口；主包登录完成不能证明独立包直达路径也执行同样初始化。未加载页面不是“已覆盖无风险”。
- **缺权限边界**：没有包或不能进入特定入口时，保留该入口覆盖缺口，继续分析已有页面与流量；不把下载/解包所有分包作为全部接口测试的前置门槛。
- **来源**：[S6 使用分包](https://developers.weixin.qq.com/miniprogram/dev/framework/subpackages/basic.html)、[S7 独立分包](https://developers.weixin.qq.com/miniprogram/dev/framework/subpackages/independent.html)，注意其基础库、低版本兼容与异步分包说明。

## R3 rich-text 与 web-view

- **适用条件**：不可信数据到达 nodes、HTML 字符串、第三方富文本组件或网页 src，怀疑内容注入/脚本执行。
- **实际语义**：微信原生 `rich-text` 接受节点数组或 HTML 字符串，只支持受信节点/属性；文档明确内部所有节点事件被屏蔽，不受信节点连同子节点移除。[S8] `web-view` 是承载网页的另一组件，具有业务域名和 JSSDK 通信约束。[S9] renderer 名称 WebView 不等于页面含 `web-view`。
- **版本边界**：读取目标 renderer、基础库、客户端、组件来源和 mode。S8 当前分别描述 Skyline 映射/布局差异，以及 mode 的 `web`（3.6.0 起）和 `web-static`（3.7.7 起）；这些选项不允许推断它具备任意网页脚本或相同会话能力，必须按该版本真实实现核实。
- **观察与验证**：先判定最终 sink 是原生 rich-text、第三方解析组件还是 web-view 网页。追踪数据源、预处理与属性，再用获授权的无害标记对比实际节点显示、属性保留和交互；脚本能力假设必须有对应运行环境中的实际执行证据。对网页另行定位 src/跳转、网页脚本和桥接消息处理，避免复用原生组件结论。
- **预期证据**：组件声明/依赖版本、完整 source-to-sink 位置、输入与处理后 nodes、renderer/基础库/mode、设备与观察结果；跨用户影响还需证明谁可写入、谁会读取及具体权限后果。
- **易错推断**：HTML 字符串进入原生 rich-text 不等于浏览器 innerHTML XSS；文档支持 class/style 或 img 不表示支持 onerror/script；第三方组件与框架同名标签未必等同原生组件；模拟器结果不能直接推广到所有真机/基础库。
- **缺权限边界**：不能运行目标 renderer 时仅报告数据流和待验证能力，不声称已执行脚本或固定漏洞等级；没有网页源码时仍可记录获授权的网页流量与可见跳转，未知桥接实现保持未知。
- **来源**：[S8 rich-text](https://developers.weixin.qq.com/miniprogram/dev/component/rich-text.html) 的受信节点、Bug & Tip、Skyline 属性；[S9 web-view](https://developers.weixin.qq.com/miniprogram/dev/component/web-view.html) 的属性、相关接口与 Bug & Tip。
