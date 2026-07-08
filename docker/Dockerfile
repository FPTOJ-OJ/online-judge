# Giai đoạn 1: Biên dịch các assets giao diện (SASS/CSS)
FROM node:20-alpine AS asset-builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
# Cài đặt các công cụ biên dịch css/sass trong container build
RUN npm install -g sass postcss postcss-cli autoprefixer
COPY make_style.sh ./
COPY resources/ ./resources/
RUN ./make_style.sh

# Giai đoạn 2: Tạo Docker Image ứng dụng chính
FROM python:3.10-slim-bullseye
WORKDIR /app

# Đặt các tham số tối ưu hóa cho Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Cài đặt các thư viện hệ thống cần thiết và Node.js phục vụ event server
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    pkg-config \
    default-libmysqlclient-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    gettext \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt các thư viện Python
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir mysqlclient uwsgi pymysql redis

# Cài đặt các thư viện Node.js production cho websocket server
COPY package*.json ./
RUN npm ci --only=production

# Sao chép assets đã biên dịch từ Stage 1
COPY --from=asset-builder /app/sass_processed/ ./sass_processed/
COPY --from=asset-builder /app/resources/ ./resources/

# Sao chép toàn bộ mã nguồn
COPY . .

# Tạo các thư mục lưu trữ logs, static, media và pdfcache
RUN mkdir -p logs static media /data/problems /data/pdfcache /data/datacache

# Expose các cổng dịch vụ
# 8000: Web uWSGI | 10000: Bridged máy chấm | 15100-15102: Websocket Event Server
EXPOSE 8000 10000 15100 15101 15102

# Sử dụng entrypoint script để điều khiển dịch vụ
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["web"]
