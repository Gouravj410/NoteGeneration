import os
import shutil
from typing import BinaryIO
from app.core.config import settings

class FileStorageService:
    def __init__(self):
        self.local_dir = settings.STORAGE_DIR
        if not settings.S3_BUCKET:
            os.makedirs(self.local_dir, exist_ok=True)

    def save_file(self, file_obj: BinaryIO, storage_key: str) -> str:
        """
        Saves a binary file stream. Returns the local path or S3 url.
        """
        if settings.S3_BUCKET:
            # TODO: Configure AWS boto3 S3 upload client
            raise NotImplementedError("S3 storage upload not configured yet.")
        else:
            local_path = os.path.join(self.local_dir, storage_key)
            # Ensure subdirectories exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                shutil.copyfileobj(file_obj, f)
            return local_path

    def get_file_path(self, storage_key: str) -> str:
        """
        Resolves a storage key to a local filesystem absolute path.
        """
        if settings.S3_BUCKET:
            # In S3 production mode, we would download the file locally to temp path
            raise NotImplementedError("S3 storage download not configured yet.")
        return os.path.abspath(os.path.join(self.local_dir, storage_key))

    def delete_file(self, storage_key: str) -> None:
        """
        Removes a file.
        """
        if settings.S3_BUCKET:
            # TODO: Configure AWS boto3 S3 delete client
            pass
        else:
            local_path = os.path.join(self.local_dir, storage_key)
            if os.path.exists(local_path):
                os.remove(local_path)

storage_service = FileStorageService()
