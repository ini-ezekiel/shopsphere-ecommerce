import logging
from pathlib import PurePosixPath
from uuid import uuid4

import cloudinary
from cloudinary import uploader
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import Storage

logger = logging.getLogger(__name__)


class CloudinaryMediaStorage(Storage):
    def _save(self, name, content):
        config = cloudinary.config()

        if not config.cloud_name or not config.api_key or not config.api_secret:
            raise ImproperlyConfigured(
                "Cloudinary credentials are missing or incomplete."
            )

        path = PurePosixPath(name.replace("\\", "/"))
        folder_parts = ["shopsphere"]

        if str(path.parent) != ".":
            folder_parts.append(str(path.parent))

        folder = "/".join(folder_parts)
        public_id = f"{path.stem}-{uuid4().hex}"

        if hasattr(content, "seek"):
            content.seek(0)

        try:
            result = uploader.upload(
                content,
                folder=folder,
                public_id=public_id,
                resource_type="image",
                overwrite=False,
                unique_filename=False,
            )
        except Exception:
            logger.exception("Cloudinary product-image upload failed.")
            raise

        return result["public_id"]

    def url(self, name):
        return cloudinary.CloudinaryImage(name).build_url(secure=True)

    def exists(self, name):
        return False

    def delete(self, name):
        if name:
            uploader.destroy(
                name,
                resource_type="image",
                invalidate=True,
            )
