from app.schemas.notification import NotificationCreate, NotificationOut


class NotificationService:
    def create(self, payload: NotificationCreate) -> NotificationOut:
        raise NotImplementedError("Implement persistence and queue publish logic")

    def list_by_user(self, user_id: str) -> list[NotificationOut]:
        raise NotImplementedError("Implement query logic")
