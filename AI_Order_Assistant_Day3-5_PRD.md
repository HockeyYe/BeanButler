# BeanButler AI 智能点单助手 Day 3-5 需求文档

## 1. 文档背景

BeanButler 当前已经具备微信原生小程序点单、商品浏览、购物车、结算、订单查询、会员、优惠券和后台管理能力。本阶段目标是在不破坏原有点单链路的前提下，新增 AI 智能点单助手后端接口，让用户可以用自然语言描述需求，由系统基于真实商品菜单返回可加购的推荐商品。

本文档覆盖三周计划中的 Day 3-5：

- Day 3：新建 AI 模块与 mock 接口。
- Day 4：Django 后端接入 DeepSeek API。
- Day 5：控制 AI 返回结构化 JSON，完成 `product_id` 校验与异常兜底。

本阶段先完成“后端接口可用 + 最小前端测试入口”，正式 AI 点单页面和推荐卡片展示放到 Day 6。

## 2. 产品目标

### 2.1 一句话目标

让已登录用户输入一句自然语言点单需求后，系统能够基于真实菜单推荐 1-3 个可购买商品，并返回前端可直接展示和后续加购的数据结构。

### 2.2 用户价值

- 降低新用户选择成本：用户不需要逐个浏览菜单，可以直接说出“冰的、低糖、不要牛奶、预算 20 内”等需求。
- 提高点单体验的智能感：AI 不只是聊天，而是能连接真实商品和后续购物车流程。
- 为后续加购闭环打基础：推荐结果必须带真实 `product_id`，方便 Day 8 复用购物车能力。

### 2.3 业务价值

- 从普通点单系统升级为 AI 咖啡点单系统。
- 形成面试/毕设可讲述的技术亮点：Prompt 约束、结构化 JSON、真实商品匹配、fallback。
- 为后续咖啡知识助手、萃取参数建议和个性化推荐打基础。

## 3. 范围说明

### 3.1 本阶段要做

- 新增 Django app：`ai_assistant`。
- 新增后端接口：`POST /api/ai/order-assistant/`。
- 接口第一版返回 mock JSON。
- 接口支持接收 `user_input` 和 `user_id`。
- 后端读取真实可售商品菜单。
- 后端调用 DeepSeek `deepseek-v4-flash`。
- Prompt 要求 AI 只能基于给定商品菜单推荐。
- AI 返回固定 JSON。
- 后端解析 JSON。
- 后端校验推荐结果中的 `product_id` 是否存在且可售。
- AI 异常、超时、非法 JSON、无关输入、商品为空时返回统一 fallback。
- 小程序增加最小前端测试入口，用于请求接口并打印返回结果。

### 3.2 本阶段暂不做

- 不新增完整 AI 点单页面，正式页面放到 Day 6。
- 不实现推荐商品加入购物车，购物车闭环放到 Day 8。
- 不做多轮对话记忆。
- 不基于历史订单做个性化推荐。
- 不接咖啡知识问答和萃取参数建议。
- 不做后台 Prompt 配置页面。
- 不做向量检索或 RAG。

## 4. 用户与权限

### 4.1 使用用户

本接口面向已登录的普通用户。

### 4.2 登录要求

AI 点单接口要求传入 `user_id`。原因：

- BeanButler 的真实点单流程默认需要登录后才能结算和下单。
- 本阶段提前保持 AI 点单与真实业务流程一致。
- 后续可以自然扩展到会员历史订单、积分、优惠券和个性化推荐。

### 4.3 未登录处理

如果请求未传 `user_id` 或 `user_id` 不存在，接口不调用 AI，直接返回统一错误格式。

后端建议返回：

```json
{
  "success": false,
  "data": {
    "intent": "login_required",
    "recommendations": [],
    "follow_up_question": "请先登录后再使用 AI 点单助手。"
  },
  "message": "请先登录",
  "error_code": "LOGIN_REQUIRED"
}
```

前端收到 `LOGIN_REQUIRED` 后，跳转到已有登录页面。实现时应复用当前项目中结算、点单等场景已有的登录判断和跳转方式，保持体验一致。

## 5. 核心用户流程

1. 用户已登录小程序。
2. 用户在最小测试入口输入点单需求。
3. 小程序调用 `POST /api/ai/order-assistant/`。
4. 后端校验 `user_id` 和 `user_input`。
5. 后端读取当前可售商品菜单。
6. 后端将用户需求和菜单数据拼接为 Prompt。
7. 后端调用 DeepSeek。
8. DeepSeek 返回结构化 JSON。
9. 后端解析 JSON，并校验推荐商品是否存在。
10. 后端返回统一格式给小程序。
11. 小程序打印接口返回结果。

## 6. 接口设计

### 6.1 接口信息

| 项目 | 内容 |
| --- | --- |
| 方法 | `POST` |
| 路径 | `/api/ai/order-assistant/` |
| 内容类型 | `application/json` |
| 是否需要登录态 | 需要传 `user_id` |
| 是否直接请求 AI | 只允许后端请求 DeepSeek，小程序不直接请求 AI |

### 6.2 Request

```json
{
  "user_input": "我想喝一杯冰的、低糖、不要牛奶的咖啡",
  "user_id": 1
}
```

### 6.3 Request 字段说明

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `user_input` | string | 是 | 用户自然语言点单需求 |
| `user_id` | number/string | 是 | 当前登录会员 ID |

### 6.4 Success Response

```json
{
  "success": true,
  "data": {
    "intent": "recommend_drink",
    "recommendations": [
      {
        "product_id": 12,
        "product_name": "冰美式",
        "reason": "符合冰饮、低糖、无奶需求，口感清爽，适合想要低负担咖啡的用户。",
        "options": {
          "temperature": "ICE",
          "sugar": "LESS",
          "milk": "none"
        }
      }
    ],
    "follow_up_question": ""
  },
  "message": "推荐成功",
  "error_code": null
}
```

### 6.5 Response 字段说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `success` | boolean | 本次接口是否成功返回可处理结果 |
| `data.intent` | string | 用户意图识别结果 |
| `data.recommendations` | array | 推荐商品列表，最多 3 个 |
| `product_id` | number | 真实商品 ID，必须存在于商品表且可售 |
| `product_name` | string | 商品名称，建议以后端商品表为准 |
| `reason` | string | 推荐理由，面向用户展示 |
| `options.temperature` | string | 推荐温度/冰量选项 |
| `options.sugar` | string | 推荐甜度选项 |
| `options.milk` | string | 奶源或是否含奶，当前作为 AI 建议字段 |
| `follow_up_question` | string | 当信息不足时，AI 给用户的追问 |
| `message` | string | 接口提示文案 |
| `error_code` | string/null | 错误码，成功时为 null |

## 7. 关于 options 字段的产品解释

当前商品模型中，温度和甜度不是中文文案，而是数据库枚举值。例如：

- 温度/冰量：`HOT`、`ICE`、`LESS_ICE`、`NO_ICE`
- 甜度：`NORMAL`、`MORE`、`LESS`、`NONE`

因此，AI 接口建议优先返回枚举值，而不是直接返回“冰的”“少糖”。这样后续加入购物车时，前端可以更稳定地复用现有规格逻辑。

产品层面可以理解为：

- 给用户看的文案：冰饮、少糖。
- 给系统处理的数据：`ICE`、`LESS`。

第一版只要求温度和甜度尽量匹配现有枚举；`milk` 暂时作为 AI 建议字段，不强依赖当前商品模型。

## 8. AI 推荐商品匹配策略

本阶段采用“AI 从真实菜单中选择商品 ID”的方案。

后端会把真实菜单整理给 DeepSeek，例如：

```json
[
  {
    "product_id": 12,
    "product_name": "冰美式",
    "category": "ESPRESSO",
    "price": 18,
    "description": "清爽低负担的经典咖啡",
    "available_temps": ["ICE", "LESS_ICE"],
    "available_sugars": ["LESS", "NONE"]
  }
]
```

Prompt 要求 AI 只能从这些商品中选择，不能编造新商品。

采用该方案的原因：

- 推荐结果能直接进入后续购物车流程。
- 避免 AI 返回“拿铁特调 Plus”等数据库不存在的商品。
- 后端可以用 `product_id` 做强校验。

如果 AI 返回的 `product_id` 不存在、不可售或不在菜单上下文中，后端会过滤该推荐；如果过滤后没有可用推荐，则返回 fallback。

## 9. AI 服务配置

### 9.1 服务商

本阶段接入 DeepSeek。

### 9.2 模型

默认模型：

```text
deepseek-v4-flash
```

### 9.3 环境变量

建议新增：

```env
DEEPSEEK_API_KEY=change_me
DEEPSEEK_API_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_TIMEOUT_SECONDS=20
```

### 9.4 安全要求

- DeepSeek API Key 只允许放在后端环境变量或 `.env` 中。
- 不允许写死在代码里。
- 不允许出现在小程序前端。
- `.env.example` 只写占位值，不写真实密钥。

## 10. Prompt 设计要求

### 10.1 角色

AI 是 BeanButler 的咖啡点单助手，负责根据用户口味、温度、甜度、预算和是否含奶等需求，从真实菜单中推荐商品。

### 10.2 任务

- 理解用户自然语言点单需求。
- 判断是否属于咖啡、饮品、菜单或点单相关需求。
- 从给定菜单中选择 1-3 个最合适商品。
- 输出固定 JSON。

### 10.3 约束

- 只能推荐菜单中存在的商品。
- 必须返回真实 `product_id`。
- 不允许编造商品、价格或规格。
- 如果用户输入与点单无关，返回 `out_of_scope`。
- 如果信息不足，可以返回追问。
- 输出必须是合法 JSON，不要附加 Markdown、解释文字或代码块。

### 10.4 推荐输出意图

| intent | 说明 |
| --- | --- |
| `recommend_drink` | 正常饮品推荐 |
| `need_more_info` | 用户需求不足，需要追问 |
| `out_of_scope` | 用户输入与咖啡、饮品、菜单、点单无关 |
| `menu_unavailable` | 当前菜单为空或无可售商品 |

## 11. 异常与兜底策略

### 11.0 fallback 推荐定义

fallback 推荐指的是：当 AI 不能稳定产出可用推荐时，系统不直接报错，而是由后端基于现有商品数据给用户返回一组保底推荐。

它不只发生在“AI 无法理解用户需求”时，也包括以下情况：

- DeepSeek 调用超时或失败。
- AI 返回内容不是合法 JSON。
- AI 推荐了数据库中不存在的商品。
- AI 推荐了已下架或不可售商品。
- AI 返回空推荐。
- 用户输入过于模糊，AI 无法判断具体偏好。

产品目标是保证用户不会看到系统崩溃或空白页面，而是至少得到一个友好的解释和可继续操作的结果。

本项目的 fallback 推荐优先复用当前系统已有的 3 个推荐商品逻辑：先尝试基于会员历史订单的推荐结果；如果没有会员推荐结果，则回退到当前商品销售热度或全局热门商品。前端展示时需要注明该推荐不是本次 AI 精准理解后的结果，而是“根据历史数据和当前商品销售热度综合推荐”。

### 11.1 用户未登录

不调用 DeepSeek，返回 `LOGIN_REQUIRED`。

### 11.2 用户输入为空

不调用 DeepSeek，返回 `INVALID_INPUT`。

建议文案：

```text
请告诉我你想喝什么，比如冰的、低糖、提神、不要牛奶或预算范围。
```

### 11.3 用户输入无关内容

返回 `out_of_scope`，不推荐商品。

建议文案：

```text
我主要负责咖啡和饮品点单，可以告诉我你的口味、温度、甜度或预算。
```

### 11.4 商品菜单为空

不调用 DeepSeek，返回 `MENU_EMPTY`。

建议文案：

```text
当前暂无可推荐商品，请稍后再试。
```

### 11.5 DeepSeek 超时或调用失败

返回 fallback，不让接口 500。

兜底推荐优先级：

1. 当前已有 `/api/recommendations/` 的推荐逻辑：会员历史订单推荐优先。
2. 如果会员没有推荐结果，则使用全局热门商品。
3. 如果推荐逻辑仍无结果，则使用 `is_recommended=True` 的可售商品。
4. 如果仍然没有商品，返回空推荐和友好提示。

fallback 推荐文案建议：

```text
AI 暂时没有生成稳定推荐，以下是根据历史数据和当前商品销售热度为你综合推荐的饮品。
```

### 11.6 AI 返回非法 JSON

后端捕获解析异常，返回 fallback。

### 11.7 AI 推荐不存在的商品

后端过滤不存在或不可售的 `product_id`。如果过滤后为空，返回 fallback。

## 12. 错误码建议

| error_code | 说明 |
| --- | --- |
| `LOGIN_REQUIRED` | 用户未登录或 `user_id` 无效 |
| `INVALID_INPUT` | 用户输入为空或格式错误 |
| `MENU_EMPTY` | 当前无可售商品 |
| `OUT_OF_SCOPE` | 用户输入与点单无关 |
| `AI_TIMEOUT` | AI 调用超时 |
| `AI_SERVICE_ERROR` | AI 服务调用失败 |
| `AI_INVALID_JSON` | AI 返回不是合法 JSON |
| `AI_PRODUCT_MISMATCH` | AI 推荐商品无法匹配真实商品 |

说明：即使出现 AI 异常，接口仍应尽量返回 HTTP 200 和统一 JSON，让小程序可以稳定处理。只有请求方法错误等明显协议问题才返回 4xx。

## 13. 最小前端测试入口

### 13.1 目标

让小程序可以快速验证接口是否打通，不做完整产品页面。

### 13.2 建议方式

在菜单页增加一个开发测试入口，原因是菜单页已经承载商品列表、推荐商品和加入购物车上下文，最贴近 AI 点单后续正式页面的业务场景。

- 在菜单页临时增加一个“AI 测试”按钮。
- 点击后使用固定测试文案请求接口。
- 在控制台打印返回结果。
- 可选：用 `wx.showToast` 或 `wx.showModal` 展示接口是否成功。

### 13.3 测试请求示例

```js
api.request('/api/ai/order-assistant/', 'POST', {
  user_input: '我想喝冰的、低糖、不要牛奶的咖啡',
  user_id: app.globalData.userInfo.id
})
```

## 14. 验收标准

### 14.1 Day 3 验收

- Django 中存在 `ai_assistant` app。
- `INSTALLED_APPS` 已配置。
- `POST /api/ai/order-assistant/` 可访问。
- 接口可返回统一格式 mock JSON。
- 小程序最小测试入口可以请求该接口并打印结果。
- 无 404 / 500。

### 14.2 Day 4 验收

- 后端从环境变量读取 DeepSeek API Key。
- 后端封装 DeepSeek 调用 service。
- 接口接收 `user_input` 和 `user_id`。
- 后端能读取真实商品菜单。
- 后端能拼接 Prompt 并调用 DeepSeek。
- API Key 没有写死在代码里。

### 14.3 Day 5 验收

- AI 返回结果为固定 JSON。
- 后端可以解析 AI JSON。
- 推荐商品的 `product_id` 能匹配真实可售商品。
- AI 返回非法 JSON 时接口不崩溃。
- DeepSeek 超时或失败时接口不 500。
- 用户未登录、输入为空、菜单为空、无关输入都有友好响应。

## 15. 后续衔接

### 15.1 Day 6

基于该接口新增正式 AI 点单页面，展示输入框、loading 状态和推荐商品卡片。

### 15.2 Day 8

推荐卡片使用 `product_id` 和 `options` 接入现有购物车流程。

### 15.3 Day 10

进一步完善日志、安全边界和异常观测。

## 16. 对话记录与后续运营分析规划

### 16.1 产品判断

用户与 AI 点单助手的对话记录具备长期价值，可以用于分析用户真实需求，并反向指导菜单设计、商品研发和商业策略调整。

但该能力不应作为 Day 3-5 的完整交付目标。当前阶段更重要的是先跑通 AI 点单接口、真实商品匹配和异常兜底。完整对话分析系统会扩大范围，涉及数据表设计、隐私说明、脱敏、后台分析页面和统计口径，适合后续迭代。

### 16.2 当前阶段建议

Day 3-5 只做基础接口日志或预留日志能力，用于调试和复盘。

建议记录：

- `user_id`
- `user_input`
- `intent`
- 推荐出的 `product_id` 列表
- 是否调用 AI 成功
- 是否触发 fallback
- 错误类型
- 创建时间

当前不要求：

- 不做完整对话历史页面。
- 不做 NLP 分析报表。
- 不做商业策略看板。
- 不把用户对话作为个性化推荐依据。

### 16.3 后续迭代价值

后续可以基于对话记录做轻量 NLP 和运营分析，例如：

- 高频需求分析：低糖、冰饮、提神、无奶、预算 20 内等。
- 菜单缺口分析：用户常问但当前菜单没有的商品或规格。
- 商品研发方向：燕麦奶、低咖啡因、低糖特调、季节限定等需求是否值得加入。
- 推荐转化分析：AI 推荐后用户是否点击、加购、下单。
- 用户偏好沉淀：为后续个性化推荐提供数据基础。

### 16.4 建议后续数据表方向

后续可新增 `AIAssistantLog` 或类似模型，用于记录 AI 请求和结果。

建议字段：

| 字段 | 说明 |
| --- | --- |
| `user_id` | 用户 ID |
| `user_input` | 用户原始输入 |
| `intent` | AI 识别意图 |
| `recommended_product_ids` | 推荐商品 ID 列表 |
| `is_fallback` | 是否触发兜底推荐 |
| `error_code` | 错误码 |
| `ai_model` | 调用模型 |
| `latency_ms` | 响应耗时 |
| `created_at` | 创建时间 |
