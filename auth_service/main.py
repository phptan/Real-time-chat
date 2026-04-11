"""
Auth Service — Main Application
Endpoints: /register, /login, /verify-token, /users/all
Đây là trung tâm xác thực cho toàn bộ hệ thống Microservices.
"""
import os
import redis
from fastapi import FastAPI, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from models import AuthUser
from schemas import (
    RegisterRequest, LoginRequest, VerifyTokenRequest,
    TokenResponse, UserInfo, StandardResponse
)
from database import get_db
from auth_utils import (
    hash_password, verify_password,
    create_access_token, decode_access_token
)

app = FastAPI(
    title="Auth Service",
    version="1.0.0",
    description="Microservice xác thực và phân quyền cho hệ thống Real-time Chat"
)

# CORS — cho phép React frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis client để quản lý online presence
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


# =============================================
# ENDPOINT: ĐĂNG KÝ TÀI KHOẢN
# =============================================
@app.post("/register", response_model=StandardResponse)
def register(req: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    """Đăng ký tài khoản mới. Tạo auth record + user profile."""

    # Kiểm tra username đã tồn tại chưa
    existing_user = db.query(AuthUser).filter(AuthUser.username == req.username).first()
    if existing_user:
        response.status_code = 409
        return StandardResponse(
            success=False,
            error="USERNAME_EXISTS",
            message="Tên đăng nhập đã được sử dụng."
        )

    # Kiểm tra email đã tồn tại chưa
    existing_email = db.query(AuthUser).filter(AuthUser.email == req.email).first()
    if existing_email:
        response.status_code = 409
        return StandardResponse(
            success=False,
            error="EMAIL_EXISTS",
            message="Email đã được sử dụng."
        )

    # Tạo user mới
    new_user = AuthUser(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Tạo JWT token luôn (auto login sau đăng ký)
    token = create_access_token(str(new_user.id), new_user.username)

    # Set online status
    redis_client.set(f"user:online:{new_user.id}", "true", ex=300)

    return StandardResponse(
        success=True,
        data={
            "access_token": token,
            "token_type": "bearer",
            "user_id": str(new_user.id),
            "username": new_user.username
        },
        message="Đăng ký thành công!"
    )


# =============================================
# ENDPOINT: ĐĂNG NHẬP
# =============================================
@app.post("/login", response_model=StandardResponse)
def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Đăng nhập bằng username + password, trả về JWT."""

    user = db.query(AuthUser).filter(AuthUser.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        response.status_code = 401
        return StandardResponse(
            success=False,
            error="INVALID_CREDENTIALS",
            message="Tên đăng nhập hoặc mật khẩu không đúng."
        )

    if not user.is_active:
        response.status_code = 403
        return StandardResponse(
            success=False,
            error="ACCOUNT_DISABLED",
            message="Tài khoản đã bị vô hiệu hóa."
        )

    # Tạo JWT
    token = create_access_token(str(user.id), user.username)

    # Set online status
    redis_client.set(f"user:online:{user.id}", "true", ex=300)

    return StandardResponse(
        success=True,
        data={
            "access_token": token,
            "token_type": "bearer",
            "user_id": str(user.id),
            "username": user.username
        },
        message="Đăng nhập thành công!"
    )


# =============================================
# ENDPOINT: XÁC THỰC TOKEN (Internal API)
# =============================================
@app.post("/verify-token", response_model=StandardResponse)
def verify_token(req: VerifyTokenRequest, response: Response):
    """Xác thực JWT token — các service khác gọi nội bộ."""
    try:
        payload = decode_access_token(req.token)
        return StandardResponse(
            success=True,
            data={
                "user_id": payload.get("user_id"),
                "username": payload.get("username")
            },
            message="Token hợp lệ."
        )
    except Exception:
        response.status_code = 401
        return StandardResponse(
            success=False,
            error="INVALID_TOKEN",
            message="Token không hợp lệ hoặc đã hết hạn."
        )


# =============================================
# ENDPOINT: DANH SÁCH TẤT CẢ USERS
# =============================================
@app.get("/users/all", response_model=StandardResponse)
def get_all_users(db: Session = Depends(get_db)):
    """Trả về danh sách tất cả users kèm trạng thái online."""
    users = db.query(AuthUser).filter(AuthUser.is_active == True).all()

    users_data = []
    for u in users:
        is_online = redis_client.exists(f"user:online:{u.id}") == 1
        users_data.append({
            "id": str(u.id),
            "username": u.username,
            "email": u.email,
            "is_online": is_online
        })

    return StandardResponse(
        success=True,
        data={"users": users_data, "total": len(users_data)},
        message="Tải danh sách người dùng thành công."
    )


# =============================================
# ENDPOINT: SET OFFLINE (khi logout)
# =============================================
@app.post("/logout", response_model=StandardResponse)
def logout(req: VerifyTokenRequest, response: Response):
    """Đăng xuất — xóa online status."""
    try:
        payload = decode_access_token(req.token)
        user_id = payload.get("user_id")
        redis_client.delete(f"user:online:{user_id}")
        return StandardResponse(success=True, data=None, message="Đăng xuất thành công.")
    except Exception:
        response.status_code = 401
        return StandardResponse(success=False, error="INVALID_TOKEN", message="Token không hợp lệ.")


# =============================================
# HEALTH CHECK
# =============================================
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "auth-service"}
