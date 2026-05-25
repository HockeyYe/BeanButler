# BeanButler 咖啡点单系统

BeanButler 是一个面向咖啡店场景的点单与后台管理系统，包含微信小程序前端和 Django 后端。项目支持商品浏览、购物车、会员登录、下单、优惠券、反馈留言、后台订单处理、库存维护、会员管理、数据看板和推荐功能。

## 项目结构

```text
.
├── frontend/                    # 微信小程序前端
│   ├── pages/                   # 小程序页面
│   ├── custom-tab-bar/          # 自定义底部导航
│   ├── images/                  # 前端静态图片
│   └── utils/                   # 请求封装与工具函数
│
├── backend/backend_fixed/        # Django 后端
│   ├── mysite/                  # Django 项目配置
│   ├── demo_orders/             # 商品、订单、订单项、推荐相关逻辑
│   ├── members/                 # 会员与微信登录
│   ├── coupons/                 # 优惠券
│   ├── feedback/                # 用户反馈
│   ├── staff/                   # 员工与排班
│   ├── analytics/               # 后台数据看板
│   ├── templates/               # 后台自定义页面模板
│   ├── requirements.txt         # Python 依赖
│   └── .env.example             # 本地环境变量示例
│
├── docs/
│   ├── requirements/            # PRD、TODO 与需求规划文档
│   └── dev-records/             # 阶段开发记录、接口记录与测试记录
│
├── .gitignore                   # Git 忽略规则
├── .gitattributes               # Git 文件类型与换行规则
└── CLEANUP_STEPS.md             # 项目清理与本地重建说明
```

## 技术栈

前端：

- 微信小程序原生开发
- `wx.request`
- `wx.cloud.callContainer`

后端：

- Python 3.11
- Django 4.2
- Django REST Framework
- MySQL
- Django SimpleUI
- WhiteNoise
- Gunicorn
- Pandas / NumPy / scikit-learn

## 主要功能

- 商品菜单展示与分类浏览
- 商品规格选择，例如温度、甜度、咖啡豆
- 购物车与结算
- 微信小程序登录
- 会员资料维护
- 会员等级、积分与优惠券
- 订单创建与订单历史
- 后台订单工作台
- 商品、库存、会员、反馈、优惠券后台管理
- 销售数据看板
- 基于历史订单的推荐功能
- AI 智能点单接口：支持自然语言需求、DeepSeek 调用、结构化 JSON 推荐、真实商品 `product_id` 校验和 fallback 推荐

## AI 点单接口

当前已新增 AI 点单后端接口：

```text
POST /api/ai/order-assistant/
```

请求示例：

```json
{
  "user_input": "我想喝冰的、低糖、不要牛奶的咖啡",
  "user_id": 1
}
```

返回结构统一为：

```json
{
  "success": true,
  "data": {
    "intent": "recommend_drink",
    "recommendations": [],
    "follow_up_question": "",
    "is_fallback": false
  },
  "message": "推荐成功",
  "error_code": null
}
```

说明：

- AI 服务商：DeepSeek。
- 默认模型：`deepseek-v4-flash`。
- API Key 只从后端环境变量读取。
- AI 推荐必须匹配真实可售商品 `product_id`。
- AI 超时、非法 JSON 或推荐商品不匹配时，会返回基于历史数据和当前商品销售热度的 fallback 推荐。

## 本地运行后端

进入后端目录：

```powershell
cd C:\Users\86177\Desktop\Fullstack\backend\backend_fixed
```

创建虚拟环境：

```powershell
py -3.11 -m venv venv
```

安装依赖：

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

创建本地环境变量文件：

```powershell
Copy-Item .env.example .env
```

然后编辑 `.env`，填写本地 MySQL 密码、Django 密钥和微信小程序配置。

执行数据库迁移：

```powershell
.\venv\Scripts\python.exe manage.py migrate
```

启动后端服务：

```powershell
.\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

后台地址：

```text
http://127.0.0.1:8000/admin/
```

## 本地运行小程序前端

1. 使用微信开发者工具打开 `frontend/` 目录。
2. 根据本地或云端环境修改 `frontend/utils/api.js` 中的 `ENV`。
3. 如果使用本地后端，确认 `LOCAL_BASE_URL` 指向当前电脑的局域网 IP，例如：

```javascript
const LOCAL_BASE_URL = 'http://192.168.x.x:8000';
```

4. 在微信开发者工具中勾选“不校验合法域名、web-view、TLS 版本以及 HTTPS 证书”。
5. 启动 Django 后端后，在小程序中测试登录、菜单、购物车和下单流程。

## 环境变量说明

后端本地环境变量参考 `backend/backend_fixed/.env.example`：

```text
DJANGO_DEBUG=True
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=bean_butler
DB_USER=root
DB_PASSWORD=change_me
DJANGO_SECRET_KEY=change_me
WECHAT_APP_ID=change_me
WECHAT_APP_SECRET=change_me
DEEPSEEK_API_KEY=change_me
DEEPSEEK_API_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_TIMEOUT_SECONDS=20
```

注意：真实 `.env` 不应提交到 GitHub。

## Git 管理说明

本项目已经清理并排除了以下不应进入仓库的内容：

- 虚拟环境 `venv/`
- 本地环境变量 `.env`
- 本地数据库 `db.sqlite3`
- 数据导出文件 `data.json`、`data_backup.json`
- 上传媒体目录 `media/`
- Python 缓存 `__pycache__/`
- zip 备份文件
- 系统临时文件 `.DS_Store`、`__MACOSX/`

如需恢复本地数据或上传文件，请从项目外部的手动备份中恢复。

## 后续优化建议

- 将后端密钥、数据库配置、微信配置全部从源码中迁移到环境变量。
- 为下单、优惠券、积分等核心流程增加事务控制。
- 使用 DRF Serializer 统一 API 参数校验和返回结构。
- 补充接口测试，避免前后端接口不一致。
- 将业务逻辑从 `views.py` 和 `admin.py` 中逐步抽离到 service 层。
