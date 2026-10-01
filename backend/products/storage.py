from pathlib import PurePosixPath
from uuid import uuid4

import cloudinary
from cloudinary import uploader
from django.core.files.storage import Storage


class CloudinaryMediaStorage(Storage):
    def _save(self, name, content):
        path = PurePosixPath(name.replace("\\", "/"))

        folder_parts = ["shopsphere"]

        if str(path.parent) != ".":
            folder_parts.append(str(path.parent))

        folder = "/".join(folder_parts)
        public_id = f"{path.stem}-{uuid4().hex}"

        if hasattr(content, "seek"):
            content.seek(0)

        result = uploader.upload(
            content,
            folder=folder,
            public_id=public_id,
            resource_type="image",
            overwrite=False,
            unique_filename=False,
        )

        return result["public_id"]

    def url(self, name):
        return cloudinary.CloudinaryImage(name).build_url(
            secure=True,
        )

    def exists(self, name):
        return False

    def delete(self, name):
        if name:
            uploader.destroy(
                name,
                resource_type="image",
                invalidate=True,
            )
