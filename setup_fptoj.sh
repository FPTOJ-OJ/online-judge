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

# Phân tích tham số dòng lệnh
AUTO_CONFIRM_PROFILE=false
for arg in "$@"; do
  case "$arg" in
    --non-interactive|-y)
      AUTO_CONFIRM_PROFILE=true
      ;;
  esac
done

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

# Đưa ra profile khuyến nghị theo CPU + RAM
if [ "$total_mem" -lt 1500 ] || [ "$cpu_cores" -lt 2 ]; then
  PROFILE="MICRO"
  UWSGI_WORKERS=1
  CELERY_CONCURRENCY=1
  JUDGE_TIER="tier1"
  JUDGE_CONCURRENCY=1
  echo "[!] Nhận diện máy chủ cấu hình rất thấp (Micro). Đề xuất cấu hình tối giản nhất."
elif [ "$total_mem" -lt 3500 ] || [ "$cpu_cores" -lt 4 ]; then
  PROFILE="LIGHTWEIGHT"
  UWSGI_WORKERS=2
  CELERY_CONCURRENCY=1
  JUDGE_TIER="tier1"
  JUDGE_CONCURRENCY=2
  echo "[!] Nhận diện máy chủ cấu hình thấp (Lightweight). Dùng Tier 1, 2 workers."
elif [ "$total_mem" -lt 8000 ] || [ "$cpu_cores" -lt 8 ]; then
  PROFILE="MEDIUM"
  UWSGI_WORKERS=4
  CELERY_CONCURRENCY=2
  JUDGE_TIER="tier2"
  JUDGE_CONCURRENCY=4
  echo "[!] Nhận diện máy chủ cấu hình trung bình (Medium). Dùng Tier 2, 4 workers."
elif [ "$total_mem" -lt 24000 ] || [ "$cpu_cores" -lt 16 ]; then
  PROFILE="PRODUCTION"
  UWSGI_WORKERS=8
  CELERY_CONCURRENCY=4
  JUDGE_TIER="tier3"
  JUDGE_CONCURRENCY=8
  echo "[!] Nhận diện máy chủ cấu hình cao (Production). Dùng Tier 3, 8 workers."
else
  PROFILE="HIGHEND"
  UWSGI_WORKERS=16
  CELERY_CONCURRENCY=8
  JUDGE_TIER="tier3"
  JUDGE_CONCURRENCY=$((cpu_cores / 2))
  echo "[!] Nhận diện máy chủ cấu hình rất cao (High-End). Dùng Tier 3, $JUDGE_CONCURRENCY workers."
fi
echo "[i] Profile: $PROFILE | uWSGI: $UWSGI_WORKERS workers | Celery: $CELERY_CONCURRENCY | Judge Tier: $JUDGE_TIER, $JUDGE_CONCURRENCY concurrent"

# Kiểm tra dung lượng ổ cứng còn trống tối thiểu
echo ""
echo "=== KIỂM TRA DUNG LƯỢNG Ổ CỨNG ==="
avail_disk_gb=$(df -BG / | awk 'NR==2{gsub("G","",$4); print $4}')
echo "[i] Dung lượng trống ở /: ${avail_disk_gb} GB"
if [ "$avail_disk_gb" -lt 10 ]; then
  echo "[x] Lỗi nghiêm trọng: Ổ cứng chỉ còn ${avail_disk_gb} GB - Cần ít nhất 10 GB để cài đặt!" >&2
  echo "[i] Hãy dọn dập hoặc mở rộng ổ cứng trước khi tiếp tục." >&2
  exit 1
elif [ "$avail_disk_gb" -lt 20 ]; then
  echo "[!] Cảnh báo: Chỉ còn ${avail_disk_gb} GB. Khử́ng nên chạy máy chấm có nhiều đề bài lớn (khuyến nghị >= 20 GB)."
else
  echo "[✓] Dung lượng ổ cứng đủ điều kiện."
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

# KHỞI TẠO CẤU HÌNH TỪ HƯỚNG CÀI ĐẶT ĐỀ XUẤT
CHOSEN_PROFILE=$PROFILE
CHOSEN_UWSGI_WORKERS=$UWSGI_WORKERS
CHOSEN_CELERY_CONCURRENCY=$CELERY_CONCURRENCY
CHOSEN_JUDGE_TIER=$JUDGE_TIER
CHOSEN_NUM_JUDGES=$JUDGE_CONCURRENCY

if [ "$AUTO_CONFIRM_PROFILE" = "false" ]; then
  while true; do
    echo ""
    echo "======================================================================"
    echo "                 BẢNG CẤU HÌNH HỆ THỐNG ĐỀ XUẤT"
    echo "======================================================================"
    echo " Cấu hình phần cứng phát hiện:"
    echo "   - Số nhân CPU: $cpu_cores cores"
    echo "   - Dung lượng RAM: ${total_mem} MB"
    echo "   - Dung lượng ổ cứng trống ở /: ${avail_disk_gb} GB"
    echo ""
    echo " Dịch vụ đang chạy trên Host:"
    echo "   - MySQL/MariaDB: $([ "$mysql_on_host" = "true" ] && echo "Đã tìm thấy" || echo "Không tìm thấy")"
    echo "   - Redis:         $([ "$redis_on_host" = "true" ] && echo "Đã tìm thấy" || echo "Không tìm thấy")"
    echo "   - Nginx:         $([ "$nginx_on_host" = "true" ] && echo "Đã tìm thấy" || echo "Không tìm thấy")"
    echo "   - Supervisor:    $([ "$supervisor_on_host" = "true" ] && echo "Đã tìm thấy" || echo "Không tìm thấy")"
    echo ""
    echo " Lựa chọn cấu hình cài đặt hiện tại:"
    echo "   [1] Profile hệ thống:          $CHOSEN_PROFILE"
    echo "   [2] Số uWSGI workers:          $CHOSEN_UWSGI_WORKERS workers"
    echo "   [3] Celery concurrency:        $CHOSEN_CELERY_CONCURRENCY workers"
    echo "   [4] Tier máy chấm (Judge Tier): $CHOSEN_JUDGE_TIER"
    echo "   [5] Số lượng máy chấm (Judges): $CHOSEN_NUM_JUDGES máy"
    echo "======================================================================"
    echo ""
    
    read -p "[?] Bạn có đồng ý với cấu hình trên không? (y/n) [y]: " confirm_conf
    confirm_conf=${confirm_conf:-y}
    
    if [ "$confirm_conf" = "y" ] || [ "$confirm_conf" = "Y" ]; then
      break
    fi
    
    echo ""
    echo "--- CẤU HÌNH THỦ CÔNG HỆ THỐNG ---"
    echo "[?] Chọn Profile hệ thống để reset cấu hình nhanh:"
    echo "   1) MICRO       (uWSGI: 1, Celery: 1, Tier: tier1, Judges: 1)"
    echo "   2) LIGHTWEIGHT (uWSGI: 2, Celery: 1, Tier: tier1, Judges: 2)"
    echo "   3) MEDIUM      (uWSGI: 4, Celery: 2, Tier: tier2, Judges: 4)"
    echo "   4) PRODUCTION  (uWSGI: 8, Celery: 4, Tier: tier3, Judges: 8)"
    echo "   5) HIGHEND     (uWSGI: 16, Celery: 8, Tier: tier3, Judges: $((cpu_cores / 2)))"
    echo "   6) Giữ cấu hình hiện tại ($CHOSEN_PROFILE)"
    read -p "Lựa chọn (1-6) [6]: " prof_choice
    prof_choice=${prof_choice:-6}
    
    case "$prof_choice" in
      1)
        CHOSEN_PROFILE="MICRO"
        CHOSEN_UWSGI_WORKERS=1
        CHOSEN_CELERY_CONCURRENCY=1
        CHOSEN_JUDGE_TIER="tier1"
        CHOSEN_NUM_JUDGES=1
        ;;
      2)
        CHOSEN_PROFILE="LIGHTWEIGHT"
        CHOSEN_UWSGI_WORKERS=2
        CHOSEN_CELERY_CONCURRENCY=1
        CHOSEN_JUDGE_TIER="tier1"
        CHOSEN_NUM_JUDGES=2
        ;;
      3)
        CHOSEN_PROFILE="MEDIUM"
        CHOSEN_UWSGI_WORKERS=4
        CHOSEN_CELERY_CONCURRENCY=2
        CHOSEN_JUDGE_TIER="tier2"
        CHOSEN_NUM_JUDGES=4
        ;;
      4)
        CHOSEN_PROFILE="PRODUCTION"
        CHOSEN_UWSGI_WORKERS=8
        CHOSEN_CELERY_CONCURRENCY=4
        CHOSEN_JUDGE_TIER="tier3"
        CHOSEN_NUM_JUDGES=8
        ;;
      5)
        CHOSEN_PROFILE="HIGHEND"
        CHOSEN_UWSGI_WORKERS=16
        CHOSEN_CELERY_CONCURRENCY=8
        CHOSEN_JUDGE_TIER="tier3"
        CHOSEN_NUM_JUDGES=$((cpu_cores / 2))
        [ "$CHOSEN_NUM_JUDGES" -lt 1 ] && CHOSEN_NUM_JUDGES=1
        ;;
    esac
    
    read -p "[?] Bạn có muốn tùy chỉnh chi tiết từng thông số không? (y/n) [n]: " detail_choice
    detail_choice=${detail_choice:-n}
    if [ "$detail_choice" = "y" ] || [ "$detail_choice" = "Y" ]; then
      read -p " - Nhập số lượng uWSGI workers [$CHOSEN_UWSGI_WORKERS]: " opt_uwsgi
      CHOSEN_UWSGI_WORKERS=${opt_uwsgi:-$CHOSEN_UWSGI_WORKERS}
      
      read -p " - Nhập Celery concurrency [$CHOSEN_CELERY_CONCURRENCY]: " opt_celery
      CHOSEN_CELERY_CONCURRENCY=${opt_celery:-$CHOSEN_CELERY_CONCURRENCY}
      
      echo " - Chọn Tier máy chấm (Judge Tier):"
      echo "   1) tier1"
      echo "   2) tier2"
      echo "   3) tier3"
      read -p "Lựa chọn (1-3) [$(echo $CHOSEN_JUDGE_TIER | sed 's/tier//')]: " opt_tier_choice
      case "$opt_tier_choice" in
        1) CHOSEN_JUDGE_TIER="tier1" ;;
        2) CHOSEN_JUDGE_TIER="tier2" ;;
        3) CHOSEN_JUDGE_TIER="tier3" ;;
      esac
      
      read -p " - Nhập số lượng máy chấm (N) [$CHOSEN_NUM_JUDGES]: " opt_num_judges
      CHOSEN_NUM_JUDGES=${opt_num_judges:-$CHOSEN_NUM_JUDGES}
    fi
  done
fi

# Áp dụng các cấu hình đã lựa chọn vào các biến chạy thực tế của script
PROFILE=$CHOSEN_PROFILE
UWSGI_WORKERS=$CHOSEN_UWSGI_WORKERS
CELERY_CONCURRENCY=$CHOSEN_CELERY_CONCURRENCY
JUDGE_TIER=$CHOSEN_JUDGE_TIER
JUDGE_CONCURRENCY=$CHOSEN_NUM_JUDGES
NUM_JUDGES=$CHOSEN_NUM_JUDGES

# 4. TRÌNH PHÂN TÍCH CẤU HÌNH CŨ (ĐỌC DEFAULTS TỪ LOCAL_SETTINGS.PY NẾU CÓ)
parse_setting() {
  local key="$1"
  local default_val="$2"
  if [ -f "$SITE_DIR/dmoj/local_settings.py" ]; then
    PARSE_KEY="$key" PARSE_FILE="$SITE_DIR/dmoj/local_settings.py" PARSE_DEFAULT="$default_val" \
      python3 - <<'PYEOF' 2>/dev/null
import re, os
key = os.environ['PARSE_KEY']
fpath = os.environ['PARSE_FILE']
default = os.environ['PARSE_DEFAULT']
try:
    with open(fpath) as f:
        content = f.read()
    pattern = r'^\s*' + re.escape(key) + r'\s*=\s*(?:["\x27](.*?)["\x27]|(\d+))'
    val = re.search(pattern, content, re.MULTILINE)
    if val:
        res = val.group(1) or val.group(2)
        if res is not None:
            print(res)
            exit(0)
except Exception:
    pass
print(default)
PYEOF
  else
    echo "$default_val"
  fi
}

parse_db_setting() {
  local key="$1"
  local default_val="$2"
  if [ -f "$SITE_DIR/dmoj/local_settings.py" ]; then
    PARSE_KEY="$key" PARSE_FILE="$SITE_DIR/dmoj/local_settings.py" PARSE_DEFAULT="$default_val" \
      python3 - <<'PYEOF' 2>/dev/null
import re, os
key = os.environ['PARSE_KEY']
fpath = os.environ['PARSE_FILE']
default = os.environ['PARSE_DEFAULT']
try:
    with open(fpath) as f:
        content = f.read()
    db_block = re.search(r'DATABASES\s*=\s*\{.*?\}', content, re.DOTALL)
    if db_block:
        pattern = r'["\x27]' + re.escape(key) + r'["\x27]\s*:\s*["\x27](.*?)["\x27]'
        val = re.search(pattern, db_block.group(0))
        if val:
            print(val.group(1))
            exit(0)
except Exception:
    pass
print(default)
PYEOF
  else
    echo "$default_val"
  fi
}

parse_judge_ip() {
  local default_ip="127.0.0.1"
  if [ -f "$SITE_DIR/dmoj/local_settings.py" ]; then
    PARSE_FILE="$SITE_DIR/dmoj/local_settings.py" PARSE_DEFAULT="$default_ip" \
      python3 - <<'PYEOF' 2>/dev/null
import re, os
fpath = os.environ['PARSE_FILE']
default = os.environ['PARSE_DEFAULT']
try:
    with open(fpath) as f:
        content = f.read()
    match = re.search(r'BRIDGED_JUDGE_ADDRESS\s*=\s*\[\s*\(\s*["\x27]([^"\x27]+)["\x27]\s*,\s*(\d+)\s*\)', content)
    if match:
        ip = match.group(1)
        if ip == '0.0.0.0':
            print('127.0.0.1')
        else:
            print(ip)
        exit(0)
except Exception:
    pass
print(default)
PYEOF
  else
    echo "$default_ip"
  fi
}

# 5. HƯỚNG DẪN TƯƠNG TÁC NHẬP THÔNG TIN CẤU HÌNH
echo ""
echo "=== HƯỚNG DẪN THIẾT LẬP CẤU HÌNH (Bấm Enter để lấy mặc định) ==="

# Kiểm tra cài đặt hiện có -> hỏi cập nhật trước khi prompt
UPDATE_MODE=false
KEEP_LOCAL_SETTINGS=false

if [ -f "$SITE_DIR/dmoj/local_settings.py" ] && [ -f "$SITE_DIR/dmoj/celery.py" ]; then
    echo ""
    echo "[i] Phát hiện hệ thống đã được cài đặt trước đó."
    echo ""
    echo "    Chọn chế độ:"
    echo "    1) Cập nhật đầy đủ  - Ghi đè local_settings.py (giữ SECRET_KEY cũ + DB),"
    echo "                           cập nhật supervisor, biên dịch assets, restart dịch vụ."
    echo "    2) Giữ nguyên cấu hình - Chỉ cập nhật supervisor, assets, restart."
    echo "                           local_settings.py và DB được giữ nguyên 100%."
    echo "    3) Cài đặt mới     - Chạy toàn bộ tiến trình cài đặt từ đầu."
    echo ""
    read -p "[?] Nhập lựa chọn (1/2/3) [1]: " update_choice
    update_choice=${update_choice:-1}
    case "$update_choice" in
        1)
            UPDATE_MODE=true
            KEEP_LOCAL_SETTINGS=false
            OLD_SECRET_KEY=$(parse_setting "SECRET_KEY" "")
            echo "[i] Cập nhật đầy đủ: ghi đè local_settings.py, giữ DB + SECRET_KEY."
            ;;
        2)
            UPDATE_MODE=true
            KEEP_LOCAL_SETTINGS=true
            echo "[i] Giữ nguyên local_settings.py, chỉ cập nhật cấu hình hệ thống."
            ;;
        *)
            UPDATE_MODE=false
            KEEP_LOCAL_SETTINGS=false
            echo "[i] Cài đặt mới hoàn toàn."
            ;;
    esac
fi

if [ "$KEEP_LOCAL_SETTINGS" = "true" ]; then
    # Tự động đọc cấu hình cũ mà không cần hỏi lại người dùng
    site_name=$(parse_setting "SITE_NAME" "FPTOJ")
    site_long_name=$(parse_setting "SITE_LONG_NAME" "FPTOJ: FPT Online Judge")
    allowed_hosts=$(parse_setting "ALLOWED_HOSTS" "localhost")
    db_host=$(parse_db_setting "HOST" "127.0.0.1")
    db_port=$(parse_db_setting "PORT" "3306")
    db_name=$(parse_db_setting "NAME" "dmoj")
    db_user=$(parse_db_setting "USER" "dmoj")
    db_pass=$(parse_db_setting "PASSWORD" "")
    email_host=$(parse_setting "EMAIL_HOST" "")
    email_port=$(parse_setting "EMAIL_PORT" "587")
    email_user=$(parse_setting "EMAIL_HOST_USER" "")
    email_pass=$(parse_setting "EMAIL_HOST_PASSWORD" "")
    email_from=$(parse_setting "DEFAULT_FROM_EMAIL" "")
    google_oauth_key=$(parse_setting "SOCIAL_AUTH_GOOGLE_OAUTH2_KEY" "")
    google_oauth_secret=$(parse_setting "SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET" "")
    github_oauth_key=$(parse_setting "SOCIAL_AUTH_GITHUB_SECURE_KEY" "")
    github_oauth_secret=$(parse_setting "SOCIAL_AUTH_GITHUB_SECURE_SECRET" "")
    turnstile_sitekey=$(parse_setting "TURNSTILE_SITEKEY" "")
    turnstile_secret=$(parse_setting "TURNSTILE_SECRET" "")
    
    problems_root=$(parse_setting "DMOJ_PROBLEM_DATA_ROOT" "/data/problems")
    data_dir=$(echo "$problems_root" | sed -e 's|/problems/\?$||')
    data_dir=${data_dir:-/data}
else
    # Tiến trình nhập cấu hình chuẩn của script
    OLD_SITE_NAME=$(parse_setting "SITE_NAME" "FPTOJ")
    OLD_HOSTS=$(parse_setting "ALLOWED_HOSTS" "fptoj.com,www.fptoj.com,127.0.0.1")
    OLD_DB_HOST=$(parse_db_setting "HOST" "127.0.0.1")
    OLD_DB_NAME=$(parse_db_setting "NAME" "dmoj")
    OLD_DB_USER=$(parse_db_setting "USER" "dmoj")
    OLD_DB_PASS=$(parse_db_setting "PASSWORD" "12345678")

    OLD_EMAIL_HOST=$(parse_setting "EMAIL_HOST" "")
    OLD_EMAIL_PORT=$(parse_setting "EMAIL_PORT" "587")
    OLD_EMAIL_USER=$(parse_setting "EMAIL_HOST_USER" "")
    OLD_EMAIL_PASS=$(parse_setting "EMAIL_HOST_PASSWORD" "")
    OLD_EMAIL_FROM=$(parse_setting "DEFAULT_FROM_EMAIL" "")

    read -p "[?] Tên trang web Online Judge của bạn [$OLD_SITE_NAME]: " site_name
    site_name=${site_name:-$OLD_SITE_NAME}

    OLD_SITE_LONG_NAME=$(parse_setting "SITE_LONG_NAME" "${site_name}: FPT Online Judge")
    read -p "[?] Tên dài (long name) hiển thị trên trang web [$OLD_SITE_LONG_NAME]: " site_long_name
    site_long_name=${site_long_name:-$OLD_SITE_LONG_NAME}

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
    echo "[i] Thiết lập Email SMTP (Để trống nếu không dùng - cấu hình lại sau ở local_settings.py)"
    read -p "[?] Địa chỉ máy chủ SMTP Mail [$OLD_EMAIL_HOST]: " email_host
    email_host=${email_host:-$OLD_EMAIL_HOST}
    if [ -n "$email_host" ]; then
        read -p "[?] Cổng SMTP (thường là 587 hoặc 465) [$OLD_EMAIL_PORT]: " email_port
        email_port=${email_port:-${OLD_EMAIL_PORT:-587}}
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
fi

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
apt-get install -y git gcc g++ make python3-dev python3-pip python3-venv libxml2-dev libxslt1-dev zlib1g-dev gettext curl supervisor nginx wkhtmltopdf lsof pkg-config default-libmysqlclient-dev

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

# Cài đặt thư viện trực tiếp vào môi trường ảo thông qua module pip của môi trường ảo
"$SITE_DIR/dmojsite/bin/python" -m pip install --upgrade pip
"$SITE_DIR/dmojsite/bin/python" -m pip install -r "$SITE_DIR/requirements.txt"
"$SITE_DIR/dmojsite/bin/python" -m pip install mysqlclient uwsgi pymysql redis

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

if [ "$KEEP_LOCAL_SETTINGS" = "true" ]; then
    echo "[i] Giữ nguyên file local_settings.py hiện có."
else
    cat << EOF > "$SITE_DIR/dmoj/local_settings.py"
# Sinh tự động bởi setup_fptoj.sh vào $(date)
import datetime
import os

SECRET_KEY = '${OLD_SECRET_KEY:-$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")}'
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
        'NAME': os.environ.get('MYSQL_DATABASE', '$db_name'),
        'USER': os.environ.get('MYSQL_USER', '$db_user'),
        'PASSWORD': os.environ.get('MYSQL_PASSWORD', '$db_pass'),
        'HOST': os.environ.get('MYSQL_HOST', '$db_host'),
        'PORT': os.environ.get('MYSQL_PORT', '$db_port'),
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
SITE_LONG_NAME = '$site_long_name'
SITE_ADMIN_EMAIL = '$admin_email'
TERMS_OF_SERVICE_URL = '/about/tos/'

# Cấu hình máy chấm kết nối
BRIDGED_JUDGE_ADDRESS = [('0.0.0.0', $judge_port)]
DMOJ_PROBLEM_DATA_ROOT = "$data_dir/problems"

# Event Server
EVENT_DAEMON_USE = True
EVENT_DAEMON_POST = os.environ.get('EVENT_DAEMON_POST', 'ws://127.0.0.1:$wsevent_post_port/')
EVENT_DAEMON_GET = os.environ.get('EVENT_DAEMON_GET', 'ws://$first_host/event/')
EVENT_DAEMON_GET_SSL = os.environ.get('EVENT_DAEMON_GET_SSL', 'wss://$first_host/event/')
EVENT_DAEMON_POLL = '/channels/'

# Celery Broker
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:$redis_port/0')
# result_backend is derived from broker_url in dmoj/celery.py

ACE_URL = '/static/vendor/ace/'
JQUERY_JS = '/static/vendor/jquery-3.4.1.min.js'
SELECT2_JS_URL = '/static/vendor/select2/select2.js'
SELECT2_CSS_URL = '/static/vendor/select2/select2.css'

TIMEZONE_MAP = 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Blue_Marble_2002.png/1024px-Blue_Marble_2002.png'

DMOJ_HTTPS = 2

# Xuất PDF
DMOJ_PDF_PDFOID_URL = os.environ.get('DMOJ_PDF_PDFOID_URL', 'http://localhost:$pdf_port')
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
fi

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
git config --global --add safe.directory "$SITE_DIR" || true
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
"$SITE_DIR/dmojsite/bin/python" manage.py collectstatic --no-input
"$SITE_DIR/dmojsite/bin/python" manage.py compilemessages -i dmojsite
"$SITE_DIR/dmojsite/bin/python" manage.py compilejsi18n

# 12. KHỞI TẠO CSDL VÀ NAP DỮ LIỆU
echo ""
echo "=== 5. KHỞI TẠO CƠ SỞ DỮ LIỆU ==="
if [ "$UPDATE_MODE" = "true" ]; then
    echo "[i] Chế độ cập nhật: migrate để đồng bộ schema mới (nếu có), giữ nguyên dữ liệu."
fi
"$SITE_DIR/dmojsite/bin/python" manage.py migrate
if [ "$UPDATE_MODE" != "true" ]; then
    "$SITE_DIR/dmojsite/bin/python" manage.py loaddata navbar
    "$SITE_DIR/dmojsite/bin/python" manage.py loaddata language_small
    "$SITE_DIR/dmojsite/bin/python" manage.py loaddata demo
fi

# Tạo superuser
if [ "$UPDATE_MODE" != "true" ]; then
    read -p "[?] Bạn có muốn tạo một tài khoản Admin mới? (y/n) [n]: " create_admin_ans
    create_admin_ans=${create_admin_ans:-n}
else
    create_admin_ans="n"
fi
if [ "$create_admin_ans" = "y" ] || [ "$create_admin_ans" = "Y" ]; then
  "$SITE_DIR/dmojsite/bin/python" manage.py createsuperuser
fi

# Tự động đăng ký các Judge vào DMOJ database
echo "[i] Đang đăng ký $NUM_JUDGES máy chấm vào cơ sở dữ liệu DMOJ..."
read -p "[?] Tên định danh máy chấm (Judge ID) [judge-01]: " judge_id
judge_id=${judge_id:-judge-01}

rm -f /tmp/fptoj_judges.txt
JUDGES_INFO=""

for i in $(seq 1 $NUM_JUDGES); do
  if [ "$NUM_JUDGES" -eq 1 ]; then
    current_id="$judge_id"
  else
    current_id="${judge_id}-${i}"
  fi
  
  # Tạo key ngẫu nhiên đề phòng tạo mới
  fallback_key=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "judge-key-auto-${i}")
  
  # Đăng ký hoặc kiểm tra Judge trong DB, trả về key tương ứng
  django_output=$("$SITE_DIR/dmojsite/bin/python" manage.py shell -c "
from judge.models import Judge
try:
    if not Judge.objects.filter(name='$current_id').exists():
        j = Judge(name='$current_id', auth_key='$fallback_key', is_blocked=False)
        j.save()
        print('STATUS:CREATED:' + '$fallback_key')
    else:
        j = Judge.objects.get(name='$current_id')
        print('STATUS:EXISTING:' + j.auth_key)
except Exception as e:
    print('STATUS:ERROR:' + str(e))
" 2>/dev/null || echo "")

  actual_key=""
  if echo "$django_output" | grep -q "^STATUS:CREATED:"; then
    actual_key=$(echo "$django_output" | grep "^STATUS:CREATED:" | cut -d':' -f3)
    echo "[✓] Đã đăng ký Judge mới: $current_id"
  elif echo "$django_output" | grep -q "^STATUS:EXISTING:"; then
    actual_key=$(echo "$django_output" | grep "^STATUS:EXISTING:" | cut -d':' -f3)
    echo "[✓] Giữ nguyên thông tin Judge đã có: $current_id"
  else
    actual_key="$fallback_key"
    echo "[!] Không thể truy cập DB hoặc xảy ra lỗi, sử dụng key tạm cho: $current_id"
  fi

  echo "${current_id}:${actual_key}" >> /tmp/fptoj_judges.txt
  JUDGES_INFO="${JUDGES_INFO} - Judge ID: $current_id | Key: $actual_key"$'\n'
done

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
command=$SITE_DIR/dmojsite/bin/celery -A dmoj worker -l info --concurrency=$CELERY_CONCURRENCY
directory=$SITE_DIR
user=$REAL_USER
group=$REAL_USER
stdout_logfile=$SITE_DIR/logs/celery.stdout.log
stderr_logfile=$SITE_DIR/logs/celery.stderr.log
autorestart=true
environment=PYTHONUNBUFFERED=1
stdout_logfile_maxbytes=10MB
stderr_logfile_maxbytes=10MB
stdout_logfile_backups=5
stderr_logfile_backups=5
EOF

echo "[✓] Đã ghi các file cấu hình Supervisor (site, bridged, wsevent, celery)."

# 14. CẤU HÌNH DỊCH VỤ XUẤT PDF (html-to-pdf-flask)
echo ""
echo "=== 7. CẤU HÌNH DỊCH VỤ XUẤT PDF ==="
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

configure_nginx=true
if [ "$UPDATE_MODE" = "true" ]; then
    echo ""
    read -p "[?] Phát hiện chế độ cập nhật. Bạn có muốn thiết lập lại cấu hình Nginx gốc của FPTOJ? (y/n) [n]: " setup_nginx_ans
    setup_nginx_ans=${setup_nginx_ans:-n}
    if [ "$setup_nginx_ans" != "y" ] && [ "$setup_nginx_ans" != "Y" ]; then
        configure_nginx=false
        echo "[i] Bỏ qua cấu hình lại Nginx để tránh ghi đè các cấu hình tùy chỉnh (SSL, Cloudflare, v.v.)."
    fi
fi

if [ "$configure_nginx" = "true" ]; then
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
        proxy_buffering off;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
        proxy_connect_timeout 75s;

        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
    }

    location /channels/ {
        proxy_read_timeout          120s;
        proxy_pass http://127.0.0.1:$wsevent_http_port;

        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    # Active cấu hình Nginx
    rm -f /etc/nginx/sites-enabled/default
    ln -sf "$nginx_conf" /etc/nginx/sites-enabled/fptoj
fi

# Cấu hình Firewall (UFW) nếu có
if command -v ufw >/dev/null 2>&1; then
  if ufw status | grep -q "Status: active"; then
    echo "[i] Phát hiện UFW đang hoạt động. Tiến hành mở các cổng dịch vụ cần thiết..."
    echo "[i] Mở cổng kết nối máy chấm Bridge (Port $judge_port/tcp)..."
    ufw allow $judge_port/tcp || true
    echo "[i] Mở cổng Web Server Nginx (Port $nginx_port/tcp)..."
    ufw allow $nginx_port/tcp || true
    echo "[i] Mở thông tuyến cho interface docker0 để máy chấm kết nối về host..."
    ufw allow in on docker0 || true
    ufw allow out on docker0 || true
    ufw reload || true
  fi
fi

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

  # Nếu file danh sách máy chấm chưa được tạo ở Section 12, tạo mặc định 1 máy chấm
  if [ ! -f /tmp/fptoj_judges.txt ]; then
    judge_id=${judge_id:-judge-01}
    judge_key=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "judge-key-auto")
    echo "${judge_id}:${judge_key}" >> /tmp/fptoj_judges.txt
    JUDGES_INFO=" - Judge ID: $judge_id | Key: $judge_key"$'\n'
  fi

  # Build judge container theo JUDGE_TIER nếu chưa có
  echo "[i] Đang biên dịch Docker Image cho máy chấm (judge-$JUDGE_TIER)..."
  if [ "$use_docker_mysql" = "true" ] || [ "$use_docker_redis" = "true" ] || command -v docker >/dev/null 2>&1; then
    cd "$JUDGE_DIR/.docker"
    # Build image với tag là dmoj/judge-$JUDGE_TIER
    docker build --build-arg TAG="master" -t dmoj/judge-$JUDGE_TIER -t dmoj/judge-$JUDGE_TIER:latest ./$JUDGE_TIER || true
    
    # Dọn dẹp các container máy chấm cũ
    echo "[i] Đang dọn dẹp các container máy chấm cũ..."
    docker ps -a --filter "name=fptoj-judge" --format "{{.Names}}" | xargs -r docker rm -f >/dev/null 2>&1 || true
    
    # Khởi chạy các container máy chấm
    local_idx=1
    connect_ip=$(parse_judge_ip)
    while IFS=':' read -r current_id current_key; do
      if [ -z "$current_id" ]; then continue; fi
      
      # Viết cấu hình judge.yml cho máy chấm hiện tại (tạo file judge.yml dùng chung)
      if [ "$local_idx" -eq 1 ]; then
        mkdir -p "$data_dir/problems"
        echo "[i] Tạo cấu hình judge.yml cho máy chấm tại $data_dir/problems/judge.yml"
        cat << EOF > "$data_dir/problems/judge.yml"
problem_storage_globs:
  - /problems/*
EOF
      fi

      echo "[i] Đang khởi chạy Docker Container 'fptoj-judge-${local_idx}' cho Judge ID '$current_id'..."
      docker run \
        --name "fptoj-judge-${local_idx}" \
        -v "$data_dir/problems":/problems:ro \
        --cap-add=SYS_PTRACE \
        --network host \
        -d \
        --restart=always \
        dmoj/judge-$JUDGE_TIER:latest \
        run -p $judge_port -c /problems/judge.yml \
        $connect_ip "$current_id" "$current_key"
        
      echo "[✓] Máy chấm '$current_id' đã được khởi chạy thành công!"
      local_idx=$((local_idx + 1))
    done < /tmp/fptoj_judges.txt

    rm -f /tmp/fptoj_judges.txt
    cd "$SITE_DIR"
  else
    echo "[x] Lỗi: Docker chưa cài đặt. Không thể khởi chạy máy chấm Docker."
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
echo "$JUDGES_INFO"
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
echo "  * Dịch vụ PDF: chạy trên http://127.0.0.1:$pdf_port"
echo "  * Dữ liệu đề bài lưu tại: $data_dir/problems"
echo "  * Truy cập nhanh MySQL Docker: chạy ./mysql_cli.sh"
echo "=============================================================================="
