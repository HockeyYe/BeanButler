# Backend 本地開發指南（MySQL + 微信小程序）

## 第一步：填 MySQL 密碼

編輯 `.env`，把 `你的MySQL密碼` 換成你本機 MySQL 的 root 密碼：

```
DB_PASSWORD=your_actual_password
```

資料庫 `bean_butler` 會自動建立，不用手動 CREATE。

## 第二步：啟動

```bash
cd backend_v1
bash start.sh
```

腳本會自動：建 venv → 裝套件 → 測試 MySQL 連線 → migrate → 建 superuser → 啟動

## Admin 後台

http://127.0.0.1:8000/admin  
帳號：`Hockey` / 密碼：`yhq20030914`

## 微信小程序對接

1. 把小程序裡的 API base URL 改成你 Mac 的**區網 IP**（不是 localhost）：
   ```
   http://192.168.x.x:8000
   ```
   （System Preferences → Network → 看 Wi-Fi IP）

2. 微信開發工具 → **詳情** → **本地設定** → 勾選「不校驗合法域名、web-view...」

## 與雲端的差異

| | 本地 | 雲端 (騰訊雲) |
|--|------|-------------|
| 資料庫 | 本地 MySQL (127.0.0.1) | 雲端 MySQL (DB_HOST env) |
| 伺服器 | `runserver 0.0.0.0:8000` | gunicorn port 80 |
| Static | 預設 Django storage | WhiteNoise compressed |
| Debug | True | False |
