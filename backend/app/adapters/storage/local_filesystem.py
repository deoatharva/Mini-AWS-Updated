import hashlib
import os
import re
import secrets
import shutil
from pathlib import Path
from typing import BinaryIO, Protocol


class StorageAdapterError(RuntimeError):
    """Raised when a local storage file operation fails."""


class UploadTooLargeError(StorageAdapterError):
    """Raised when an uploaded object exceeds the configured limit."""


class UploadSource(Protocol):
    file: BinaryIO


_STORAGE_NAME_PATTERN = re.compile(r"^[a-f0-9]{32}$")


class LocalFilesystemStorage:
    """Filesystem storage whose paths are derived only from trusted IDs."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _ensure_within_root(self, path: Path) -> Path:
        resolved = path.resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise StorageAdapterError("The storage path escaped the data directory.") from exc
        return resolved

    def bucket_directory(self, user_id: int, bucket_id: int) -> Path:
        candidate = self.root / str(int(user_id)) / str(int(bucket_id))
        return self._ensure_within_root(candidate)

    def ensure_bucket_directory(self, user_id: int, bucket_id: int) -> Path:
        try:
            directory = self.bucket_directory(user_id, bucket_id)
            (directory / "objects").mkdir(parents=True, exist_ok=True)
            return directory
        except OSError as exc:
            raise StorageAdapterError("The bucket directory could not be created.") from exc

    def object_path(self, bucket_dir: Path, storage_name: str) -> Path:
        if not _STORAGE_NAME_PATTERN.fullmatch(storage_name):
            raise StorageAdapterError("Invalid internal storage identifier.")
        objects_dir = self._ensure_within_root(bucket_dir / "objects")
        candidate = objects_dir / f"{storage_name}.bin"
        return self._ensure_within_root(candidate)

    def save_upload(
        self,
        bucket_dir: Path,
        upload_file: UploadSource,
        storage_name: str,
        max_bytes: int,
    ) -> tuple[int, str]:
        """Stream an upload to a temporary file, then atomically publish it."""
        destination = self.object_path(bucket_dir, storage_name)
        objects_dir = destination.parent
        temp_path = objects_dir / f".upload-{secrets.token_hex(12)}.tmp"
        digest = hashlib.sha256()
        size = 0

        try:
            objects_dir.mkdir(parents=True, exist_ok=True)
            with temp_path.open("wb") as target:
                while True:
                    chunk = upload_file.file.read(64 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_bytes:
                        raise UploadTooLargeError(
                            f"Files must be at most {max_bytes} bytes."
                        )
                    digest.update(chunk)
                    target.write(chunk)
            os.replace(temp_path, destination)
        except UploadTooLargeError:
            temp_path.unlink(missing_ok=True)
            raise
        except (OSError, ValueError) as exc:
            temp_path.unlink(missing_ok=True)
            raise StorageAdapterError("The uploaded file could not be saved.") from exc
        finally:
            upload_file.file.close()

        return size, digest.hexdigest()

    def remove_object(self, bucket_dir: Path, storage_name: str) -> None:
        try:
            self.object_path(bucket_dir, storage_name).unlink(missing_ok=True)
        except OSError as exc:
            raise StorageAdapterError("The stored object file could not be removed.") from exc

    def remove_bucket_directory(self, user_id: int, bucket_id: int) -> None:
        directory = self.bucket_directory(user_id, bucket_id)
        try:
            if directory.exists():
                shutil.rmtree(directory)
        except OSError as exc:
            raise StorageAdapterError("The bucket directory could not be removed.") from exc
