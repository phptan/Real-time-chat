from uuid import UUID

from fastapi import Request
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings


class JWTAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.protected_prefixes = ("/api/notifications",)
        self.public_paths = {"/health", "/docs", "/redoc", "/openapi.json"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in self.public_paths or not path.startswith(self.protected_prefixes):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing bearer token"})

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            user_id = payload.get("user_id") or payload.get("sub")
            if not user_id:
                return JSONResponse(status_code=401, content={"detail": "Invalid token payload"})
            UUID(str(user_id))
            request.state.user_id = str(user_id)
        except (JWTError, ValueError):
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        return await call_next(request)
