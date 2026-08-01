---
name: miniapp-audit-payment-audit
description: 支付安全审计 - 检测价格篡改、订单状态管理、回调验证、重放攻击风险
metadata:
  version: 1.0.0
  category: security-audit
  author: WxRay
  input_format: "source_dir=<path> output_dir=<path> attack_surface=<path>"
  output_schema: "../miniapp-audit-shared/schemas/payment-findings.schema.json"
allowed-tools:
  - Bash
  - Read
  - Write
---

# Payment Audit - 支付安全专项审计

## 功能

对小程序支付流程进行全面安全分析：
- 支付流程完整性检查
- 价格篡改风险
- 订单状态管理
- 支付回调验证
- 重放和重复支付保护
- 优惠券和折扣安全

## 执行流程

### 1. 识别支付流程

#### 1.1 搜索支付相关代码

```bash
# 微信支付 API
rg "wx\.requestPayment|wx\.requestPluginPayment" --type js -A 10

# 支付相关函数
rg "(pay|payment|order|checkout)" --type js -i

# 订单创建
rg "(createOrder|placeOrder|submitOrder)" --type js -A 10
```

#### 1.2 提取支付流程

完整流程：
```
商品选择 → 订单创建 → 价格计算 → 支付请求 → 支付回调 → 订单确认 → 发货
```

提取关键节点：
- **订单创建 API**：`/api/order/create`
- **价格计算**：客户端 or 服务端？
- **支付统一下单**：`/api/payment/prepay`
- **支付调用**：`wx.requestPayment()`
- **客户端回调**：`wx.requestPayment({success: ...})`
- **服务端回调**：异步通知 URL

### 2. 价格篡改检查

#### 2.1 客户端价格传递

**危险模式**：客户端计算并传递支付金额
```javascript
// 危险：客户端计算总价
const totalPrice = this.data.goodsPrice * this.data.quantity - this.data.discount

wx.request({
  url: '/api/order/create',
  data: {
    goodsId: this.data.goodsId,
    quantity: this.data.quantity,
    totalPrice: totalPrice  // ❌ 客户端传入金额
  }
})
```

**安全模式**：服务端重新计算
```javascript
// 安全：只传商品和数量，服务端计算价格
wx.request({
  url: '/api/order/create',
  data: {
    goodsId: this.data.goodsId,
    quantity: this.data.quantity
    // ✅ 不传价格，由服务端计算
  }
})
```

#### 2.2 检查点

搜索订单创建/支付相关 API 的参数：
- `totalPrice`, `amount`, `price`, `payAmount` → 客户端传入？
- 是否只传 `goodsId` + `quantity`？
- 是否有价格验证的服务端逻辑？

### 3. 优惠券和折扣安全

#### 3.1 客户端折扣计算

**危险模式**：
```javascript
// 危险：客户端计算折扣后价格
const discountPrice = originalPrice * this.data.discountRate

wx.request({
  url: '/api/order/create',
  data: {
    goodsId: goodsId,
    discountPrice: discountPrice  // ❌ 客户端计算的折扣价
  }
})
```

**安全模式**：
```javascript
// 安全：传优惠券ID，服务端验证和计算
wx.request({
  url: '/api/order/create',
  data: {
    goodsId: goodsId,
    couponId: this.data.selectedCoupon.id  // ✅ 只传优惠券ID
  }
})
```

#### 3.2 优惠券验证

检查优惠券使用是否有：
- 有效期验证
- 使用次数限制
- 商品适用范围
- 用户资格检查
- 防止重复使用

### 4. 订单状态管理

#### 4.1 订单状态机

标准状态流转：
```
待支付 → 已支付 → 已发货 → 已完成
         ↓
       已取消/已退款
```

#### 4.2 状态跳转检查

**危险模式**：客户端可直接修改订单状态
```javascript
// 危险：客户端传入状态
wx.request({
  url: '/api/order/update',
  data: {
    orderId: orderId,
    status: 'paid'  // ❌ 客户端指定状态
  }
})
```

检查：
- 订单状态是否可由客户端指定？
- 状态跳转是否有服务端验证？
- 关键状态（已支付、已发货）的修改权限

### 5. 支付回调验证

#### 5.1 客户端回调

```javascript
wx.requestPayment({
  success: res => {
    // ❌ 危险：依赖客户端回调确认支付
    wx.request({
      url: '/api/order/confirm',
      data: { orderId: orderId, paid: true }
    })
  }
})
```

**风险**：客户端可伪造 success 回调

#### 5.2 服务端异步通知

检查是否有：
```javascript
// 在订单创建时，应该有 notify_url
{
  "out_trade_no": "ORDER123",
  "notify_url": "https://api.example.com/payment/callback"
}
```

**检查点**：
- 是否依赖客户端 success 回调？
- 是否有服务端异步通知？
- 异步通知是否验证签名？

### 6. 重放和重复支付保护

#### 6.1 订单号生成

```javascript
// 检查订单号生成逻辑
const orderId = generateOrderId()

// 是否有随机性？
// 是否可预测？
// 是否检查重复？
```

#### 6.2 幂等性保护

检查订单接口：
- 相同订单号的重复请求如何处理？
- 已支付订单能否重复支付？
- 是否有防重放 token？

### 7. 金额字段类型检查

#### 7.1 整数 vs 浮点数

```javascript
// 危险：使用浮点数
const price = 19.99
const total = price * quantity  // 可能有精度问题

// 安全：使用分为单位的整数
const priceInCents = 1999
const total = priceInCents * quantity
```

检查：
- 金额是否使用浮点数？
- 是否有精度损失风险？
- 计算是否正确四舍五入？

### 8. 测试用例生成

为每个风险生成测试用例：

```json
{
  "test_case_id": "PAY-TC-001",
  "type": "price_tampering",
  "description": "篡改订单金额测试",
  "steps": [
    {
      "action": "intercept_request",
      "target": "POST /api/order/create",
      "modify": {
        "field": "totalPrice",
        "from": 99.00,
        "to": 0.01
      }
    },
    {
      "action": "check_response",
      "expected": "服务端拒绝或重新计算价格",
      "vulnerable_if": "接受篡改后的价格"
    }
  ]
}
```

### 9. 输出结果

生成 `evidence/payment-findings.json`：

```json
{
  "skill": "payment-audit",
  "scanned_at": "2024-01-01T12:00:00Z",
  "source_dir": "...",
  "payment_flow": {
    "has_payment": true,
    "payment_api": "wx.requestPayment",
    "order_create_api": "/api/order/create",
    "prepay_api": "/api/payment/prepay",
    "callback_handling": {
      "client_callback": true,
      "server_notify": "unknown"
    }
  },
  "findings": [
    {
      "finding_id": "PAY-001",
      "type": "client_price_trust",
      "severity": "CRITICAL",
      "confidence": "HIGH",
      "description": "客户端传入支付金额，服务端未重新计算",
      "location": "pages/checkout/index.js:156",
      "evidence": "totalPrice: this.data.totalPrice",
      "vulnerable_code": "wx.request({\n  url: '/api/order/create',\n  data: {\n    totalPrice: this.data.totalPrice\n  }\n})",
      "impact": "用户可篡改支付金额为 0.01 元",
      "remediation": [
        "只传商品 ID 和数量，由服务端计算价格",
        "如必须传价格，服务端必须重新计算并对比"
      ],
      "test_case": {
        "id": "PAY-TC-001",
        "description": "抓包修改 totalPrice 为 0.01",
        "expected": "服务端拒绝或使用正确价格",
        "vulnerable_if": "接受 0.01 的订单"
      }
    },
    {
      "finding_id": "PAY-002",
      "type": "client_callback_trust",
      "severity": "HIGH",
      "confidence": "MEDIUM",
      "description": "依赖客户端 success 回调确认支付",
      "location": "pages/payment/index.js:88",
      "evidence": "wx.requestPayment({success: confirmOrder})",
      "impact": "用户可伪造 success 回调，不付款获取商品",
      "remediation": [
        "使用服务端异步通知确认支付",
        "客户端回调仅用于 UI 更新，不更改订单状态"
      ]
    },
    {
      "finding_id": "PAY-003",
      "type": "coupon_validation",
      "severity": "MEDIUM",
      "confidence": "LOW",
      "description": "优惠券折扣由客户端计算",
      "location": "pages/checkout/index.js:201",
      "evidence": "discountAmount: coupon.discount",
      "impact": "用户可能篡改折扣金额",
      "remediation": [
        "只传优惠券 ID，服务端验证并计算折扣"
      ]
    }
  ],
  "statistics": {
    "total_findings": 3,
    "by_severity": {
      "CRITICAL": 1,
      "HIGH": 1,
      "MEDIUM": 1
    },
    "by_type": {
      "client_price_trust": 1,
      "client_callback_trust": 1,
      "coupon_validation": 1
    }
  }
}
```

## 检查清单

### 价格安全
- [ ] 价格是否由服务端计算？
- [ ] 客户端传入的价格是否重新验证？
- [ ] 金额使用什么数据类型？（整数/浮点）

### 优惠安全
- [ ] 优惠券/折扣由谁计算？
- [ ] 优惠券是否验证有效期？
- [ ] 优惠券是否防重复使用？
- [ ] 积分/余额抵扣是否验证？

### 订单状态
- [ ] 订单状态能否由客户端指定？
- [ ] 关键状态变更是否有权限控制？
- [ ] 订单号生成是否有随机性？

### 支付回调
- [ ] 是否依赖客户端 success 回调？
- [ ] 是否有服务端异步通知？
- [ ] 异步通知是否验证签名？

### 防重放
- [ ] 订单是否有幂等性保护？
- [ ] 已支付订单能否重复支付？
- [ ] 是否有防重放 token？

## 输出文件

- `evidence/payment-findings.json` - 完整分析结果
- `evidence/payment-test-cases.json` - 测试用例列表（可选）
