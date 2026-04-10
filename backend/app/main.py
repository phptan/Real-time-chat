from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints.notifications import router as notifications_router
from app.db import Base, engine
from app.middleware import JWTAuthMiddleware
from app.scheduler import BackupScheduler
from app.workers import RedisEventWorker
from app import models  # noqa: F401


app = FastAPI(
    title="Notification Service",
    version="0.1.0",
    description="Microservice for delivering real-time chat notifications.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(JWTAuthMiddleware)

app.include_router(notifications_router, prefix="/api", tags=["notifications"])


@app.on_event("startup")
async def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    worker = RedisEventWorker()
    await worker.start()
    app.state.redis_worker = worker
    backup_scheduler = BackupScheduler()
    backup_scheduler.start()
    app.state.backup_scheduler = backup_scheduler


@app.on_event("shutdown")
async def on_shutdown() -> None:
    worker = getattr(app.state, "redis_worker", None)
    if worker:
        await worker.stop()
    backup_scheduler = getattr(app.state, "backup_scheduler", None)
    if backup_scheduler:
        backup_scheduler.shutdown()


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "service": "notification-service"}
