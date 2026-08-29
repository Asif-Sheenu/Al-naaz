from PIL import Image
from rest_framework import serializers


IDENTITY_PROOF_ALLOWED_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}

IDENTITY_PROOF_MAX_SIZE = 5 * 1024 * 1024


def validate_identity_proof_file(file):

    if not file:
        raise serializers.ValidationError(
            "Identity proof file is required."
        )

    if file.size > IDENTITY_PROOF_MAX_SIZE:
        raise serializers.ValidationError(
            "Identity proof file must not exceed 5 MB."
        )

    content_type = getattr(
        file,
        "content_type",
        None,
    )

    if content_type not in IDENTITY_PROOF_ALLOWED_TYPES:
        raise serializers.ValidationError(
            "Unsupported file type. "
            "Only PDF, JPEG, and PNG files are allowed."
        )

    file.seek(0)

    try:

        if content_type in {
            "image/jpeg",
            "image/png",
        }:
            try:
                image = Image.open(file)
                image.verify()

            except Exception as exc:
                raise serializers.ValidationError(
                    "The uploaded image is invalid or corrupted."
                ) from exc

        elif content_type == "application/pdf":

            header = file.read(5)

            if header != b"%PDF-":
                raise serializers.ValidationError(
                    "The uploaded file is not a valid PDF."
                )

    finally:
        file.seek(0)

    return file