# Hướng dẫn Khởi chạy FPTOJ bằng Docker Compose (Tier 1-3)

Thư mục này chứa cấu hình Docker Compose đầy đủ cho cả 3 cấp độ cấu hình máy chủ từ yếu đến mạnh. Tất cả các dịch vụ (Web, DB, Redis, Celery, Websocket, Nginx, Judge) đều được đóng gói độc lập.

---

## 📂 Danh sách các file cấu hình

1. **[Dockerfile](Dockerfile)**: Dockerfile đa giai đoạn biên dịch static assets và đóng gói toàn bộ mã nguồn Django/Python/NodeJS cho web, worker, websocket, bridged.
2. **[nginx.conf](nginx.conf)**: Cấu hình proxy ngược Nginx chia tĩnh và điều hướng Websocket kết nối event server.
3. **[.env.example](.env.example)**: File mẫu cấu hình biến môi trường hệ thống.
4. **[docker-compose.tier1.yml](docker-compose.tier1.yml)**: Dành cho máy chủ cấu hình yếu (DB nhẹ MariaDB, 2 uWSGI Web workers, Celery concurrency 1, 1 máy chấm `tier1`).
5. **[docker-compose.tier2.yml](docker-compose.tier2.yml)**: Dành cho máy chủ cấu hình trung bình (MySQL 8.0, 4 uWSGI Web workers, Celery concurrency 2, 2 máy chấm `tier2`).
6. **[docker-compose.tier3.yml](docker-compose.tier3.yml)**: Dành cho máy chủ mạnh / Production (MySQL tối ưu cache, 8 uWSGI Web workers, Celery concurrency 4, 4 máy chấm `tier3`).

---

## 🚀 Hướng dẫn Cài đặt & Khởi chạy nhanh

### Bước 1: Sao chép cấu hình biến môi trường
Tại thư mục `docker/`, tiến hành copy file `.env.example` thành `.env`:
```bash
cp .env.example .env
```
Mở file `.env` ra bằng nano hoặc vim và thay đổi các mật khẩu, key, cùng đường dẫn thư mục lưu trữ dữ liệu tĩnh:
```bash
nano .env
```

### Bước 2: Khởi chạy dịch vụ theo Tier mong muốn
Chọn một trong ba file compose để khởi chạy bằng cách chạy lệnh tương ứng:

* **Đối với Tier 1 (Cấu hình yếu):**
  ```bash
  docker compose -f docker-compose.tier1.yml up -d --build
  ```

* **Đối với Tier 2 (Cấu hình trung bình):**
  ```bash
  docker compose -f docker-compose.tier2.yml up -d --build
  ```

* **Đối với Tier 3 (Cấu hình Production):**
  ```bash
  docker compose -f docker-compose.tier3.yml up -d --build
  ```

### Bước 3: Khởi tạo cơ sở dữ liệu ban đầu
Sau khi các container khởi động thành công, tiến hành truy cập vào container Web để chạy các lệnh khởi tạo (chỉ cần chạy một lần duy nhất khi cài đặt):

1. **Khởi tạo dữ liệu Django (Nạp database mặc định):**
   ```bash
   docker exec -it fptoj-web-tier2 python manage.py loaddata navbar language_small demo
   ```
   *(Thay thế `fptoj-web-tier2` bằng tên container tương ứng của Tier bạn chạy).*

2. **Tạo tài khoản Admin (Superuser):**
   ```bash
   docker exec -it fptoj-web-tier2 python manage.py createsuperuser
   ```

---

## 🛠️ Câu lệnh Quản lý Hữu ích

* **Kiểm tra trạng thái các dịch vụ:**
  ```bash
  docker compose -f docker-compose.tier2.yml ps
  ```

* **Xem logs trực tiếp của Web / Celery:**
  ```bash
  docker compose -f docker-compose.tier2.yml logs -f web
  docker compose -f docker-compose.tier2.yml logs -f celery
  ```

* **Dừng toàn bộ hệ thống:**
  ```bash
  docker compose -f docker-compose.tier2.yml down
  ```
