from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str = "notification-service"
    env: str = "dev"
    database_url: str = "postgresql+psycopg2://postgres:postgres@postgres:5432/notification_db"
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    redis_url: str = "redis://redis:6379/0"
    redis_channels: str = "new_message,message_deleted,user_registered,password_reset,friend_request,friend_accepted"
    fcm_credentials_path: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@example.com"
    smtp_use_tls: bool = True
    auth_pg_dump_url: str = "postgresql://postgres:postgres@postgres:5432/notification_db"
    chat_mongo_uri: str = "mongodb://mongo:27017/chat_db"
    chat_mongo_db_name: str = "chat_db"
    backup_bucket: str = "backups"
    backup_keep_last: int = 30
    backup_cron_hour: int = 2
    backup_cron_minute: int = 0
    backup_timezone: str = "UTC"
    minio_endpoint_url: str = "http://minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"

    @property
    def redis_channel_list(self) -> list[str]:
        return [ch.strip() for ch in self.redis_channels.split(",") if ch.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
