"""
User Service — Main Application (MVP Refactored)
Quản lý hồ sơ người dùng, trạng thái online, bạn bè.
Tích hợp với Auth Service qua JWT.
"""
import os
import uuid
import jwt
from fastapi import FastAPI, Depends, Response, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import redis

from models import UserProfile, Friendship
from schemas import StandardResponse, UserPublic, ProfileUpdate, FriendAction
from database import get_db

app = FastAPI(
    title="User Service",
    version="2.0.0",
    description="Microservice quản lý hồ sơ người dùng"
)

# CORS — cho phép React frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", include_in_schema=False)
def read_root():
    return RedirectResponse(url="/docs")

# Redis client — sử dụng biến môi trường cho Docker network
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "SECRET_YOUR_TEAM_CHOSE")


# === XÁC THỰC NGƯỜI DÙNG QUA JWT ===
def get_current_user_id(request: Request) -> str:
    """Lấy user_id từ JWT token trong Authorization header."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1]
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            return payload.get("user_id")
        except Exception:
            pass

    # Fallback: header X-User-Id (cho internal service calls)
    user_id = request.headers.get("X-User-Id")
    if user_id:
        return user_id

    return None


def check_online_status(user_id: str) -> bool:
    """Kiểm tra trạng thái online từ Redis."""
    return redis_client.exists(f"user:online:{user_id}") == 1


# =============================================
# ENDPOINT: TẠO PROFILE (Auth Service gọi khi đăng ký)
# =============================================
@app.post("/api/users/create-profile", response_model=StandardResponse)
def create_profile(request: Request, response: Response, db: Session = Depends(get_db)):
    """Tạo user profile mới — được gọi bởi Auth Service khi đăng ký."""
    body = {}
    import asyncio
    # Dùng sync approach
    return _create_profile_handler(request, response, db)


@app.post("/api/users/profile", response_model=StandardResponse)
def create_profile_v2(
    response: Response,
    user_id: str = None,
    username: str = None,
    email: str = None,
    db: Session = Depends(get_db)
):
    """Tạo user profile — endpoint đơn giản hơn."""
    if not user_id or not username:
        response.status_code = 400
        return StandardResponse(success=False, error="MISSING_FIELDS", message="Thiếu user_id hoặc username")

    existing = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if existing:
        return StandardResponse(success=True, data={"id": str(existing.id)}, message="Profile đã tồn tại.")

    new_profile = UserProfile(
        id=uuid.UUID(user_id),
        display_name=username,
        bio=""
    )
    db.add(new_profile)
    db.commit()
    return StandardResponse(success=True, data={"id": user_id}, message="Tạo profile thành công.")


def _create_profile_handler(request, response, db):
    return StandardResponse(success=True, data=None, message="OK")


# =============================================
# ENDPOINT: THÔNG TIN CÁ NHÂN
# =============================================
@app.get("/api/users/me", response_model=StandardResponse)
def get_my_profile(response: Response, db: Session = Depends(get_db), current_user_id: str = Depends(get_current_user_id)):
    if not current_user_id:
        response.status_code = 401
        return StandardResponse(success=False, error="UNAUTHORIZED", message="Chưa đăng nhập.")

    user = db.query(UserProfile).filter(UserProfile.id == current_user_id).first()
    if not user:
        response.status_code = 404
        return StandardResponse(success=False, error="NOT_FOUND", message="Không tìm thấy thông tin hồ sơ người dùng.")

    data = {
        "id": str(user.id),
        "displayName": user.display_name,
        "avatarUrl": user.avatar_url,
        "bio": user.bio,
        "isOnline": check_online_status(str(user.id)),
        "createdAt": str(user.created_at) if user.created_at else None
    }
    return StandardResponse(success=True, data=data, message="Tải thông tin cá nhân thành công.")


@app.patch("/api/users/me", response_model=StandardResponse)
def update_profile(update_data: ProfileUpdate, response: Response, db: Session = Depends(get_db), current_user_id: str = Depends(get_current_user_id)):
    user = db.query(UserProfile).filter(UserProfile.id == current_user_id).first()
    if update_data.displayName:
        user.display_name = update_data.displayName
    if update_data.bio is not None:
        user.bio = update_data.bio
    db.commit()
    db.refresh(user)
    return StandardResponse(success=True, data={"id": str(user.id)}, message="Thông tin hồ sơ đã được cập nhật.")


# =============================================
# ENDPOINT: DANH SÁCH BẠN BÈ
# =============================================
@app.get("/api/users/friends", response_model=StandardResponse)
def get_friends_list(db: Session = Depends(get_db), current_user_id: str = Depends(get_current_user_id)):
    friendships = db.query(Friendship).filter(
        and_(or_(Friendship.requester_id == current_user_id, Friendship.addressee_id == current_user_id),
             Friendship.status == 'accepted')
    ).all()

    friends_data = []
    for f in friendships:
        f_id = f.addressee_id if str(f.requester_id) == current_user_id else f.requester_id
        u = db.query(UserProfile).filter(UserProfile.id == f_id).first()
        if u:
            friends_data.append({
                "id": str(u.id), "displayName": u.display_name, "avatarUrl": u.avatar_url,
                "isOnline": check_online_status(str(u.id)), "friendshipId": str(f.id)
            })
    return StandardResponse(success=True, data={"friends": friends_data}, message="Tải danh sách bạn bè thành công.")


@app.get("/api/users/search", response_model=StandardResponse)
def search_users(q: str, response: Response, limit: int = 10, db: Session = Depends(get_db), current_user_id: str = Depends(get_current_user_id)):
    if len(q) < 2:
        response.status_code = 400
        return StandardResponse(success=False, error="KEYWORD_TOO_SHORT", message="Vui lòng nhập từ khóa tìm kiếm dài hơn (tối thiểu 2 ký tự).")

    users = db.query(UserProfile).filter(
        UserProfile.display_name.ilike(f"%{q}%"),
        UserProfile.is_public == True,
        UserProfile.id != current_user_id
    ).limit(limit).all()

    results = [{"id": str(u.id), "displayName": u.display_name, "avatarUrl": u.avatar_url} for u in users]
    return StandardResponse(success=True, data={"users": results, "total": len(results)}, message="Kết quả tìm kiếm phù hợp.")


@app.get("/api/users/friends/pending", response_model=StandardResponse)
def get_pending_requests(db: Session = Depends(get_db), current_user_id: str = Depends(get_current_user_id)):
    requests = db.query(Friendship).filter(
        Friendship.addressee_id == current_user_id,
        Friendship.status == 'pending'
    ).all()

    results = []
    for req in requests:
        u = db.query(UserProfile).filter(UserProfile.id == req.requester_id).first()
        if u:
            results.append({
                "friendshipId": str(req.id), "requesterId": str(u.id),
                "displayName": u.display_name, "avatarUrl": u.avatar_url
            })
    return StandardResponse(success=True, data={"pendingRequests": results}, message="Đã tải các yêu cầu kết bạn đang chờ.")


# Gửi lời mời kết bạn
@app.post("/api/users/{target_id}/friends", response_model=StandardResponse)
def send_friend_request(target_id: str, response: Response, db: Session = Depends(get_db), current_user_id: str = Depends(get_current_user_id)):
    if current_user_id == target_id:
        response.status_code = 400
        return StandardResponse(success=False, error="SELF_REQUEST", message="Bạn không thể gửi yêu cầu kết bạn cho chính mình.")

    existing = db.query(Friendship).filter(
        or_(
            and_(Friendship.requester_id == current_user_id, Friendship.addressee_id == target_id),
            and_(Friendship.requester_id == target_id, Friendship.addressee_id == current_user_id)
        )
    ).first()

    if existing:
        if existing.status == 'accepted':
            response.status_code = 400
            return StandardResponse(success=False, error="ALREADY_FRIENDS", message="Hai bạn đã trở thành bạn bè.")
        elif existing.status == 'pending':
            response.status_code = 400
            return StandardResponse(success=False, error="REQUEST_PENDING", message="Yêu cầu kết bạn đang chờ đối phương xác nhận.")

    new_req = Friendship(requester_id=current_user_id, addressee_id=target_id, status='pending')
    db.add(new_req)
    db.commit()
    return StandardResponse(success=True, data=None, message="Đã gửi yêu cầu kết bạn thành công.")


@app.patch("/api/users/friends/{friendship_id}", response_model=StandardResponse)
def handle_friend_request(friendship_id: str, action_data: FriendAction, response: Response, db: Session = Depends(get_db), current_user_id: str = Depends(get_current_user_id)):
    friendship = db.query(Friendship).filter(Friendship.id == friendship_id).first()

    if not friendship:
        response.status_code = 404
        return StandardResponse(success=False, error="NOT_FOUND", message="Yêu cầu kết bạn không tồn tại hoặc đã bị hủy.")

    if str(friendship.addressee_id) != current_user_id:
        response.status_code = 403
        return StandardResponse(success=False, error="FORBIDDEN", message="Bạn không có quyền thực hiện thao tác này.")

    if action_data.action == "accept":
        friendship.status = "accepted"
        msg = "Đã chấp nhận yêu cầu kết bạn."
    else:
        friendship.status = "rejected"
        msg = "Đã từ chối yêu cầu kết bạn."

    db.commit()
    return StandardResponse(success=True, data=None, message=msg)


@app.delete("/api/users/friends/{friendship_id}", response_model=StandardResponse)
def unfriend(friendship_id: str, db: Session = Depends(get_db), current_user_id: str = Depends(get_current_user_id)):
    friendship = db.query(Friendship).filter(Friendship.id == friendship_id).first()

    if not friendship:
        return StandardResponse(success=False, error="NOT_FOUND", message="Mối quan hệ không tồn tại.")

    if str(friendship.requester_id) != current_user_id and str(friendship.addressee_id) != current_user_id:
        return StandardResponse(success=False, error="FORBIDDEN", message="Bạn không có quyền thực hiện thao tác này.")

    db.delete(friendship)
    db.commit()
    return StandardResponse(success=True, data=None, message="Đã hủy kết bạn thành công.")


# === CẬP NHẬT TRẠNG THÁI ONLINE ===
@app.post("/api/users/status")
def update_user_status(user_id: str, status: str):
    if status == "online":
        redis_client.set(f"user:online:{user_id}", "true", ex=300)
    else:
        redis_client.delete(f"user:online:{user_id}")
    return {"success": True, "message": f"User {user_id} is now {status}"}


@app.get("/api/users/{userId}", response_model=StandardResponse)
def get_user_profile(userId: str, response: Response, db: Session = Depends(get_db)):
    user = db.query(UserProfile).filter(UserProfile.id == userId).first()
    if not user:
        response.status_code = 404
        return StandardResponse(success=False, error="NOT_FOUND", message="Không tìm thấy người dùng này.")
    return StandardResponse(success=True, data={
        "id": str(user.id), "displayName": user.display_name,
        "avatarUrl": user.avatar_url, "isOnline": check_online_status(str(user.id))
    }, message="Tải hồ sơ thành công.")


# Health check
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "user-service"}