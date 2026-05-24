#!/bin/bash
# 本地開發啟動腳本（MySQL + 微信小程序）

set -e

# 載入 .env
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✅ 已載入 .env"
else
    echo "❌ 找不到 .env！請先複製並填好密碼："
    echo "   cp .env .env（已存在，直接編輯）"
    exit 1
fi

# 確認 venv
if [ ! -d "venv" ]; then
    echo "🔧 建立虛擬環境..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "📦 安裝套件..."
pip install -r requirements.txt -q

# 確認 MySQL 可連線
echo "🔌 測試 MySQL 連線..."
python3 -c "
import pymysql, os
try:
    conn = pymysql.connect(
        host=os.getenv('DB_HOST','127.0.0.1'),
        port=int(os.getenv('DB_PORT','3306')),
        user=os.getenv('DB_USER','root'),
        password=os.getenv('DB_PASSWORD',''),
    )
    # 建立資料庫（如果不存在）
    db_name = os.getenv('DB_NAME','bean_butler')
    conn.cursor().execute(f'CREATE DATABASE IF NOT EXISTS \`{db_name}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;')
    conn.commit()
    conn.close()
    print(f'✅ MySQL 連線成功，資料庫 [{db_name}] 已確認')
except Exception as e:
    print(f'❌ MySQL 連線失敗：{e}')
    print('   請確認 .env 裡的 DB_PASSWORD 是否正確，以及 MySQL 是否已啟動')
    exit(1)
"

echo "🗄️  執行 migration..."
python3 manage.py migrate

# 建立 superuser
echo "👤 確認 superuser..."
python3 manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='Hockey').exists():
    User.objects.create_superuser('Hockey', 'hockey@example.com', 'yhq20030914')
    print('Superuser 建立完成')
else:
    print('Superuser 已存在')
"

echo ""
echo "⏰  設定每日 12:00 自動跑推薦模型..."
# Write crontab entry (idempotent — won't duplicate if already set)
CRON_JOB="0 12 * * * cd $(pwd) && source venv/bin/activate && python manage.py run_cf_recommender --trigger scheduled >> logs/recommender.log 2>&1"
mkdir -p logs
( crontab -l 2>/dev/null | grep -v 'run_cf_recommender'; echo "$CRON_JOB" ) | crontab -
echo "   ✅ Cron 已設定：每天 12:00 自動執行"
echo "   📄 Log 路徑：$(pwd)/logs/recommender.log"
echo ""

echo ""
echo "🚀 啟動 Django → http://127.0.0.1:8000"
echo "   Admin：http://127.0.0.1:8000/admin"
echo "   微信小程序請求打到：http://你的本機IP:8000"
echo "   （微信開發工具 → 詳情 → 本地設定 → 不校驗合法域名）"
echo ""
python3 manage.py runserver 0.0.0.0:8000
