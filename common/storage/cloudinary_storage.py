import cloudinary
import cloudinary.uploader
import cloudinary.utils

class CloudinaryStorageError(Exception):
    """Raised when a Cloudinary storage operation fails."""


def upload_file(
    file,
    *,
    folder: str,
    resource_type: str = "auto",
) -> dict:
    """
    Upload a file to Cloudinary.

    Returns only the storage metadata required by the application.
    """

    try:
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type=resource_type,
            secure=True,
        )
    except Exception as exc:
        raise CloudinaryStorageError(
            "Failed to upload file to Cloudinary."
        ) from exc

    return {
        "public_id": result["public_id"],
        "secure_url": result.get("secure_url"),
        "resource_type": result.get("resource_type"),
        "format": result.get("format"),
        "bytes": result.get("bytes"),
        "original_filename": result.get("original_filename"),
    }


def delete_file(
    public_id: str,
    *,
    resource_type: str = "image",
) -> None:
    """
    Delete a file from Cloudinary.
    """

    try:
        cloudinary.uploader.destroy(
            public_id,
            resource_type=resource_type,
        )
    except Exception as exc:
        raise CloudinaryStorageError(
            "Failed to delete file from Cloudinary."
        ) from exc



def get_file_url(
    public_id: str,
    *,
    resource_type: str = "image",
) -> str:

    return cloudinary.utils.cloudinary_url(
        public_id,
        resource_type=resource_type,
        secure=True,
    )[0]    


    # -----------------------for front end to see the i.d card ------------------------------------  



def get_signed_file_url(
    public_id: str,
    *,
    resource_type: str = "image",
    expires_at=None,
) -> str:

    options = {
        "resource_type": resource_type,
        "secure": True,
        "sign_url": True,
    }

    if expires_at is not None:
        options["expires_at"] = expires_at

    url, _ = cloudinary.utils.cloudinary_url(
        public_id,
        **options,
    )

    return url    