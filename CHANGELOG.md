# 更新日志

本项目所有重要变更均会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/spec/v2.0.0.html)。

---

## [未发布]

### 新增
- 新增 `ai_assistant` Django app。
- 新增 `POST /api/ai/order-assistant/` AI 智能点单接口。
- 接入 DeepSeek `deepseek-v4-flash`，API Key 从后端 `.env` / 环境变量读取。
- 新增 AI 点单 Prompt、JSON 解析、真实商品 `product_id` 校验和 fallback 推荐逻辑。
- 菜单页新增最小 AI 点单接口测试入口。
- 新增 `AI_Order_Assistant_Day3-5_PRD.md` 和 `AI_Order_Assistant_Day3-5_Dev_Record.md`，记录需求、接口和测试结果。

### 变更
- `.env.example` 增加 DeepSeek 相关环境变量占位配置。
- README 增加 AI 点单接口说明和环境变量说明。

### 验证
- 已通过小程序菜单页测试入口成功调用 AI 接口。
- 已确认真实 API Key 只写入本地 `.env`，未进入 Git 状态。

## [0.1.0] - 2026-05-24

### 新增
- 新增 `CHANGELOG.md`，用于系统性地记录项目变更。
- 新增 `.env.example` 模板，列出所有必需的环境变量。
- 新增 migration `0008_alter_member_options`，用于 members 模型。

### 变更
- 前端 API 模式从云托管（`wx.cloud.callContainer`）切换为本地 Django（`wx.request` → `http://127.0.0.1:8000`）。
- 重构 `mysite/settings.py`，通过 `python-dotenv` 从 `.env` 文件读取所有配置项。
- `members/views.py` 中 `WECHAT_APP_ID` 和 `WECHAT_APP_SECRET` 从硬编码改为 `os.getenv()` 读取。

### 修复
- 修复迁移到本地 Django 后微信登录返回 `"invalid code"` 的问题。原因为硬编码的 AppID 与小程序实际的 AppID（`wx84347eb28e2473c4`）不一致，导致 `jscode2session` 拒绝授权码。
