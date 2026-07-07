#!/usr/bin/env bash
# Script hỗ trợ truy cập nhanh giao diện dòng lệnh MySQL bên trong Docker của FPTOJ

# Kiểm tra Docker
if ! command -v docker >/dev/null 2>&1; then
    echo "[x] Lỗi: Máy chủ chưa được cài đặt Docker."
    exit 1
fi

# Kiểm tra xem Container MySQL có tồn tại không
if ! docker ps -a --format '{{.Names}}' | grep -q '^fptoj-mysql$'; then
    echo "[x] Lỗi: Không tìm thấy Docker Container 'fptoj-mysql'."
    echo "[i] Có vẻ như bạn chưa chạy cài đặt FPTOJ bằng Docker MySQL, hoặc container đã bị xóa."
    exit 1
fi

# Kiểm tra xem Container MySQL có đang chạy không
if ! docker ps --format '{{.Names}}' | grep -q '^fptoj-mysql$'; then
    echo "[!] Cảnh báo: Container 'fptoj-mysql' đang dừng."
    read -p "[?] Bạn có muốn khởi động lại container này không? (y/n) [y]: " start_ans
    start_ans=${start_ans:-y}
    if [ "$start_ans" = "y" ] || [ "$start_ans" = "Y" ]; then
        echo "[i] Đang khởi động 'fptoj-mysql'..."
        docker start fptoj-mysql
        sleep 2
    else
        echo "[x] Thao tác bị hủy. Không thể kết nối đến database đang dừng."
        exit 1
    fi
fi

# Đọc thông tin cấu hình từ local_settings.py
LOCAL_SETTINGS="dmoj/local_settings.py"
if [ ! -f "$LOCAL_SETTINGS" ]; then
    echo "[x] Lỗi: Không tìm thấy file cấu hình '$LOCAL_SETTINGS'."
    echo "[i] Vui lòng chạy setup_fptoj.sh trước."
    exit 1
fi

echo "[i] Đang đọc cấu hình kết nối từ $LOCAL_SETTINGS..."
db_name=$(python3 -c "import re; m = re.search(r'[\"\']NAME[\"\']\s*:\s*[\"\'](.*?)[\"\']', open('$LOCAL_SETTINGS').read()); print(m.group(1)) if m else print('')" 2>/dev/null)
db_user=$(python3 -c "import re; m = re.search(r'[\"\']USER[\"\']\s*:\s*[\"\'](.*?)[\"\']', open('$LOCAL_SETTINGS').read()); print(m.group(1)) if m else print('')" 2>/dev/null)
db_pass=$(python3 -c "import re; m = re.search(r'[\"\']PASSWORD[\"\']\s*:\s*[\"\'](.*?)[\"\']', open('$LOCAL_SETTINGS').read()); print(m.group(1)) if m else print('')" 2>/dev/null)

if [ -z "$db_name" ] || [ -z "$db_user" ]; then
    echo "[x] Lỗi: Không thể đọc tên database hoặc user từ local_settings.py."
    exit 1
fi

echo "======================================================================"
echo "  Kết nối đến Database: $db_name (User: $db_user)"
echo "  Nhấn Ctrl+D hoặc gõ 'exit' để thoát khỏi MySQL CLI."
echo "======================================================================"
echo ""

# Chạy MySQL CLI bên trong container
docker exec -it fptoj-mysql mysql -u"$db_user" -p"$db_pass" "$db_name"
