FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安裝 MySQL 所需的系統依賴
# 安裝 MySQL 所需的系統依賴與 HTTPS 憑證
# 確保 ca-certificates 安裝後執行 update-ca-certificates
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 設定環境變量，告訴 Python 去哪裡找剛剛裝好的憑證
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

WORKDIR /app

COPY requirements.txt .
# 使用騰訊雲鏡像源加速
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.tencent.com/pypi/simple/

COPY . .

# 收集靜態文件
RUN python manage.py collectstatic --noinput --clear

EXPOSE 80

# 只專心負責啟動 Gunicorn，保持極速啟動
# 將 workers 改為 2，讓啟動更輕量
CMD ["gunicorn", "mysite.wsgi:application", "--bind", "0.0.0.0:80", "--workers=2", "--timeout=60"]