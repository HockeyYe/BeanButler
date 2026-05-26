# BeanButler AI 点单助手 Day 6 开发记录

## 1. 完成日期

2026-05-26

## 2. 本次完成内容

- 新增小程序页面 `pages/ai-order/ai-order`，含 wxml/wxss/js/json 四件套。
- `frontend/app.json` 注册新页面，并将 `pages/index/index` 移至 pages 数组首位确保首页正确。
- AI 点单入口集成到点单页 `menu` 页面顶部，使用 `wx.navigateTo` 跳转。
- 页面包含多行输入框 + 发送按钮，支持 200 字自然语言输入。
- 快捷需求 Chip：提供 3 个预设输入示例（冰的/热的手冲/花果香），点击自动填充。
- Loading 状态：发送后展示"正在分析你的口味..."动画，按钮置灰防重复提交。
- 调用 `POST /api/ai/order-assistant/`，传入 `user_input` 和 `user_id`。
- AI 推荐结果展示为推荐卡片列表：商品图片、名称、价格、推荐理由、规格建议标签。
- 通过 `GET /api/products/` 补齐推荐商品的完整价格和图片信息。
- options 中 `temperature/sugar/milk` 转换为中文标签展示（如 冰/少糖/燕麦奶）。
- 未登录弹窗引导登录，支持 `LOGIN_REQUIRED` 响应二次兜底。
- AI 异常 / 无推荐 / `OUT_OF_SCOPE` 展示友好 fallback 提示。
- 预留"选择规格"按钮样式，Day 6 不绑定加购逻辑，留待 Day 8。
- 自定义 NavigationBar 适配状态栏高度。
- 编写 Day 6 PRD（`AI_Coffee_Day6_PRD.md`）。
- 编写 Day 6 交互原型 HTML（`day6-ai-order-prototype.html`）。
- 验收后修复：
  - `app.json` pages 数组顺序修正（index 置首）。
  - `checkLogin` 使用 `userInfo.member_id` 替代不存在的 `userInfo.id`。
  - `ai-order` 页面 `goBack()` 增加 `wx.switchTab` 兜底。
  - 清理 `menu` 页面旧 AI 推荐区域（ai-rec-section）及对应 JS/样式。

## 3. 涉及文件

前端：

- `frontend/pages/ai-order/ai-order.wxml`
- `frontend/pages/ai-order/ai-order.wxss`
- `frontend/pages/ai-order/ai-order.js`
- `frontend/pages/ai-order/ai-order.json`
- `frontend/pages/menu/menu.wxml`（新增 AI 入口；移除旧 ai-rec-section）
- `frontend/pages/menu/menu.js`（移除 fetchRecommendations；checkLogin 修正）
- `frontend/pages/menu/menu.wxss`（移除 ai-rec-* 样式）
- `frontend/app.json`（注册 ai-order 页面；调整 pages 顺序）

产品/记录：

- `docs/requirements/AI_Coffee_Day6_PRD.md`
- `docs/prototypes/day6-ai-order-prototype.html`
- `docs/requirements/AI_Coffee_Project_3Week_TODO.md`

## 4. 页面结构说明

### 4.1 页面路径

```text
pages/ai-order/ai-order
```

入口：点单页 `menu` 页面顶部 AI 入口卡片 → `wx.navigateTo`。

### 4.2 页面模块

| 模块 | 说明 |
|------|------|
| 自定义 NavigationBar | 适配状态栏高度，返回按钮 + 标题"AI 帮我点" |
| 顶部说明区 | 标题"告诉 AI 你想喝什么"，副标题描述能力范围 |
| 输入区 | 多行 textarea，200 字上限，placeholder 引导 |
| 快捷 Chip | 3 个预设文本标签，点击填充输入框 |
| 发送按钮 | "让 AI 推荐"，loading 期间禁用 |
| Loading 区 | 旋转动画 + "正在分析你的口味..." |
| 推荐结果区 | 1-3 张推荐卡片，含图片/名称/价格/理由/规格标签 |
| 错误/兜底区 | 友好图标 + 文案 + 重试按钮 |

### 4.3 交互流程

```text
用户进入页面
  → 输入口味需求（或点击快捷 Chip）
  → 点击"让 AI 推荐"
  → 展示 loading
  → 调用 /api/ai/order-assistant/
  → 成功：展示推荐卡片列表
  → 失败/无结果：展示兜底提示 + 重试按钮
```

### 4.4 非本日范围

- 推荐卡片不接入购物车（Day 8）。
- 不做多轮对话（Day 12）。
- 不做快捷需求按钮专区（Day 9）。

## 5. 遗留问题

- 消息订阅通知函数 `subscribeMsg` 未定义，需 Day 7 清理。
- `wx.request` 在真机预览存在 TLS/证书兼容性问题，需检查后端 HTTPS 配置。
- 输入框聚焦后页面可能滚动错乱，已通过 `adjust-position` 优化。
- menu 页旧 AI 推荐区域已完全清理，功能迁移至独立 ai-order 页面。

## 6. 明日计划

Day 7 第一周收尾：
- 修复 Week 1 主要 bug。
- 整理 AI 点单相关代码。
- README 初版：项目介绍、启动方式、当前进度。
- 完成一页轻量竞品分析初稿。
- 记录接口请求示例。