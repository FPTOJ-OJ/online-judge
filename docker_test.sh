#!/bin/bash
# Script này cài dependencies và chạy expect test trong Docker Ubuntu

set -e

SITE_DIR=/home/kien/site
IMAGE=ubuntu:24.04
CONTAINER_NAME=fptoj-test-debug

echo "[i] Dọn container cũ nếu còn tồn tại..."
docker rm -f $CONTAINER_NAME 2>/dev/null || true

echo "[i] Khởi tạo container test và cài dependencies..."
docker run -d --name $CONTAINER_NAME \
  -v "$SITE_DIR:/site" \
  --privileged \
  $IMAGE sleep infinity

docker exec $CONTAINER_NAME bash -c '
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq expect lsof curl netcat-openbsd \
    mysql-server redis-server nginx supervisor \
    python3 python3-pip git nodejs npm \
    default-libmysqlclient-dev build-essential libssl-dev libffi-dev 2>&1 | tail -5
  echo "[OK] Dependencies installed"
'

echo ""
echo "[i] Khởi động MySQL, Redis và Nginx bên trong container..."
docker exec $CONTAINER_NAME bash -c '
  service mysql start
  service redis-server start
  service nginx start
  service supervisor start
  sleep 2
  echo "[OK] Services started"
'

echo ""
echo "[i] Chạy expect test script..."
docker exec -i $CONTAINER_NAME bash -c '
  cd /site
  cat > /tmp/test_setup.exp << '"'"'EOF'"'"'
#!/usr/bin/expect -f
log_user 1
set timeout 20
spawn bash ./setup_fptoj.sh
expect {
    "*Online Judge*"           { send "\r"; exp_continue }
    "*Docker*"                 { send "\r"; exp_continue }
    "*database '"'"'dmoj'"'"'*" { send "fake_password\r"; exp_continue }
    "*ROOT*"                   { send "fake_password\r"; exp_continue }
    "*Host IP*"                { send "\r"; exp_continue }
    "*Port*"                   { send "\r"; exp_continue }
    "*dang nhap Database*"     { send "\r"; exp_continue }
    "*khau dang nhap Database*"{ send "fake_password\r"; exp_continue }
    "*SMTP Mail*"              { send "\r"; exp_continue }
    "*Cong SMTP*"              { send "\r"; exp_continue }
    "*SMTP Email*"             { send "\r"; exp_continue }
    "*Email gui*"              { send "\r"; exp_continue }
    "*Admin*"                  { send "Admin\r"; exp_continue }
    "*Email Admin*"            { send "admin@fake.com\r"; exp_continue }
    "*Problems, Cache*"        { send "/data\r"; exp_continue }
    "*fptoj.com,www.fptoj.com*" { send "fake.domain.com\r"; exp_continue }
    "*Google OAuth2 Key*"      { send "\r"; exp_continue }
    "*Google OAuth2 Secret*"   { send "\r"; exp_continue }
    "*GitHub OAuth2 Key*"      { send "\r"; exp_continue }
    "*GitHub OAuth2 Secret*"   { send "\r"; exp_continue }
    "*Turnstile SiteKey*"      { send "\r"; exp_continue }
    "*Turnstile Secret*"       { send "\r"; exp_continue }
    "*tai khoan Admin*"        { send "n\r"; exp_continue }
    "*Web Server*"             { send "8080\r"; exp_continue }
    "*Judge ID*"               { send "test-judge-1\r"; exp_continue }
    "*Judge Key*"              { send "\r"; exp_continue }
    "*Judge Server*"           { send "n\r"; exp_continue }
    timeout {
        send_user "\n[ERROR] TIMEOUT - Script bị kẹt ở đây!\n"
        exit 1
    }
    eof
}
catch wait result
set exit_status [lindex $result 3]
exit $exit_status
EOF
  chmod +x /tmp/test_setup.exp
  /tmp/test_setup.exp
'

EXIT_CODE=$?
echo ""
if [ $EXIT_CODE -eq 0 ]; then
  echo "[✓] Test thành công!"
else
  echo "[✗] Test thất bại (exit $EXIT_CODE)"
fi

echo "[i] Dọn container..."
docker rm -f $CONTAINER_NAME 2>/dev/null || true
