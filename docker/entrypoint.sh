#!/bin/bash
set -e

# Đọc loại dịch vụ từ tham số đầu tiên, mặc định là 'web'
SERVICE_TYPE="${1:-web}"

# Chuyển đổi tham số nếu người dùng cấu hình bằng biến môi trường
if [ -n "$DMOJ_SERVICE_TYPE" ]; then
    SERVICE_TYPE="$DMOJ_SERVICE_TYPE"
fi

echo "=== KHỞI CHẠY DỊCH VỤ DMOJ: $SERVICE_TYPE ==="

if [ "$SERVICE_TYPE" = "web" ]; then
    # Bước khởi tạo (chỉ chạy khi container Web bắt đầu)
    echo "[i] Đang khởi chạy migrations..."
    python manage.py migrate --noinput
    
    echo "[i] Đang compile messages..."
    python manage.py compilemessages -i dmojsite
    
    echo "[i] Đang compile JS translations..."
    python manage.py compilejsi18n
    
    echo "[i] Đang gom static files..."
    python manage.py collectstatic --noinput
    
    # Khởi chạy ứng dụng Web uWSGI
    echo "[i] Khởi chạy uWSGI Web Server..."
    exec uwsgi --ini docker/uwsgi.ini --workers "${UWSGI_WORKERS:-4}"

elif [ "$SERVICE_TYPE" = "celery" ]; then
    # Khởi chạy Celery Worker
    CONCURRENCY="${CELERY_CONCURRENCY:-2}"
    echo "[i] Khởi chạy Celery Worker (concurrency: $CONCURRENCY)..."
    exec celery -A dmoj worker -l info --concurrency="$CONCURRENCY"

elif [ "$SERVICE_TYPE" = "wsevent" ]; then
    # Khởi chạy Event Server
    echo "[i] Khởi chạy Websocket Event Server..."
    export NODE_PATH="/app/node_modules"
    exec node websocket/daemon.js

elif [ "$SERVICE_TYPE" = "bridged" ]; then
    # Khởi chạy Bridged Server (Máy chủ phân phối kết nối cho máy chấm)
    echo "[i] Khởi chạy Bridged Server..."
    exec python manage.py runbridged

else
    # Nếu truyền lệnh tùy chỉnh khác (ví dụ: bash, python manage.py shell)
    exec "$@"
fi
