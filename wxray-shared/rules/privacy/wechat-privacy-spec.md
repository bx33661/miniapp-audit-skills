# 微信小程序隐私保护规范（2023）

## 隐私保护指引配置

### __usePrivacyCheck__
- 在 `app.json` 中配置 `"__usePrivacyCheck__": true` 启用隐私保护检查
- 启用后微信会在小程序首次启动时自动弹出隐私保护指引

### privacyUrl
- 必须在 `app.json` 中配置隐私政策链接
- 格式：`"privacyUrl": "https://example.com/privacy.html"`
- 或使用嵌套格式：`"privacy": { "url": "https://example.com/privacy.html" }`

## 隐私接口声明

### requiredPrivateInfos
在 `app.json` 中声明小程序使用的所有隐私接口：

```json
{
  "requiredPrivateInfos": [
    "chooseAddress",
    "chooseLocation",
    "getLocation",
    "getUserProfile"
  ]
}
```

### 隐私接口清单

#### 位置信息
- `chooseLocation` - 选择位置
- `choosePoi` - 选择地点
- `getLocation` - 获取当前位置
- `onLocationChange` - 监听位置变化
- `startLocationUpdate` - 开始更新位置
- `startLocationUpdateBackground` - 后台定位

#### 用户信息
- `getUserInfo` - 获取用户信息（昵称、头像）
- `getUserProfile` - 获取用户信息（带授权弹窗）

#### 通讯录
- `addPhoneContact` - 添加手机联系人
- `chooseContact` - 选择联系人

#### 相册
- `chooseImage` - 选择图片
- `chooseMedia` - 选择图片或视频
- `chooseVideo` - 选择视频
- `chooseMessageFile` - 选择聊天文件
- `saveImageToPhotosAlbum` - 保存图片到相册
- `saveVideoToPhotosAlbum` - 保存视频到相册
- `writePhotosAlbum` - 写入相册权限

#### 摄像头
- `camera` - 摄像头组件

#### 麦克风
- `startRecord` - 开始录音
- `getRecorderManager` - 录音管理器

#### 蓝牙
- `bluetooth` - 蓝牙相关接口

#### 其他
- `chooseAddress` - 选择收货地址
- `chooseInvoiceTitle` - 选择发票抬头
- `getWeRunData` - 获取微信运动数据

## 隐私弹窗 API

### wx.getPrivacySetting()
获取隐私协议状态：
```javascript
wx.getPrivacySetting({
  success: res => {
    // res.needAuthorization: 是否需要用户授权隐私协议
    // res.privacyContractName: 隐私协议名称
  }
})
```

### wx.openPrivacyContract()
打开隐私协议页面：
```javascript
wx.openPrivacyContract({
  success: () => {}, // 成功打开
  fail: () => {}     // 打开失败
})
```

### wx.requirePrivacyAuthorize()
请求用户授权隐私协议（需在隐私接口调用前）：
```javascript
wx.requirePrivacyAuthorize({
  success: () => {
    // 用户同意授权，可以继续调用隐私接口
  },
  fail: () => {
    // 用户拒绝授权
  }
})
```

## 用户授权流程

### 授权时机
- 首次启动小程序时弹出隐私协议
- 调用隐私接口前必须获得用户同意
- 用户可随时查看和修改授权状态

### 授权方式
- 使用 button 组件的 `open-type="agreePrivacyAuthorization"`
- 或使用 `wx.requirePrivacyAuthorize()` 主动请求

### 弹窗要求
- 必须清晰说明收集的个人信息类型
- 必须说明收集的目的和用途
- 不得默认勾选同意
- 必须提供拒绝选项

## 第三方插件和SDK

### 插件声明
在 `app.json` 中声明使用的插件：
```json
{
  "plugins": {
    "myPlugin": {
      "version": "1.0.0",
      "provider": "wxidxxxxxxxxxxxx"
    }
  }
}
```

### 第三方处理声明要求
- 在隐私政策中明确说明使用的第三方服务
- 列出第三方名称、处理的数据类型和目的
- 说明第三方的数据安全措施

## 数据安全要求

### 传输安全
- 所有数据传输必须使用 HTTPS
- 不得使用 HTTP 明文传输个人信息

### 存储安全
- 本地存储的敏感信息应加密
- 定期清理不再需要的数据

### 服务器要求
- 服务器域名必须在小程序管理后台配置
- 必须完成域名备案和 HTTPS 证书配置

## 用户权利保障

### 撤回同意
- 提供便捷的权限管理入口
- 用户可随时撤回对隐私接口的授权
- 撤回后不得影响基本功能使用

### 账号注销
- 提供账号注销功能入口
- 注销流程不得设置不合理障碍
- 注销后及时删除用户数据

### 数据访问
- 用户可查看已收集的个人信息
- 提供数据更正和删除功能

## 审核要求

### 提审材料
- 隐私政策链接必须可访问
- `requiredPrivateInfos` 必须与代码实际使用一致
- 不得声明未使用的隐私接口

### 常见驳回原因
- 隐私政策链接无效或无法访问
- 使用隐私接口但未在 `requiredPrivateInfos` 中声明
- 隐私政策内容不完整或不符合规范
- 未提供用户协议或服务条款
- 过度收集与功能无关的个人信息

## 违规处罚

### 轻微违规
- 警告并限期整改
- 暂停小程序发布能力

### 严重违规
- 下架小程序
- 封禁开发者账号
- 列入黑名单

### 违规行为
- 未经授权收集个人信息
- 隐私政策虚假或误导
- 违规向第三方提供用户数据
- 未提供账号注销功能
- 未经授权收集儿童信息
