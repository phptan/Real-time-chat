# 💬 User Service - Real-time Chat Application

Đây là phân hệ **User Service** thuộc hệ thống ứng dụng Chat thời gian thực, được phát triển theo kiến trúc **Microservices**. Phân hệ này chịu trách nhiệm quản lý danh tính người dùng, mối quan hệ bạn bè, trạng thái hoạt động và lưu trữ dữ liệu cá nhân.

---

## 🚀 Tính năng chính (Core Features)

* **Quản lý hồ sơ (Profile):** Cập nhật thông tin cá nhân và tiểu sử (bio).
* **Lưu trữ ảnh đại diện (Avatar):** Upload, lưu trữ ảnh trực tiếp lên **MinIO**. Hỗ trợ xem ảnh phóng to (Lightbox) và **xóa ảnh đại diện** về mặc định (có bảng xác nhận xác nhận an toàn bằng SweetAlert2).
* **Hệ thống bạn bè (Friendships):** Xử lý luồng tìm kiếm, gửi lời mời kết bạn, chấp nhận/từ chối và hủy kết bạn.
* **Trạng thái hoạt động (Online Status):** Tích hợp **Redis** để theo dõi trạng thái Online/Offline theo thời gian thực (TTL 5 phút).
* **Chế độ Demo:** Chuyển đổi nhanh các User qua Header `X-Mock-User` để test luồng kết bạn ngay trên UI.

---

## 🛠️ Công nghệ sử dụng (Tech Stack)

| Thành phần | Công nghệ | Chi tiết |
| :--- | :--- | :--- |
| **Backend** | Python (FastAPI) | Xử lý logic, API Routing, Pydantic Validation |
| **Database** | PostgreSQL 16 | Lưu trữ dữ liệu quan hệ (SQLAlchemy ORM) |
| **Caching** | Redis 7 | Quản lý trạng thái Online/Offline |
| **Storage** | MinIO | S3 Compatible Storage lưu trữ Avatar |
| **Frontend** | ReactJS + Axios | UI Glassmorphism, SweetAlert2, cấu hình Proxy |
| **Infrastructure**| Docker Compose | Đóng gói và quản lý toàn bộ Backend & Dịch vụ |

---

## 📦 Hướng dẫn cài đặt và chạy (Setup & Installation)

Đảm bảo máy bạn đã cài đặt và bật sẵn phần mềm **Docker Desktop** trước khi thực hiện.

### 1. Khởi động toàn bộ Backend & Hạ tầng (Docker)
Không cần cài đặt Python thủ công. Mở terminal tại thư mục gốc `user_service` và chạy lệnh sau để Docker tự động build và chạy tất cả dịch vụ (FastAPI: 3003, Postgres: 5432, Redis: 6379, MinIO: 9000):

    docker compose up --build -d

### 2. Nạp dữ liệu giả lập (Seed Data)
Ở lần chạy đầu tiên, cần nạp dữ liệu nhóm (Thư, Trí, Tấn, Long) để test UI:
1. Truy cập Swagger UI: `http://localhost:3003/docs`
2. Tìm đến Endpoint `POST /seed_test_data`
3. Chọn **Try it out** -> **Execute**.

### 3. Cài đặt và chạy Frontend (ReactJS)
Mở một terminal mới, di chuyển vào thư mục Frontend:

    cd user-service-frontend
    npm install sweetalert2
    npm install
    npm start

Truy cập giao diện tại: `http://localhost:3000`

---

## 🔗 Danh sách API Endpoints chính

**1. Hồ sơ cá nhân (Profile)**
* `GET /api/users/me` - Lấy thông tin tài khoản đang đăng nhập.
* `PATCH /api/users/me` - Cập nhật thông tin (Tên hiển thị, tiểu sử).
* `POST /api/users/me/avatar` - Upload ảnh đại diện lên MinIO.
* `DELETE /api/users/me/avatar` - Xóa ảnh đại diện hiện tại.
* `GET /api/users/{userId}` - Lấy profile công khai của một user khác.

**2. Quản lý Bạn bè & Tìm kiếm**
* `GET /api/users/search?q={keyword}` - Tìm kiếm người dùng (yêu cầu ≥ 2 ký tự).
* `GET /api/users/friends` - Lấy danh sách bạn bè kèm trạng thái Online/Offline.
* `GET /api/users/friends/pending` - Lấy danh sách lời mời kết bạn đang chờ.
* `POST /api/users/{target_id}/friends` - Gửi lời mời kết bạn.
* `PATCH /api/users/friends/{friendship_id}` - Chấp nhận hoặc từ chối lời mời.
* `DELETE /api/users/friends/{friendship_id}` - Hủy kết bạn.

**3. Trạng thái (Internal/Chat Service gọi)**
* `POST /api/users/status` - Cập nhật trạng thái `online`/`offline` vào Redis.

---

## 📖 Tài liệu API (API Documentation)

Sau khi chạy Backend (Bước 1), truy cập tài liệu API tự động tại:
* **Swagger UI:** `http://localhost:3003/docs`
* **ReDoc:** `http://localhost:3003/redoc`

---
