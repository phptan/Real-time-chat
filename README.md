# 💬 Real-time Chat — Microservices MVP

Hệ thống nhắn tin thời gian thực được xây dựng trên kiến trúc **Microservices**, sử dụng **Docker Compose** để triển khai toàn bộ hệ thống chỉ với một câu lệnh duy nhất.

---

## 📐 Kiến Trúc Hệ Thống

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                 │
│                  React + Vite (:5173)                           │
│          Socket.io-client │ Axios (REST API)                    │
└────────────┬──────────────┼──────────────┬──────────────────────┘
             │              │              │
     ┌───────▼───────┐ ┌───▼────────┐ ┌───▼──────────────┐
     │ Auth Service  │ │ User       │ │ Chat Service     │
     │ FastAPI :8001 │ │ Service    │ │ Node.js + Socket │
     │               │ │ FastAPI    │ │ .io :3002        │
     │ • Register    │ │ :8002      │ │                  │
     │ • Login       │ │            │ │ • Rooms          │
     │ • JWT Token   │ │ • Profile  │ │ • Messages       │
     │ • Users List  │ │ • Friends  │ │ • WebSocket      │
     └───────┬───────┘ │ • Search   │ │ • Typing         │
             │         └─────┬──────┘ └───┬──────────────┘
             │               │            │        │
     ┌───────▼───────────────▼────────────▼──┐     │
     │            Redis (:6379)              │     │
     │  • Pub/Sub (tin nhắn → notification)  │     │
     │  • Presence (Online/Offline)          │     │
     └───────────────┬───────────────────────┘     │
                     │                             │
          ┌──────────▼──────────┐                  │
          │ Notification Service│                  │
          │ FastAPI :8003       │                  │
          │ • Redis Subscriber  │                  │
          │ • FCM / Email       │                  │
          └──────────┬──────────┘                  │
                     │                             │
     ┌───────────────▼───────┐    ┌────────────────▼───┐
     │  PostgreSQL (:5432)   │    │  MongoDB (:27017)  │
     │  • auth_db            │    │  • chatdb          │
     │  • user_service_db    │    │    - messages       │
     │  • notification_db    │    │    - rooms          │
     └───────────────────────┘    └────────────────────┘
```

---

## 🛠️ Công Nghệ Sử Dụng

| Thành phần | Công nghệ | Phiên bản |
|------------|-----------|-----------|
| **Auth Service** | Python, FastAPI, SQLAlchemy, PyJWT, bcrypt | Python 3.11 |
| **User Service** | Python, FastAPI, SQLAlchemy, PyJWT | Python 3.11 |
| **Chat Service** | Node.js, Express, Socket.io, Mongoose | Node 20 |
| **Notification Service** | Python, FastAPI, Redis Pub/Sub, FCM | Python 3.11 |
| **Frontend** | React 18, Vite, Socket.io-client, Axios | Node 20 |
| **Database (SQL)** | PostgreSQL | 16 |
| **Database (NoSQL)** | MongoDB | 7 |
| **Message Broker / Cache** | Redis | 7 |
| **Containerization** | Docker, Docker Compose | 3.8 |

---

## 📁 Cấu Trúc Thư Mục

```
Real-time-chat/
├── auth_service/              # 🔐 Dịch vụ xác thực (FastAPI)
│   ├── main.py                #    API: register, login, verify-token, users/all
│   ├── models.py              #    SQLAlchemy model: AuthUser
│   ├── schemas.py             #    Pydantic schemas
│   ├── database.py            #    PostgreSQL connection (auth_db)
│   ├── auth_utils.py          #    Bcrypt hashing + JWT utilities
│   ├── requirements.txt
│   └── Dockerfile
│
├── user_service/              # 👤 Dịch vụ quản lý người dùng (FastAPI)
│   ├── main.py                #    API: profile, friends, search, online status
│   ├── models.py              #    SQLAlchemy: UserProfile, Friendship
│   ├── schemas.py             #    Pydantic schemas
│   ├── database.py            #    PostgreSQL connection (user_service_db)
│   ├── requirements.txt
│   └── Dockerfile
│
├── chat-service/              # 💬 Dịch vụ chat (Node.js + Socket.io)
│   ├── index.js               #    REST API + WebSocket server
│   ├── package.json
│   ├── .env
│   └── Dockerfile
│
├── notification-service/      # 🔔 Dịch vụ thông báo (FastAPI)
│   └── backend/
│       ├── app/
│       │   ├── main.py        #    Redis Pub/Sub subscriber
│       │   ├── core/          #    Config, settings
│       │   ├── models/        #    NotificationLog, DeviceToken
│       │   ├── workers/       #    RedisEventWorker
│       │   ├── services/      #    FCM, Email, Backup
│       │   └── middleware/    #    JWT authentication
│       ├── requirements.txt
│       └── Dockerfile
│
├── frontend/                  # 🎨 Giao diện người dùng (React + Vite)
│   ├── src/
│   │   ├── App.jsx            #    Root: auth state, routing, toast
│   │   ├── main.jsx           #    Entry point
│   │   ├── index.css          #    Design system (dark glassmorphism)
│   │   ├── config/
│   │   │   └── api.js         #    API endpoints configuration
│   │   └── pages/
│   │       ├── LoginPage.jsx  #    Đăng nhập / Đăng ký
│   │       ├── LoginPage.css
│   │       ├── ChatPage.jsx   #    Chat realtime + online presence
│   │       └── ChatPage.css
│   ├── index.html
│   ├── vite.config.js         #    Proxy to microservices
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml         # 🐳 Orchestration — 8 containers
├── init-db.sql                # 🗃️ PostgreSQL multi-database init
└── README.md                  # 📖 Tài liệu này
```

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy

### Yêu Cầu

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (bao gồm Docker Compose)
- **RAM tối thiểu**: 4 GB (khuyến nghị 8 GB)

### Khởi Động

```bash
# 1. Clone repository
git clone <repository-url>
cd Real-time-chat

# 2. Khởi động toàn bộ hệ thống (lần đầu sẽ build ~3-5 phút)
docker-compose up --build

# 3. Mở trình duyệt
#    → http://localhost:5173
```

### Dừng Hệ Thống

```bash
# Dừng tất cả containers
docker-compose down

# Dừng và xóa dữ liệu (reset hoàn toàn)
docker-compose down -v
```

---

## 🌐 Cổng Dịch Vụ (Port Mapping)

| Service | URL | Mô tả |
|---------|-----|-------|
| **Frontend** | [http://localhost:5173](http://localhost:5173) | Giao diện chính |
| **Auth Service** | [http://localhost:8001/docs](http://localhost:8001/docs) | Swagger API — Xác thực |
| **User Service** | [http://localhost:8002/docs](http://localhost:8002/docs) | Swagger API — Người dùng |
| **Chat Service** | [http://localhost:3002/health](http://localhost:3002/health) | Health check |
| **Notification** | [http://localhost:8003/docs](http://localhost:8003/docs) | Swagger API — Thông báo |
| **PostgreSQL** | `localhost:5432` | 3 databases |
| **MongoDB** | `localhost:27017` | Chat data |
| **Redis** | `localhost:6379` | Pub/Sub + Presence |

---

## 🔄 Luồng Hoạt Động (MVP Flow)

### 1. 🔐 Identity — Đăng ký / Đăng nhập

```
Người dùng → [POST /register] → Auth Service → PostgreSQL (auth_db)
                                             → Redis (set online:true)
                                             → JWT Token ← trả về Frontend
```

### 2. 🟢 Presence — Trạng thái Online/Offline

```
Auth Service  ──[login]──→ Redis SET user:online:{id} "true" EX 300
Chat Service  ──[socket connect]──→ Redis (refresh TTL)
Chat Service  ──[socket disconnect]──→ Redis DEL user:online:{id}
Frontend      ──[GET /users/all]──→ Auth Service check Redis → 🟢/⚫
```

### 3. 💬 Real-time Chat — Nhắn tin 1-1

```
User A gửi tin nhắn
  → Socket.io emit("send_message")
  → Chat Service lưu MongoDB
  → Socket.io broadcast → Room
  → Redis publish("new_message")
  → User B nhận tin nhắn ngay lập tức (Socket.io)
  → Notification Service nhận từ Redis Pub/Sub
```

### 4. 📜 Persistence — Lịch sử tin nhắn

```
User mở phòng chat
  → [GET /api/chat/rooms/:roomId/messages]
  → Chat Service query MongoDB
  → Trả về 50 tin nhắn gần nhất (cursor pagination)
```

---

## 📡 API Reference

### Auth Service (:8001)

| Method | Endpoint | Mô tả | Body |
|--------|----------|-------|------|
| `POST` | `/register` | Đăng ký tài khoản | `{username, email, password}` |
| `POST` | `/login` | Đăng nhập | `{username, password}` |
| `POST` | `/verify-token` | Xác thực JWT | `{token}` |
| `POST` | `/logout` | Đăng xuất | `{token}` |
| `GET`  | `/users/all` | Danh sách users + online | — |
| `GET`  | `/health` | Health check | — |

### Chat Service (:3002)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/api/chat/rooms` | Tạo/lấy phòng chat |
| `GET`  | `/api/chat/rooms/user/:userId` | Danh sách phòng của user |
| `GET`  | `/api/chat/rooms/:roomId/messages` | Lịch sử tin nhắn |
| `POST` | `/api/chat/messages` | Gửi tin nhắn (REST) |

**Socket.io Events:**

| Event | Direction | Payload |
|-------|-----------|---------|
| `join_room` | Client → Server | `roomId` |
| `send_message` | Client → Server | `{senderId, senderName, roomId, text}` |
| `new_message` | Server → Client | Message object |
| `typing` | Client → Server | `{roomId, userId, username}` |
| `stop_typing` | Client → Server | `{roomId, userId}` |
| `user_typing` | Server → Client | `{userId, username}` |
| `delete_message` | Client → Server | `{messageId, userId}` |

### User Service (:8002)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/api/users/me` | Profile cá nhân |
| `PATCH` | `/api/users/me` | Cập nhật profile |
| `GET` | `/api/users/{id}` | Profile theo ID |
| `GET` | `/api/users/friends` | Danh sách bạn bè |
| `GET` | `/api/users/search?q=...` | Tìm kiếm user |
| `POST` | `/api/users/{id}/friends` | Gửi lời mời kết bạn |

---

## 🔑 Cấu Hình Bảo Mật

| Biến | Giá trị mặc định | Mô tả |
|------|-------------------|-------|
| `JWT_SECRET_KEY` | `SECRET_YOUR_TEAM_CHOSE` | Khóa ký JWT (chia sẻ giữa các service) |
| `POSTGRES_USER` | `admin` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `password` | PostgreSQL password |

> ⚠️ **Lưu ý**: Các giá trị mặc định chỉ dùng cho môi trường **development**. Trong production, hãy thay đổi tất cả credentials và sử dụng biến môi trường hoặc secrets manager.

---

## 🧪 Kiểm Thử

### Kiểm thử thủ công

1. Mở **http://localhost:5173**
2. **Đăng ký** 2 tài khoản (User A và User B) trên 2 tab khác nhau
3. Đăng nhập cả hai → thấy đèn 🟢 online
4. User A chọn User B → gửi tin nhắn
5. Tab User B nhận tin nhắn **ngay lập tức** (không cần refresh)
6. Refresh trang → lịch sử tin nhắn vẫn hiển thị

### Kiểm thử API trực tiếp

```bash
# Đăng ký
curl -X POST http://localhost:8001/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "123456"}'

# Đăng nhập
curl -X POST http://localhost:8001/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "123456"}'

# Health checks
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:3002/health
curl http://localhost:8003/health
```

---

## 👥 Thành Viên Nhóm

| Thành viên | Service phụ trách |
|------------|-------------------|
| Phạm Thị Anh Thư | User Service |
| Nguyễn Minh Trí | Chat Service |
| Nguyễn Trọng Tấn | Notification Service |
| Nguyễn Ngọc Quốc Long | Auth Service + Integration |

---

## 📋 Ghi Chú Kỹ Thuật

- **Redis Presence TTL**: Online status tự động hết hạn sau **5 phút** (300 giây). Chat Service refresh TTL khi WebSocket còn kết nối.
- **Message Pagination**: API trả tối đa **50 tin nhắn** mỗi request, hỗ trợ cursor-based pagination qua parameter `before`.
- **JWT Expiry**: Token có hạn **24 giờ**.
- **Soft Delete**: Tin nhắn bị xóa chỉ cập nhật `deletedAt`, không xóa khỏi database.
- **Inter-service Communication**: Các service giao tiếp qua **Redis Pub/Sub** (async) và **REST API** (sync).
