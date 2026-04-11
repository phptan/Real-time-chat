from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.services.backup_service import BackupService


logger = logging.getLogger(__name__)


class BackupScheduler:
    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler(timezone=settings.backup_timezone)
        self._backup_service = BackupService()

    def start(self) -> None:
        self._scheduler.add_job(
            self._backup_service.run_backup,
            trigger=CronTrigger(hour=settings.backup_cron_hour, minute=settings.backup_cron_minute),
            id="daily_backup_job",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self._scheduler.start()
        logger.info(
            "Backup scheduler started at %02d:%02d (%s)",
            settings.backup_cron_hour,
            settings.backup_cron_minute,
            settings.backup_timezone,
        )

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Backup scheduler stopped")
