# BeanButler AI 点单助手 Day 3-5 开发记录

## 1. 完成日期

2026-05-25

## 2. 本次完成内容

- 新增 Django app：`ai_assistant`。
- 新增接口：`POST /api/ai/order-assistant/`。
- 接入 DeepSeek `deepseek-v4-flash`。
- DeepSeek API Key 从后端 `.env` 读取，不进入小程序前端。
- 后端读取真实可售商品菜单，并将用户输入和菜单数据拼接为 Prompt。
- Prompt 约束 AI 只能从真实菜单中选择商品，且必须返回 JSON。
- 后端解析 AI JSON，校验 `recommendations` 中的 `product_id` 是否存在且可售。
- AI 异常时返回 fallback，避免接口 500。
- 菜单页增加最小测试入口，用于请求接口并打印返回结果。

## 3. 涉及文件

后端：

- `backend/backend_fixed/ai_assistant/apps.py`
- `backend/backend_fixed/ai_assistant/services.py`
- `backend/backend_fixed/ai_assistant/views.py`
- `backend/backend_fixed/mysite/settings.py`
- `backend/backend_fixed/mysite/urls.py`
- `backend/backend_fixed/.env.example`

前端：

- `frontend/pages/menu/menu.js`
- `frontend/pages/menu/menu.wxml`
- `frontend/pages/menu/menu.wxss`

产品/记录：

- `AI_Order_Assistant_Day3-5_PRD.md`
- `AI_Coffee_Project_3Week_TODO.md`

## 4. 接口说明

### 4.1 Request

```http
POST /api/ai/order-assistant/
Content-Type: application/json
```

```json
{
  "user_input": "我想喝冰的、低糖、不要牛奶的咖啡",
  "user_id": 1
}
```

### 4.2 Success Response

```json
{
  "success": true,
  "data": {
    "intent": "recommend_drink",
    "recommendations": [
      {
        "product_id": 12,
        "product_name": "冰美式",
        "reason": "符合冰饮、低糖、无奶需求，口感清爽。",
        "options": {
          "temperature": "ICE",
          "sugar": "LESS",
          "milk": "none"
        }
      }
    ],
    "follow_up_question": "",
    "is_fallback": false
  },
  "message": "推荐成功",
  "error_code": null
}
```

### 4.3 Login Required Response

```json
{
  "success": false,
  "data": {
    "intent": "login_required",
    "recommendations": [],
    "follow_up_question": "请先登录后再使用 AI 点单助手。"
  },
  "message": "请先登录后再使用 AI 点单助手。",
  "error_code": "LOGIN_REQUIRED"
}
```

### 4.4 Fallback Response

```json
{
  "success": true,
  "data": {
    "intent": "fallback_recommendation",
    "recommendations": [],
    "follow_up_question": "",
    "is_fallback": true,
    "fallback_reason": "AI_SERVICE_ERROR"
  },
  "message": "AI 暂时没有生成稳定推荐，以下是根据历史数据和当前商品销售热度为你综合推荐的饮品。",
  "error_code": null
}
```

## 5. 环境变量

真实配置放在后端本地 `.env`，不要提交到 Git。

```env
DEEPSEEK_API_KEY=change_me
DEEPSEEK_API_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_TIMEOUT_SECONDS=20
```

## 6. fallback 规则

当 DeepSeek 未配置、调用失败、超时、返回非法 JSON、返回空推荐或推荐了不存在商品时，接口不直接 500，而是返回 fallback。

fallback 推荐优先级：

1. 会员已有推荐结果。
2. 全局热门商品。
3. 后台标记为 `is_recommended=True` 的可售商品。
4. 任意可售商品。

fallback 文案：

```text
AI 暂时没有生成稳定推荐，以下是根据历史数据和当前商品销售热度为你综合推荐的饮品。
```

## 7. 测试记录

已验证：

- Django 后端和 MySQL 手动启动后，AI 接口可访问。
- 小程序菜单页测试入口可以请求接口。
- 未登录时前端会跳转登录页。
- 配置 DeepSeek API Key 后，可以成功调用 AI 接口。
- AI 返回结果可以被后端解析并转换为统一响应结构。
- 真实 API Key 只写入本地 `.env`，未进入 Git 状态。

代码级验证：

- `python -m compileall ai_assistant mysite` 已通过。

未完成验证：

- `manage.py check` 未在 Codex 环境中完成，因为当前虚拟环境缺少 Django，安装完整依赖时网络下载超时。用户手动启动 Django 后已完成实际功能测试。

## 8. 当前限制

- 菜单页只是最小测试入口，不是正式 AI 点单页面。
- AI 推荐结果暂时不能直接加入购物车。
- 目前没有保存完整对话历史，只保留日志规划。
- `milk` 当前只是 AI 建议字段，不是商品规格模型字段。

## 9. 下一步建议

进入 Day 6：

- 新增 `pages/ai-order/ai-order` 页面。
- 页面包含输入框、发送按钮、loading 状态。
- 展示推荐商品卡片、推荐理由、规格建议。
- 展示 fallback 提示。
- 未登录时跳转登录页。

