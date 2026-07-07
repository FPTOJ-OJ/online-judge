#!/bin/bash
# ==============================================================================
# FPTOJ - HỆ THỐNG CÀI ĐẶT TỰ ĐỘNG (AUTO-INSTALLER)
# Thiết kế dành cho người mới bắt đầu (Admin Non-Tech)
# ==============================================================================

set -e

# 1. TỰ ĐỘNG LẤY QUYỀN SUDO
if [ "$EUID" -ne 0 ]; then
  echo "[★] Yêu cầu quyền root/sudo. Đang tự nâng cấp quyền..."
  exec sudo "$0" "$@"
fi

# Xác định user gốc chạy script (để gán quyền chính xác cho các thư mục / dịch vụ)
REAL_USER=${SUDO_USER:-$USER}
USER_HOME=$(eval echo "~$REAL_USER")
if [ -z "$USER_HOME" ] || [ "$USER_HOME" = "~" ]; then
  USER_HOME="/home/kien"
fi

SITE_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "[★] Thư mục cài đặt Site: $SITE_DIR"
echo "[★] Tài khoản chạy hệ thống: $REAL_USER (Home: $USER_HOME)"

# 2. KIỂM TRA CẤU HÌNH PHẦN CỨNG MÁY CHỦ
echo ""
echo "=== KIỂM TRA CẤU HÌNH PHẦN CỨNG ==="
cpu_cores=$(nproc)
total_mem=$(free -m | awk '/^Mem:/{print $2}')
echo "[i] Số nhân CPU: $cpu_cores cores"
echo "[i] Dung lượng RAM: ${total_mem} MB"

# Đưa ra profile khuyến nghị
if [ "$total_mem" -lt 2000 ]; then
  PROFILE="LIGHTWEIGHT"
  UWSGI_WORKERS=2
  CELERY_CONCURRENCY=1
  echo "[!] Nhận diện máy chủ cấu hình thấp. Tự động đề xuất cấu hình tối giản."
elif [ "$total_mem" -lt 4000 ]; then
  PROFILE="MEDIUM"
  UWSGI_WORKERS=4
  CELERY_CONCURRENCY=2
  echo "[!] Nhận diện máy chủ cấu hình trung bình."
else
  PROFILE="PRODUCTION"
  UWSGI_WORKERS=8
  CELERY_CONCURRENCY=4
  echo "[!] Nhận diện máy chủ cấu hình cao. Bật cấu hình tối đa."
fi

# 3. PHÁT HIỆN CÁC DỊCH VỤ ĐÃ CÓ TRÊN HOST
echo ""
echo "=== QUÉT DỊCH VỤ HIỆN CÓ TRÊN MÁY CHỦ HOST ==="
mysql_on_host=false
redis_on_host=false
nginx_on_host=false
supervisor_on_host=false

# Kiểm tra MySQL/MariaDB
if systemctl is-active mysql >/dev/null 2>&1 || systemctl is-active mariadb >/dev/null 2>&1 || lsof -i :3306 >/dev/null 2>&1; then
  echo "[✓] Phát hiện MySQL/MariaDB đang chạy trên Host."
  mysql_on_host=true
else
  echo "[x] Không tìm thấy MySQL/MariaDB trên Host."
fi

# Kiểm tra Redis
if systemctl is-active redis >/dev/null 2>&1 || systemctl is-active redis-server >/dev/null 2>&1 || lsof -i :6379 >/dev/null 2>&1; then
  echo "[✓] Phát hiện Redis đang chạy trên Host."
  redis_on_host=true
else
  echo "[x] Không tìm thấy Redis trên Host."
fi

# Kiểm tra Nginx
if systemctl is-active nginx >/dev/null 2>&1 || lsof -i :80 >/dev/null 2>&1; then
  echo "[✓] Phát hiện Nginx đang chạy trên Host."
  nginx_on_host=true
fi

# Kiểm tra Supervisor
if systemctl is-active supervisor >/dev/null 2>&1; then
  echo "[✓] Phát hiện Supervisor đang chạy trên Host."
  supervisor_on_host=true
fi

# Hàm tìm port trống
find_free_port() {
  local port=$1
  while lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; do
    port=$((port + 1))
  done
  echo $port
}

# 4. TRÌNH PHÂN TÍCH CẤU HÌNH CŨ (ĐỌC DEFAULTS TỪ LOCAL_SETTINGS.PY NẾU CÓ)
parse_setting() {
  local key="$1"
  local default_val="$2"
  if [ -f "$SITE_DIR/dmoj/local_settings.py" ]; then
    python3 -c "
import re
try:
    with open('$SITE_DIR/dmoj/local_settings.py') as f:
        content = f.read()
    val = re.search(r'^\s*$key\s*=\s*[\"'](.*?)[\"']', content, re.MULTILINE)
    if val:
        print(val.group(1))
        exit(0)
except Exception:
    pass
print('$default_val')
" 2>/dev/null
  else
    echo "$default_val"
  fi
}

parse_db_setting() {
  local key="$1"
  local default_val="$2"
  if [ -f "$SITE_DIR/dmoj/local_settings.py" ]; then
    python3 -c "
import re
try:
    with open('$SITE_DIR/dmoj/local_settings.py') as f:
        content = f.read()
    db_block = re.search(r'DATABASES\s*=\s*\{.*?\}', content, re.DOTALL)
    if db_block:
        val = re.search(r'[\"']$key[\"']\s*:\s*[\"'](.*?)[\"']', db_block.group(0))
        if val:
            print(val.group(1))
            exit(0)
except Exception:
    pass
print('$default_val')
" 2>/dev/null
  else
    echo "$default_val"
  fi
}

# 5. HƯỚNG DẪN TƯƠNG TÁC NHẬP THÔNG TIN CẤU HÌNH
echo ""
echo "=== HƯỚNG DẪN THIẾT LẬP CẤU HÌNH (Bấm Enter để lấy mặc định) ==="

# Đọc các giá trị mặc định sẵn có
OLD_SITE_NAME=$(parse_setting "SITE_NAME" "FPTOJ")
OLD_HOSTS=$(parse_setting "ALLOWED_HOSTS" "fptoj.com,www.fptoj.com,127.0.0.1")
OLD_DB_HOST=$(parse_db_setting "HOST" "127.0.0.1")
OLD_DB_NAME=$(parse_db_setting "NAME" "dmoj")
OLD_DB_USER=$(parse_db_setting "USER" "dmoj")
OLD_DB_PASS=$(parse_db_setting "PASSWORD" "12345678")

OLD_EMAIL_HOST=$(parse_setting "EMAIL_HOST" "")
OLD_EMAIL_PORT=$(parse_setting "EMAIL_PORT" "")
OLD_EMAIL_USER=$(parse_setting "EMAIL_HOST_USER" "")
OLD_EMAIL_PASS=$(parse_setting "EMAIL_HOST_PASSWORD" "")
OLD_EMAIL_FROM=$(parse_setting "DEFAULT_FROM_EMAIL" "")

read -p "[?] Tên trang web Online Judge của bạn [$OLD_SITE_NAME]: " site_name
site_name=${site_name:-$OLD_SITE_NAME}


# Hỏi về Docker cho MySQL/Redis
use_docker_mysql=false
use_docker_redis=false

if [ "$mysql_on_host" = "false" ]; then
  read -p "[?] MySQL/MariaDB không chạy trên Host. Bạn có muốn tự động tạo bằng Docker? (y/n) [y]: " docker_mysql_ans
  docker_mysql_ans=${docker_mysql_ans:-y}
  if [ "$docker_mysql_ans" = "y" ] || [ "$docker_mysql_ans" = "Y" ]; then
    use_docker_mysql=true
  fi
fi

if [ "$redis_on_host" = "false" ]; then
  read -p "[?] Redis không chạy trên Host. Bạn có muốn tự động tạo bằng Docker? (y/n) [y]: " docker_redis_ans
  docker_redis_ans=${docker_redis_ans:-y}
  if [ "$docker_redis_ans" = "y" ] || [ "$docker_redis_ans" = "Y" ]; then
    use_docker_redis=true
  fi
fi

# Thiết lập Database
if [ "$use_docker_mysql" = "true" ]; then
  db_host="127.0.0.1"
  db_name="dmoj"
  db_user="dmoj"
  read -p "[?] Đặt mật khẩu cho người dùng database 'dmoj' [$OLD_DB_PASS]: " db_pass
  db_pass=${db_pass:-$OLD_DB_PASS}
  read -p "[?] Đặt mật khẩu cho tài khoản ROOT của MySQL Docker [rootpass]: " db_root_pass
  db_root_pass=${db_root_pass:-rootpass}
else
  read -p "[?] Địa chỉ máy chủ Database (Host IP) [$OLD_DB_HOST]: " db_host
  db_host=${db_host:-$OLD_DB_HOST}
  read -p "[?] Cổng Database (Port) [3306]: " db_port
  db_port=${db_port:-3306}
  read -p "[?] Tên Cơ sở dữ liệu [$OLD_DB_NAME]: " db_name
  db_name=${db_name:-$OLD_DB_NAME}
  read -p "[?] Tên đăng nhập Database [$OLD_DB_USER]: " db_user
  db_user=${db_user:-$OLD_DB_USER}
  read -p "[?] Mật khẩu đăng nhập Database [$OLD_DB_PASS]: " db_pass
  db_pass=${db_pass:-$OLD_DB_PASS}
fi

# Thiết lập Email SMTP
echo ""
echo "[i] Thiết lập Email SMTP (Để trống nếu không dùng - cấu hình lại sau ở Admin)"
read -p "[?] Địa chỉ máy chủ SMTP Mail [$OLD_EMAIL_HOST]: " email_host
email_host=${email_host:-$OLD_EMAIL_HOST}
if [ -n "$email_host" ]; then
    read -p "[?] Cổng SMTP (thường là 587 hoặc 465) [$OLD_EMAIL_PORT]: " email_port
    email_port=${email_port:-$OLD_EMAIL_PORT}
    read -p "[?] Tên đăng nhập SMTP Email [$OLD_EMAIL_USER]: " email_user
    email_user=${email_user:-$OLD_EMAIL_USER}
    read -p "[?] Mật khẩu SMTP Email [$OLD_EMAIL_PASS]: " email_pass
    email_pass=${email_pass:-$OLD_EMAIL_PASS}
    read -p "[?] Email gửi đi hiển thị (From Email) [$OLD_EMAIL_FROM]: " email_from
    email_from=${email_from:-$OLD_EMAIL_FROM}
fi

echo ""
echo "[i] Thiết lập Tài khoản Admin Mặc định"
read -p "[?] Tên Admin (Để trống nếu không dùng) []: " admin_name
if [ -n "$admin_name" ]; then
    read -p "[?] Email Admin []: " admin_email
fi

echo ""
echo "[i] Thiết lập Thư mục Dữ liệu (Data Directory)"
read -p "[?] Thư mục chứa dữ liệu tĩnh (Problems, Cache) [/data]: " data_dir
data_dir=${data_dir:-/data}

# Tạo các thư mục dữ liệu cần thiết trước để tránh Docker tạo với quyền root
mkdir -p "$data_dir"
mkdir -p "$data_dir/problems" "$data_dir/pdfcache" "$data_dir/datacache" "$data_dir/mysql"
chmod -R 775 "$data_dir"
chown -R $REAL_USER:$REAL_USER "$data_dir"

# Tạo thư mục logs sớm cho dự án tránh lỗi Django FileHandler
mkdir -p "$SITE_DIR/logs"
chown -R $REAL_USER:$REAL_USER "$SITE_DIR/logs"
chmod -R 775 "$SITE_DIR/logs"

# Kiểm tra và tự động cấu hình các cổng kết nối tránh trùng lặp
echo ""
echo "=== KIỂM TRA VÀ TỰ ĐỘNG CẤU HÌNH CỔNG KẾT NỐI ==="

db_port=${db_port:-3306}
if [ "$use_docker_mysql" = "true" ]; then
  db_port=$(find_free_port 3306)
  if [ "$db_port" != "3306" ]; then
    echo "[!] Port 3306 đã bị chiếm. Tự động chuyển cổng Docker MySQL sang $db_port."
  fi
fi

redis_port=6379
if [ "$use_docker_redis" = "true" ]; then
  redis_port=$(find_free_port 6379)
  if [ "$redis_port" != "6379" ]; then
    echo "[!] Port 6379 đã bị chiếm. Tự động chuyển cổng Docker Redis sang $redis_port."
  fi
elif [ "$redis_on_host" = "true" ]; then
  read -p "[?] Port của Redis đang chạy trên Host [6379]: " redis_port
  redis_port=${redis_port:-6379}
fi

judge_port=$(find_free_port 9999)
if [ "$judge_port" != "9999" ]; then
  echo "[!] Port 9999 (Máy chấm) đã bị chiếm. Tự động chuyển sang cổng $judge_port."
fi

pdf_port=$(find_free_port 8888)
if [ "$pdf_port" != "8888" ]; then
  echo "[!] Port 8888 (PDF Service) đã bị chiếm. Tự động chuyển sang cổng $pdf_port."
fi

wsevent_get_port=$(find_free_port 15100)
wsevent_post_port=$(find_free_port $((wsevent_get_port + 1)))
wsevent_http_port=$(find_free_port $((wsevent_post_port + 1)))
if [ "$wsevent_get_port" != "15100" ] || [ "$wsevent_post_port" != "15101" ] || [ "$wsevent_http_port" != "15102" ]; then
  echo "[!] Một trong các cổng Websocket (15100, 15101, 15102) bị chiếm. Đổi sang: GET=$wsevent_get_port, POST=$wsevent_post_port, HTTP=$wsevent_http_port."
fi

# 6. CÀI ĐẶT CÁC THƯ VIỆN HỆ THỐNG
echo ""
echo "=== 1. CÀI ĐẶT THƯ VIỆN HỆ THỐNG ==="
apt-get update
apt-get install -y git gcc g++ make python3-dev python3-pip python3-venv libxml2-dev libxslt1-dev zlib1g-dev gettext curl supervisor nginx wkhtmltopdf lsof

# Kiểm tra và cài đặt Node.js nếu chưa có
if ! command -v node >/dev/null 2>&1; then
  echo "[i] Không tìm thấy NodeJS. Tiến hành cài đặt NodeJS 18..."
  curl -sL https://deb.nodesource.com/setup_18.x | bash -
  apt-get install -y nodejs
else
  echo "[✓] NodeJS đã được cài đặt: $(node -v)"
fi

# Cài đặt global npm packages phục vụ cho make_style.sh
echo "[i] Cài đặt sass, postcss, autoprefixer..."
npm install -g sass postcss-cli postcss autoprefixer

# 7. CÀI ĐẶT DOCKER NẾU CẦN THIẾT
if [ "$use_docker_mysql" = "true" ] || [ "$use_docker_redis" = "true" ]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "[i] Đang cài đặt Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
  else
    echo "[✓] Docker đã được cài đặt."
  fi
fi

# Khởi chạy Docker MySQL nếu chọn
if [ "$use_docker_mysql" = "true" ]; then
  if docker ps -a --format '{{.Names}}' | grep -q '^fptoj-mysql$'; then
    echo "[!] Container fptoj-mysql đã tồn tại. Đang khởi động lại..."
    docker start fptoj-mysql || true
  else
    echo "[i] Đang khởi chạy MySQL Container..."
    docker run -d \
      --name fptoj-mysql \
      --restart always \
      -p 127.0.0.1:$db_port:3306 \
      -v "$data_dir/mysql":/var/lib/mysql \
      -e MYSQL_ROOT_PASSWORD="$db_root_pass" \
      -e MYSQL_DATABASE="$db_name" \
      -e MYSQL_USER="$db_user" \
      -e MYSQL_PASSWORD="$db_pass" \
      mariadb:10.11 \
      --character-set-server=utf8mb4 \
      --collation-server=utf8mb4_unicode_ci
    echo "[i] Đợi 15 giây cho MySQL khởi động hoàn tất..."
    sleep 15
  fi
fi

# Khởi chạy Docker Redis nếu chọn
if [ "$use_docker_redis" = "true" ]; then
  if docker ps -a --format '{{.Names}}' | grep -q '^fptoj-redis$'; then
    echo "[!] Container fptoj-redis đã tồn tại. Đang khởi động lại..."
    docker start fptoj-redis || true
  else
    echo "[i] Đang khởi chạy Redis Container..."
    docker run -d \
      --name fptoj-redis \
      --restart always \
      -p 127.0.0.1:$redis_port:6379 \
      redis:7-alpine
  fi
fi

# 8. THIẾT LẬP MÔI TRƯỜNG ẢO PYTHON CHO SITE
echo ""
echo "=== 2. THIẾT LẬP PYTHON VIRTUALENV ==="
if [ ! -d "$SITE_DIR/dmojsite" ]; then
  echo "[i] Tạo môi trường ảo dmojsite..."
  python3 -m venv "$SITE_DIR/dmojsite"
fi

# Kích hoạt môi trường ảo và cài đặt thư viện
source "$SITE_DIR/dmojsite/bin/activate"
pip install --upgrade pip
pip install -r "$SITE_DIR/requirements.txt"
pip install mysqlclient uwsgi pymysql redis

# Tạo symbolic link hoặc mock cho pymysql
# (Trường hợp không compile được mysqlclient trên các nền tảng đặc biệt)
cat << 'EOF' > "$SITE_DIR/dmoj_install_pymysql.py"
import pymysql
pymysql.install_as_MySQLdb()
pymysql.version_info = (1, 4, 3, 'final', 0)
EOF

# 9. TỰ ĐỘNG SINH FILE CẤU HÌNH LOCAL_SETTINGS.PY
echo ""
echo "=== THIẾT LẬP DOMAIN VÀ BẢO MẬT ==="
read -p "[?] Tên miền hoặc IP truy cập (cách nhau bằng dấu phẩy, ấn Enter để dùng localhost) [$OLD_HOSTS]: " allowed_hosts
allowed_hosts=${allowed_hosts:-$OLD_HOSTS}

echo "[i] Nhập các API Keys (để trống nếu không dùng):"
read -p " - Google OAuth2 Key: " google_oauth_key
read -p " - Google OAuth2 Secret: " google_oauth_secret
read -p " - GitHub OAuth2 Key: " github_oauth_key
read -p " - GitHub OAuth2 Secret: " github_oauth_secret
read -p " - Cloudflare Turnstile SiteKey: " turnstile_sitekey
read -p " - Cloudflare Turnstile Secret: " turnstile_secret

echo ""
echo "=== 3. CẤU HÌNH DMOJ LOCAL_SETTINGS.PY ==="
# Định dạng chuỗi ALLOWED_HOSTS cho Django
formatted_hosts=$(echo "$allowed_hosts" | sed "s/,/','/g" | sed "s/^/['/" | sed "s/$/']/")
first_host=$(echo "$allowed_hosts" | cut -d',' -f1)

# Xử lý Email Config
if [ -n "$email_host" ]; then
    email_config="
# Cấu hình SMTP Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
EMAIL_HOST = '$email_host'
EMAIL_PORT = $email_port
EMAIL_HOST_USER = '$email_user'
EMAIL_HOST_PASSWORD = '$email_pass'
DEFAULT_FROM_EMAIL = '$email_from'
SERVER_EMAIL = '$email_user'
"
else
    email_config=""
fi

if [ -n "$admin_name" ]; then
    admin_config="
ADMINS = (
    ('$admin_name', '$admin_email'),
)
"
else
    admin_config=""
fi

cat << EOF > "$SITE_DIR/dmoj/local_settings.py"
# Sinh tự động bởi setup_fptoj.sh vào $(date)
import datetime

SECRET_KEY = '$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")'
DEBUG = False

ALLOWED_HOSTS = $formatted_hosts

INSTALLED_APPS += (
)

# Cấu hình cache Redis hoặc LocMem
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': '$db_name',
        'USER': '$db_user',
        'PASSWORD': '$db_pass',
        'HOST': '$db_host',
        'PORT': '$db_port',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'sql_mode': 'STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION',
        },
    },
}

LANGUAGE_CODE = 'vi'
DEFAULT_USER_TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_L10N = True
USE_TZ = True

COMPRESS_OUTPUT_DIR = 'cache'
COMPRESS_CSS_FILTERS = [
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.CSSMinFilter',
]
COMPRESS_JS_FILTERS = ['compressor.filters.jsmin.JSMinFilter']
COMPRESS_STORAGE = 'compressor.storage.GzipCompressorFileStorage'
STATICFILES_FINDERS += ('compressor.finders.CompressorFinder',)

DMOJ_TMP_DIR = '/tmp'

$email_config

$admin_config

STATIC_ROOT = '$SITE_DIR/static'
STATIC_URL = '/static/'

SITE_NAME = '$site_name'
SITE_LONG_NAME = '${site_name}: FPT Online Judge'
SITE_ADMIN_EMAIL = '$admin_email'
TERMS_OF_SERVICE_URL = '/about/tos/'

# Cấu hình máy chấm kết nối
BRIDGED_JUDGE_ADDRESS = [('0.0.0.0', $judge_port)]
DMOJ_PROBLEM_DATA_ROOT = "$data_dir/problems"

# Event Server
EVENT_DAEMON_USE = True
EVENT_DAEMON_POST = 'ws://127.0.0.1:$wsevent_post_port/'
EVENT_DAEMON_GET = 'ws://$first_host/event/'
EVENT_DAEMON_GET_SSL = 'wss://$first_host/event/'
EVENT_DAEMON_POLL = '/channels/'

# Celery Broker
CELERY_BROKER_URL = 'redis://localhost:$redis_port/0'
CELERY_RESULT_BACKEND = 'redis://localhost:$redis_port/0'

ACE_URL = '//cdnjs.cloudflare.com/ajax/libs/ace/1.43.3/'
JQUERY_JS = '//cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js'
SELECT2_JS_URL = '//cdnjs.cloudflare.com/ajax/libs/select2/4.0.13/js/select2.min.js'
SELECT2_CSS_URL = '//cdnjs.cloudflare.com/ajax/libs/select2/4.0.13/css/select2.min.css'

TIMEZONE_MAP = 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Blue_Marble_2002.png/1024px-Blue_Marble_2002.png'

DMOJ_HTTPS = 2

# Xuất PDF độc quyền
DMOJ_PDF_PDFOID_URL = 'http://localhost:$pdf_port'
DMOJ_PDF_PROBLEM_CACHE = '$data_dir/pdfcache'
DMOJ_PDF_PROBLEM_INTERNAL = '/pdfcache'

DMOJ_USER_DATA_DOWNLOAD = True
DMOJ_USER_DATA_CACHE = '$data_dir/datacache'
DMOJ_USER_DATA_INTERNAL = '/datacache'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'file': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s',
        },
        'simple': {
            'format': '%(levelname)s %(message)s',
        },
    },
    'handlers': {
        'bridge': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '$SITE_DIR/logs/web.log',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 10,
            'formatter': 'file',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'file',
        },
    },
    'loggers': {
        'judge.bridge': {
            'handlers': ['bridge'],
            'level': 'INFO',
            'propagate': True,
        },
        '': {
            'handlers': ['console'],
        },
    },
}

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = '$google_oauth_key'
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = '$google_oauth_secret'
SOCIAL_AUTH_GITHUB_SECURE_KEY = '$github_oauth_key'
SOCIAL_AUTH_GITHUB_SECURE_SECRET = '$github_oauth_secret'

TURNSTILE_SITEKEY = '$turnstile_sitekey' or None
TURNSTILE_SECRET = '$turnstile_secret' or None
DATA_UPLOAD_MAX_NUMBER_FIELDS = 2000
LOGIN_URL = '/accounts/login/'
EOF

echo "[✓] Đã tạo file cấu hình dmoj/local_settings.py thành công."

# 10. TẠO FILE UWSGI.INI CHO PRODUCTION
echo "[i] Sinh file cấu hình uwsgi.ini..."
cat << EOF > "$SITE_DIR/uwsgi.ini"
[uwsgi]
uwsgi-socket = /tmp/dmoj-site.sock
chmod-socket = 666
pidfile = /tmp/dmoj-site.pid

uid = $REAL_USER
gid = $REAL_USER

chdir = $SITE_DIR
pythonpath = $SITE_DIR
virtualenv = $SITE_DIR/dmojsite

protocol = uwsgi
master = true
env = DJANGO_SETTINGS_MODULE=dmoj.settings
module = dmoj.wsgi:application
optimize = 2

memory-report = true
cheaper-algo = backlog
cheaper = 2
cheaper-initial = 3
cheaper-step = 1
workers = $UWSGI_WORKERS
EOF

# Thư mục dữ liệu đã được tạo trước ở bước trên

# 11. DỊCH GIAO DIỆN VÀ BIÊN DỊCH ASSETS
echo ""
echo "=== 4. BIÊN DỊCH GIAO DIỆN & ASSETS ==="
# Tải các submodules nếu có
git submodule init
git submodule update

# Cài đặt thư viện Nodejs phục vụ websocket
if [ -f "$SITE_DIR/package.json" ]; then
  npm install
  
  # Tạo file cấu hình websocket động
  echo "[i] Tạo cấu hình websocket động..."
  cat << EOF > "$SITE_DIR/websocket/config.js"
module.exports = {
    get_host: '127.0.0.1',
    get_port: $wsevent_get_port,
    post_host: '127.0.0.1',
    post_port: $wsevent_post_port,
    http_host: '127.0.0.1',
    http_port: $wsevent_http_port,
    long_poll_timeout: 29000,
};
EOF
  chown $REAL_USER:$REAL_USER "$SITE_DIR/websocket/config.js"
fi

# Biên dịch css/Sass
./make_style.sh
python manage.py collectstatic --no-input
python manage.py compilemessages -i dmojsite
python manage.py compilejsi18n

# 12. KHỞI TẠO CSDL VÀ NAP DỮ LIỆU
echo ""
echo "=== 5. KHỞI TẠO CƠ SỞ DỮ LIỆU ==="
python manage.py migrate
python manage.py loaddata navbar
python manage.py loaddata language_small
python manage.py loaddata demo

# Tạo superuser
read -p "[?] Bạn có muốn tạo một tài khoản Admin mới? (y/n) [n]: " create_admin_ans
create_admin_ans=${create_admin_ans:-n}
if [ "$create_admin_ans" = "y" ] || [ "$create_admin_ans" = "Y" ]; then
  python manage.py createsuperuser
fi

# 13. CẤU HÌNH SUPERVISOR CHO CÁC DỊCH VỤ NỀN
echo ""
echo "=== 6. CẤU HÌNH DỊCH VỤ NỀN SUPERVISOR ==="
mkdir -p /etc/supervisor/conf.d
mkdir -p "$SITE_DIR/logs"
chown -R $REAL_USER:$REAL_USER "$SITE_DIR/logs"
chmod -R 775 "$SITE_DIR/logs"

# Lấy đường dẫn NodeJS động để cấu hình wsevent
NODE_PATH_BIN=$(command -v node || echo "/usr/bin/node")

# Web site service
cat << EOF > /etc/supervisor/conf.d/site.conf
[program:site]
command=$SITE_DIR/dmojsite/bin/uwsgi --ini uwsgi.ini
directory=$SITE_DIR
stopsignal=QUIT
stdout_logfile=$SITE_DIR/logs/site.stdout.log
stderr_logfile=$SITE_DIR/logs/site.stderr.log
autorestart=true
stdout_logfile_maxbytes=10MB
stderr_logfile_maxbytes=10MB
stdout_logfile_backups=5
stderr_logfile_backups=5
EOF

# Bridge service
cat << EOF > /etc/supervisor/conf.d/bridged.conf
[program:bridged]
command=$SITE_DIR/dmojsite/bin/python manage.py runbridged
directory=$SITE_DIR
stopsignal=INT
user=$REAL_USER
group=$REAL_USER
stdout_logfile=$SITE_DIR/logs/bridge.stdout.log
stderr_logfile=$SITE_DIR/logs/bridge.stderr.log
autorestart=true
stdout_logfile_maxbytes=10MB
stderr_logfile_maxbytes=10MB
stdout_logfile_backups=5
stderr_logfile_backups=5
EOF

# WS event daemon
cat << EOF > /etc/supervisor/conf.d/wsevent.conf
[program:wsevent]
command=$NODE_PATH_BIN $SITE_DIR/websocket/daemon.js
environment=NODE_PATH="$SITE_DIR/node_modules"
user=$REAL_USER
group=$REAL_USER
stdout_logfile=$SITE_DIR/logs/wsevent.stdout.log
stderr_logfile=$SITE_DIR/logs/wsevent.stderr.log
autorestart=true
stdout_logfile_maxbytes=10MB
stderr_logfile_maxbytes=10MB
stdout_logfile_backups=5
stderr_logfile_backups=5
EOF

# Celery worker
cat << EOF > /etc/supervisor/conf.d/celery.conf
[program:celery]
command=$SITE_DIR/dmojsite/bin/celery -A dmoj_celery worker --concurrency=$CELERY_CONCURRENCY
directory=$SITE_DIR
user=$REAL_USER
group=$REAL_USER
stdout_logfile=$SITE_DIR/logs/celery.stdout.log
stderr_logfile=$SITE_DIR/logs/celery.stderr.log
autorestart=true
stdout_logfile_maxbytes=10MB
stderr_logfile_maxbytes=10MB
stdout_logfile_backups=5
stderr_logfile_backups=5
EOF

echo "[✓] Đã ghi các file cấu hình Supervisor (site, bridged, wsevent, celery)."

# 14. CẤU HÌNH DỊCH VỤ XUẤT PDF ĐỘC QUYỀN (html-to-pdf-flask)
echo ""
echo "=== 7. CẤU HÌNH DỊCH VỤ XUẤT PDF ĐỘC QUYỀN ==="
PDF_DIR="/home/$REAL_USER/html-to-pdf-flask"
if [ ! -d "$PDF_DIR" ]; then
  echo "[i] Đang tải mã nguồn html-to-pdf-flask từ Github..."
  git clone https://github.com/FPTOJ-OJ/html-to-pdf-flask.git "$PDF_DIR"
  chown -R $REAL_USER:$REAL_USER "$PDF_DIR"
fi

if [ -d "$PDF_DIR" ]; then
  # Thiết lập env cho pdf service
  if [ ! -d "$PDF_DIR/env" ]; then
    echo "[i] Thiết lập môi trường ảo cho PDF Tool..."
    python3 -m venv "$PDF_DIR/env"
  fi
  
  # Cài đặt requirements cho PDF Tool
  "$PDF_DIR/env/bin/pip" install --upgrade pip
  "$PDF_DIR/env/bin/pip" install -r "$PDF_DIR/requirements.txt"
  "$PDF_DIR/env/bin/pip" install uwsgi
  
  # Tạo cấu hình uwsgi.ini cho PDF Tool
  cat << EOF > "$PDF_DIR/uwsgi.ini"
[uwsgi]
module = wsgi:app
http = 127.0.0.1:$pdf_port
processes = 2
threads = 1
enable-threads = false
chdir = $PDF_DIR
virtualenv = $PDF_DIR/env
die-on-term = true
vacuum = true
EOF

  # Sinh file Supervisor cho PDF Tool
  cat << EOF > /etc/supervisor/conf.d/html-to-pdf-flask.conf
[program:html-to-pdf-flask]
command=$PDF_DIR/env/bin/uwsgi --ini uwsgi.ini
directory=$PDF_DIR
stopsignal=QUIT
stdout_logfile=$SITE_DIR/logs/html-to-pdf-flask_log.log
stderr_logfile=$SITE_DIR/logs/html-to-pdf-flask.log
autorestart=true
stopasgroup=true
killasgroup=true
environment=BASE_PATH="$SITE_DIR"
stdout_logfile_maxbytes=10MB
stderr_logfile_maxbytes=10MB
stdout_logfile_backups=5
stderr_logfile_backups=5
EOF

  echo "[✓] Thiết lập dịch vụ html-to-pdf-flask thành công."
else
  echo "[!] Không tìm thấy thư mục html-to-pdf-flask và clone thất bại. Bỏ qua."
fi

# 15. CẤU HÌNH NGINX
echo ""
echo "=== 8. CẤU HÌNH WEB SERVER NGINX ==="

if lsof -Pi :80 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "[!] Cảnh báo: Port 80 đang bị phần mềm khác chiếm dụng!"
    read -p "[?] Vui lòng nhập port khác cho Web Server (VD: 8080): " nginx_port
    nginx_port=${nginx_port:-8080}
    echo "[i] Đã cấu hình Nginx chạy ở port $nginx_port."
    echo "[!] KHUYÊN DÙNG: Bạn nên dùng Cloudflare Tunnel (cloudflared) để public web qua port $nginx_port mà không cần mở port trên router."
else
    nginx_port=80
fi

nginx_conf="/etc/nginx/sites-available/fptoj"
cat << EOF > "$nginx_conf"
server {
    listen       $nginx_port;
    listen       [::]:$nginx_port;
    server_name  localhost $allowed_hosts;

    add_header X-UA-Compatible "IE=Edge,chrome=1";
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    charset utf-8;
    try_files \$uri @icons;
    error_page 502 504 /502.html;

    location ~ ^/502\.html$|^/logo\.png$|^/robots\.txt$ {
        root $SITE_DIR;
    }

    location @icons {
        root $SITE_DIR/resources/icons;
        error_page 403 = @uwsgi;
        error_page 404 = @uwsgi;
    }

    location @uwsgi {
        uwsgi_read_timeout 600;
        uwsgi_pass unix:///tmp/dmoj-site.sock;
        include uwsgi_params;
        uwsgi_param SERVER_SOFTWARE nginx/\$nginx_version;
    }

    location /static {
        gzip_static on;
        expires max;
        root $SITE_DIR;
    }

    location /pdfcache {
        internal;
        root $data_dir;
    }

    location /datacache {
        internal;
        root $data_dir;
    }

    # Bật kết nối sự kiện Realtime Event
    location /event/ {
        proxy_pass http://127.0.0.1:$wsevent_get_port/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    location /channels/ {
        proxy_read_timeout          120;
        proxy_pass http://127.0.0.1:$wsevent_http_port;
    }
}
EOF

# Active cấu hình Nginx
rm -f /etc/nginx/sites-enabled/default
ln -sf "$nginx_conf" /etc/nginx/sites-enabled/fptoj

# 16. HỖ TRỢ THIẾT LẬP MÁY CHẤM (JUDGE SERVER) QUA DOCKER
echo ""
echo "=== 9. HƯỚNG DẪN THIẾT LẬP MÁY CHẤM (JUDGE SERVER) ==="
read -p "[?] Bạn có muốn cài đặt và chạy máy chấm (Judge Server) bằng Docker ngay? (y/n) [y]: " setup_judge_ans
setup_judge_ans=${setup_judge_ans:-y}

if [ "$setup_judge_ans" = "y" ] || [ "$setup_judge_ans" = "Y" ]; then
  JUDGE_DIR="/home/$REAL_USER/judge"
  if [ ! -d "$JUDGE_DIR" ]; then
    echo "[i] Đang tải mã nguồn máy chấm..."
    git clone --recursive https://github.com/FPTOJ-OJ/judge-server.git "$JUDGE_DIR"
    chown -R $REAL_USER:$REAL_USER "$JUDGE_DIR"
  fi
  
  read -p "[?] Tên định danh máy chấm (Judge ID) [judge-01]: " judge_id
  judge_id=${judge_id:-judge-01}
  
  read -p "[?] Khóa xác thực bí mật máy chấm (Judge Key, để trống để tạo ngẫu nhiên): " judge_key
  
  if [ -z "$judge_key" ]; then
    echo "[!] Không nhập Judge Key. Hệ thống sẽ tự tạo khóa ngẫu nhiên..."
    judge_key=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
  fi

  if [ -n "$judge_key" ]; then
    # Viết cấu hình judge.yml
    mkdir -p "$data_dir/problems"
    cat << EOF > "$data_dir/problems/judge.yml"
id: $judge_id
key: "$judge_key"
problem_storage_globs:
  - /problems/*

runtime:
  as_x64: /usr/bin/x86_64-linux-gnu-as
  as_x86: /usr/bin/as
  awk: /usr/bin/mawk
  cargo: /home/judge/.cargo/bin/cargo
  cat: /usr/bin/cat
  chicken-csc: /usr/bin/chicken-csc
  clang: /usr/bin/clang
  clang++: /usr/bin/clang++
  dmd: /opt/dlang/linux/bin64/dmd
  fpc: /usr/bin/fpc
  fpc-themis: /usr/bin/fpc
  fsharpc: /usr/bin/fsharpc
  g++: /usr/bin/g++
  g++-themis: /usr/bin/g++
  g++11: /usr/bin/g++
  g++14: /usr/bin/g++
  g++17: /usr/bin/g++
  g++20: /usr/bin/g++
  gcc: /usr/bin/gcc
  gcc11: /usr/bin/gcc
  ghc: /usr/bin/ghc
  go: /usr/bin/go
  java: /usr/lib/jvm/java-22-openjdk-amd64/bin/java
  java8: /usr/lib/jvm/java-8-openjdk-amd64/bin/java
  javac: /usr/lib/jvm/java-22-openjdk-amd64/bin/javac
  javac8: /usr/lib/jvm/java-8-openjdk-amd64/bin/javac
  ld_x64: /usr/bin/x86_64-linux-gnu-ld
  ld_x86: /usr/bin/ld
  llc: /usr/bin/llc
  mono: /usr/bin/mono
  mono-csc: /usr/bin/mono-csc
  mono-vbnc: /usr/bin/vbnc
  nasm: /usr/bin/nasm
  ocamlfind: /home/judge/.opam/dmoj/bin/ocamlfind
  opt: /usr/bin/opt
  perl: /usr/bin/perl
  pypy: /opt/pypy2/bin/pypy
  pypy3: /opt/pypy3/bin/pypy3
  python: /usr/bin/python2.7
  python3: /usr/bin/python3
  racket: /usr/bin/racket
  raco: /usr/bin/raco
  ruby: /usr/bin/ruby
  scala_args:
  - -Xbootclasspath/a:/usr/share/scala-2.11/lib/hawtjni-runtime.jar:/usr/share/scala-2.11/lib/jansi.jar:/usr/share/scala-2.11/lib/jline.jar:/usr/share/scala-2.11/lib/scala-actors.jar:/usr/share/scala-2.11/lib/scala-compiler.jar:/usr/share/scala-2.11/lib/scala-library.jar:/usr/share/scala-2.11/lib/scala-parser-combinators.jar:/usr/share/scala-2.11/lib/scala-reflect.jar:/usr/share/scala-2.11/lib/scala-xml.jar:/usr/share/scala-2.11/lib/scalap.jar
  - -classpath
  - '""'
  - -Dscala.boot.class.path=/usr/share/scala-2.11/lib/hawtjni-runtime.jar:/usr/share/scala-2.11/lib/jansi.jar:/usr/share/scala-2.11/lib/jline.jar:/usr/share/scala-2.11/lib/scala-actors.jar:/usr/share/scala-2.11/lib/scala-compiler.jar:/usr/share/scala-2.11/lib/scala-library.jar:/usr/share/scala-2.11/lib/scala-parser-combinators.jar:/usr/share/scala-2.11/lib/scala-reflect.jar:/usr/share/scala-2.11/lib/scala-xml.jar:/usr/share/scala-2.11/lib/scalap.jar
  - -Dscala.home=/usr/share/scala-2.11
  - -Dscala.usejavacp=true
  - -Denv.emacs=
  - scala.tools.nsc.MainGenericRunner
  scala_vm: /usr/lib/jvm/java-22-openjdk-amd64/bin/java
  scalac: /usr/bin/scalac
  sed: /usr/bin/sed
  v8dmoj: /usr/bin/v8dmoj
  crt_x86_in_lib32: true
EOF
    
    # Build judge-tier1 container nếu chưa có
    echo "[i] Đang biên dịch Docker Image cho máy chấm (judge-tier1)..."
    if [ "$use_docker_mysql" = "true" ] || [ "$use_docker_redis" = "true" ] || command -v docker >/dev/null 2>&1; then
      cd "$JUDGE_DIR/.docker"
      # Build image
      docker build --build-arg TAG="master" -t dmoj/judge-tier1 -t dmoj/judge-tier1:latest ./tier1 || true
      
      # Run container
      docker rm -f fptoj-judge >/dev/null 2>&1 || true
      docker run \
        --name fptoj-judge \
        -v "$data_dir/problems":/problems \
        --cap-add=SYS_PTRACE \
        --network host \
        -d \
        --restart=always \
        dmoj/judge-tier1:latest \
        run -p $judge_port -c /problems/judge.yml \
        127.0.0.1 "$judge_id" "$judge_key"
        
      echo "[✓] Máy chấm '$judge_id' đã được khởi chạy trong Docker!"
    else
      echo "[x] Lỗi: Docker chưa cài đặt. Không thể khởi chạy máy chấm Docker."
    fi
  else
    echo "[!] Không nhập Judge Key. Bỏ qua khởi chạy máy chấm tự động."
  fi
fi

# 17. KHỞI ĐỘNG LẠI TẤT CẢ DỊCH VỤ VÀ HOÀN TẤT
echo ""
echo "=== 10. KHỞI ĐỘNG LẠI DỊCH VỤ HỆ THỐNG ==="
systemctl daemon-reload

# Touch và phân quyền log trong thư mục logs trước khi Supervisor chạy
# để tránh lỗi không thể ghi log vì lỗi Permission
for logfile in site.stdout.log site.stderr.log bridge.stdout.log bridge.stderr.log wsevent.stdout.log wsevent.stderr.log celery.stdout.log celery.stderr.log html-to-pdf-flask_log.log html-to-pdf-flask.log; do
    touch "$SITE_DIR/logs/$logfile"
    chown $REAL_USER:$REAL_USER "$SITE_DIR/logs/$logfile"
    chmod 666 "$SITE_DIR/logs/$logfile"
done

# Đảm bảo bàn giao lại toàn bộ quyền sở hữu thư mục cho REAL_USER
chown -R $REAL_USER:$REAL_USER "$SITE_DIR"

# Khởi động lại Supervisor
if [ "$supervisor_on_host" = "true" ]; then
  systemctl restart supervisor
else
  systemctl enable supervisor
  systemctl start supervisor
fi
supervisorctl reread
supervisorctl update
supervisorctl restart all || true

# Khởi động lại Nginx
systemctl restart nginx

# Tạo file lưu trữ thông tin cấu hình cho người dùng
SETUP_INFO_FILE="$USER_HOME/fptoj_setup_info.txt"
cat << EOF > "$SETUP_INFO_FILE"
=== THÔNG TIN CÀI ĐẶT FPTOJ ===
Ngày cài đặt: $(date)
Tài khoản chạy hệ thống: $REAL_USER

1. THÔNG TIN TRANG WEB
Tên trang web: $site_name
Domain / IP: $allowed_hosts
Nginx Port: $nginx_port

2. THÔNG TIN DATABASE
Máy chủ Database: $db_host
Tên Database: $db_name
Người dùng Database: $db_user
Mật khẩu Database: $db_pass
$(if [ "$use_docker_mysql" = "true" ]; then echo "Mật khẩu ROOT MySQL: $db_root_pass"; fi)

3. THÔNG TIN EMAIL SMTP
Host: $email_host
Port: $email_port
User: $email_user
Pass: $email_pass
From: $email_from

4. THÔNG TIN MÁY CHẤM (JUDGE)
$(if [ "$setup_judge_ans" = "y" ] || [ "$setup_judge_ans" = "Y" ]; then
echo "Judge ID: $judge_id
Judge Key: $judge_key"
else
echo "Không cài đặt máy chấm tự động qua Docker."
fi)

5. API KEYS ĐÃ CUNG CẤP
Google OAuth2 Key: $google_oauth_key
Github OAuth2 Key: $github_oauth_key
Turnstile SiteKey: $turnstile_sitekey

* LƯU Ý: HÃY LƯU TRỮ FILE NÀY CẨN THẬN, NÓ CHỨA CÁC MẬT KHẨU NHẠY CẢM CỦA HỆ THỐNG!
EOF

chmod 600 "$SETUP_INFO_FILE"
chown $REAL_USER:$REAL_USER "$SETUP_INFO_FILE"

echo ""
echo "=============================================================================="
echo "    [✓] FPTOJ ĐÃ ĐƯỢC THIẾT LẬP VÀ CÀI ĐẶT THÀNH CÔNG!"
echo "=============================================================================="
echo "  * Giao diện site: http://localhost:$nginx_port hoặc địa chỉ IP máy chủ của bạn."
echo "  * FILE THÔNG TIN CÀI ĐẶT (QUAN TRỌNG): $SETUP_INFO_FILE"
echo "  * Trạng thái dịch vụ nền (Supervisor):"
supervisorctl status
echo "  * Dịch vụ PDF độc quyền: chạy trên http://127.0.0.1:$pdf_port"
echo "  * Dữ liệu đề bài lưu tại: $data_dir/problems"
echo "  * Truy cập nhanh MySQL Docker: chạy ./mysql_cli.sh"
echo "=============================================================================="
