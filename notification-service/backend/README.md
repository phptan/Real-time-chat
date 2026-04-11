# Backend Documentation - Notification Service

Tai lieu nay mo ta toan bo backend cua Notification Service: kien truc, cau hinh, API, worker bat dong bo, backup scheduler, va cach van hanh.

## 1. Tong quan

Backend duoc xay dung voi FastAPI, SQLAlchemy, PostgreSQL va Redis Pub/Sub.

Chuc nang chinh:
- Xac thuc JWT o middleware.
- Quan ly FCM device token theo user.
- Lay lich su thong bao co phan trang.
- Nhan su kien Redis va gui thong bao qua FCM / Email.
- Tu dong backup PostgreSQL + MongoDB len MinIO theo lich.

## 2. Kien truc va module

Cau truc backend:

```text
backend/
├─ app/
│  ├─ main.py
│  ├─ api/
│  │  ├─ deps.py
│  │  └─ v1/endpoints/notifications.py
│  ├─ core/config.py
│  ├─ db/
│  │  ├─ base.py
│  │  └─ session.py
│  ├─ middleware/jwt_auth.py
│  ├─ models/
│  │  ├─ device_token.py
│  │  └─ notification_log.py
│  ├─ schemas/notification.py
│  ├─ services/
│  │  ├─ email_service.py
│  │  ├─ fcm_service.py
│  │  ├─ notification_log_service.py
│  │  └─ backup_service.py
│  ├─ workers/redis_event_worker.py
│  └─ scheduler/backup_scheduler.py
├─ tests/
├─ requirements.txt
└─ .env.example
```

Luot startup trong app:
1. Tao bang DB qua Base.metadata.create_all.
2. Start RedisEventWorker de subscribe cac channel.
3. Start BackupScheduler de chay backup theo cron.

## 3. Cong nghe va dependency

- FastAPI + Uvicorn
- SQLAlchemy 2.x
- PostgreSQL (psycopg2)
- Redis client (redis asyncio)
- Firebase Admin SDK (FCM)
- aiosmtplib (SMTP)
- APScheduler
- boto3 (S3/MinIO)

## 4. Cac endpoint HTTP

Base URL mac dinh: `http://localhost:8000`

### 4.1 Public endpoint

#### GET /health
- Auth: khong can JWT.
- Muc dich: health check service.
- Response:

```json
{
  "status": "ok",
  "service": "notification-service"
}
```

### 4.2 Protected endpoint (bat buoc JWT)

Tat ca endpoint duoi prefix `/api/notifications` deu bat buoc header:

`Authorization: Bearer <jwt_token>`

JWT payload phai co `user_id` hoac `sub` va gia tri phai la UUID hop le.

#### POST /api/notifications/device-token
- Muc dich: tao moi hoac cap nhat FCM token cho user hien tai.
- Body:

```json
{
  "fcm_token": "fcm_token_string_very_long_123456",
  "platform": "android"
}
```

- Validation:
  - `fcm_token`: min 20, max 512.
  - `platform`: `ios | android | web`.

#### DELETE /api/notifications/device-token
- Muc dich: deactivate token khi logout (`is_active=false`).
- Body:

```json
{
  "fcm_token": "fcm_token_string_very_long_123456"
}
```

- Response:

```json
{
  "status": "ok"
}
```

#### GET /api/notifications?limit=&offset=
- Muc dich: lay lich su notification cua user trong JWT.
- Query:
  - `limit`: 1..100, default 20
  - `offset`: >=0, default 0

- Response:

```json
{
  "items": [
    {
      "id": "...",
      "user_id": "...",
      "type": "new_message",
      "channel": "fcm",
      "status": "sent",
      "error_msg": null
    }
  ],
  "limit": 20,
  "offset": 0
}
```

## 5. Redis event worker

Worker subscribe cac channel tu bien `REDIS_CHANNELS`.

Mac dinh:
- `new_message`
- `message_deleted`
- `user_registered`
- `password_reset`
- `friend_request`
- `friend_accepted`

Mapping xu ly:
- `new_message`: gui push cho danh sach recipient (bo qua sender).
- `message_deleted`: cap nhat status log thanh `deleted` theo `notification_log_id`.
- `user_registered`: gui email verify.
- `password_reset`: gui email reset token/link.
- `friend_request` / `friend_accepted`: gui push cho target user.

Co che fail-safe:
- Loi FCM/SMTP duoc catch, ghi `notification_logs` voi `status=failed`.
- Worker khong crash toan bo khi 1 event loi.

## 6. Backup scheduler

Backup scheduler chay AsyncIOScheduler voi CronTrigger.

Mac dinh:
- Gio: 02:00
- Timezone: UTC
- Retention: giu `BACKUP_KEEP_LAST` ban backup gan nhat

Quy trinh 1 job backup:
1. Chay `pg_dump` cho Auth/User DB (`AUTH_PG_DUMP_URL`).
2. Chay `mongodump` cho Chat DB (`CHAT_MONGO_URI`, `CHAT_MONGO_DB_NAME`).
3. Nen 2 file dump thanh `backup_YYYY-MM-DD_HH-MM.tar.gz`.
4. Upload len MinIO bucket (`BACKUP_BUCKET`).
5. Xoa backup cu theo retention policy.

## 7. Bien moi truong

Tham khao file `.env.example`.

### 7.1 Core
- `APP_NAME`
- `ENV`
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`

### 7.2 Redis / Worker
- `REDIS_URL`
- `REDIS_CHANNELS`

### 7.3 FCM
- `FCM_CREDENTIALS_PATH`

### 7.4 SMTP
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `SMTP_USE_TLS`

### 7.5 Backup
- `AUTH_PG_DUMP_URL`
- `CHAT_MONGO_URI`
- `CHAT_MONGO_DB_NAME`
- `BACKUP_BUCKET`
- `BACKUP_KEEP_LAST`
- `BACKUP_CRON_HOUR`
- `BACKUP_CRON_MINUTE`
- `BACKUP_TIMEZONE`
- `MINIO_ENDPOINT_URL`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `MINIO_SECURE`

## 8. Chay bang Docker

Tu root project:

```bash
docker-compose up -d --build
```

Service chinh:
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- MailHog UI: `http://localhost:8025`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`

## 9. Chay local khong Docker (optional)

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Luu y:
- Ban can tu cung cap PostgreSQL, Redis, SMTP, MongoDB, MinIO ben ngoai.

## 10. Test

### 10.1 Pytest

```bash
cd backend
pytest -q
```

### 10.2 Postman

Da co bo Postman tai:
- `backend/tests/postman/notification-service.postman_collection.json`
- `backend/tests/postman/notification-service.postman_environment.json`
- `backend/tests/postman/API_ANALYSIS.md`

## 11. Bao mat va van hanh

Khuyen nghi production:
- Khong dung `JWT_SECRET_KEY=change-me`.
- Han che CORS origin theo domain thuc te.
- Bao mat secrets (JWT, SMTP, MinIO key) bang secret manager.
- Bat logging va monitoring cho:
  - worker errors
  - backup failures
  - SMTP/FCM failures

## 12. Troubleshooting nhanh

### 401 Unauthorized
- Kiem tra header `Authorization: Bearer <token>`.
- Kiem tra JWT secret/algorithm trung khop backend.
- Kiem tra payload co `user_id` hoac `sub` dang UUID.

### 422 Validation Error
- Kiem tra body request theo schema (`fcm_token` do dai, `platform` hop le).
- Kiem tra `limit`, `offset` trong range cho phep.

### Khong gui duoc FCM
- Kiem tra `FCM_CREDENTIALS_PATH`.
- Kiem tra file service account co ton tai trong container (`/app/secrets/...`).

### Khong gui duoc email
- Kiem tra `SMTP_HOST`, `SMTP_PORT`, TLS setting.
- Neu dung local docker stack, xem MailHog tai `http://localhost:8025`.

### Backup khong tao file tren MinIO
- Kiem tra tool `pg_dump` va `mongodump` co trong image.
- Kiem tra ket noi MinIO + bucket + credential.
- Kiem tra log cua service `notification-service`.
