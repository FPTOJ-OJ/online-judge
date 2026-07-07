#!/bin/bash
# ==============================================================================
# docker_test.sh - Chạy setup_fptoj.sh trong Docker Ubuntu để debug cô lập
# Sử dụng: bash .github/workflows/docker_test.sh [--no-services]
# ==============================================================================

set -e

SITE_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
IMAGE=ubuntu:24.04
CONTAINER_NAME=fptoj-test-debug
START_SERVICES=true

if [ "$1" = "--no-services" ]; then
  START_SERVICES=false
fi

echo "=============================================="
echo "  FPTOJ Docker Debug Test Runner"
echo "  Site dir: $SITE_DIR"
echo "=============================================="

echo "[i] Dọn container cũ nếu còn tồn tại..."
docker rm -f $CONTAINER_NAME 2>/dev/null || true

echo "[i] Khởi tạo container và mount source code..."
docker run -d --name $CONTAINER_NAME \
  -v "$SITE_DIR:/site" \
  --privileged \
  $IMAGE sleep infinity

echo "[i] Cài đặt dependencies..."
docker exec $CONTAINER_NAME bash -c '
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq lsof curl \
    mysql-server redis-server nginx supervisor \
    python3 python3-pip git nodejs npm \
    default-libmysqlclient-dev build-essential libssl-dev libffi-dev 2>&1 | tail -5
  echo "[OK] Dependencies installed"
'

if [ "$START_SERVICES" = "true" ]; then
  echo "[i] Khởi động MySQL, Redis, Nginx bên trong container..."
  docker exec $CONTAINER_NAME bash -c '
    service mysql start  2>/dev/null || mysqld_safe --skip-networking &
    service redis-server start 2>/dev/null || redis-server --daemonize yes
    service nginx start  2>/dev/null || true
    sleep 3
    echo "[OK] Services started"
  '
fi

echo ""
echo "[i] Chạy setup_fptoj.sh qua stdin pipe..."
docker exec -i $CONTAINER_NAME bash -c '
  cd /site
  mkdir -p logs
  {
    echo ""
    echo ""
    echo ""
    echo ""
    echo "fake_password"
    echo ""; echo ""; echo ""; echo ""; echo ""
    echo ""
    echo "/data"
    echo "fake.domain.com"
    echo ""; echo ""; echo ""; echo ""; echo ""; echo ""
    echo "n"
    echo "test-judge-1"
    echo ""
    echo "n"
    python3 -c "print(\"\n\" * 50)"
  } | bash ./setup_fptoj.sh
'

EXIT_CODE=$?
echo ""
if [ $EXIT_CODE -eq 0 ]; then
  echo "[✓] Test thành công!"
  docker exec $CONTAINER_NAME cat /site/dmoj/local_settings.py | grep "fake.domain.com" && \
    echo "[✓] Domain fake.domain.com có trong cấu hình."
else
  echo "[✗] Test thất bại (exit $EXIT_CODE)"
fi

echo "[i] Dọn container..."
docker rm -f $CONTAINER_NAME 2>/dev/null || true
