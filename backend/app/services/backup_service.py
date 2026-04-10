from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings


logger = logging.getLogger(__name__)


class BackupService:
    def __init__(self) -> None:
        self._s3 = boto3.client(
            "s3",
            endpoint_url=settings.minio_endpoint_url,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            use_ssl=settings.minio_secure,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    async def run_backup(self) -> None:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M")
        backup_name = f"backup_{timestamp}.tar.gz"
        temp_dir = Path(tempfile.mkdtemp(prefix="backup_job_"))
        auth_dump_file = temp_dir / "auth_user_db.sql"
        chat_dump_file = temp_dir / "chat_db.archive"
        archive_file = temp_dir / backup_name

        try:
            await self._run_pg_dump(auth_dump_file)
            await self._run_mongo_dump(chat_dump_file)
            self._build_archive(archive_file, auth_dump_file, chat_dump_file)
            await asyncio.to_thread(self._upload_to_minio, archive_file, backup_name)
            await asyncio.to_thread(self._enforce_retention)
            logger.info("Backup job completed: %s", backup_name)
        except Exception:
            logger.exception("Backup job failed")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def _run_pg_dump(self, output_file: Path) -> None:
        cmd = ["pg_dump", "--dbname", settings.auth_pg_dump_url, "--file", str(output_file)]
        await self._run_command(cmd, "pg_dump")

    async def _run_mongo_dump(self, output_file: Path) -> None:
        cmd = [
            "mongodump",
            f"--uri={settings.chat_mongo_uri}",
            f"--db={settings.chat_mongo_db_name}",
            f"--archive={output_file}",
        ]
        await self._run_command(cmd, "mongodump")

    async def _run_command(self, command: list[str], command_name: str) -> None:
        def _execute() -> None:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise RuntimeError(f"{command_name} failed: {result.stderr.strip()}")

        await asyncio.to_thread(_execute)

    @staticmethod
    def _build_archive(archive_path: Path, auth_dump_file: Path, chat_dump_file: Path) -> None:
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(auth_dump_file, arcname=auth_dump_file.name)
            tar.add(chat_dump_file, arcname=chat_dump_file.name)

    def _upload_to_minio(self, archive_path: Path, object_name: str) -> None:
        self._ensure_bucket_exists(settings.backup_bucket)
        self._s3.upload_file(str(archive_path), settings.backup_bucket, object_name)

    def _ensure_bucket_exists(self, bucket_name: str) -> None:
        try:
            self._s3.head_bucket(Bucket=bucket_name)
        except ClientError:
            self._s3.create_bucket(Bucket=bucket_name)

    def _enforce_retention(self) -> None:
        response = self._s3.list_objects_v2(Bucket=settings.backup_bucket)
        objects = response.get("Contents", [])
        backups = [obj for obj in objects if obj.get("Key", "").startswith("backup_")]
        backups.sort(key=lambda item: item.get("LastModified"), reverse=True)

        for old_obj in backups[settings.backup_keep_last :]:
            self._s3.delete_object(Bucket=settings.backup_bucket, Key=old_obj["Key"])
