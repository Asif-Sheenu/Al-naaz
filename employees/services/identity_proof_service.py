from django.db import transaction

from common.storage.cloudinary_storage import (
    CloudinaryStorageError,
    upload_file,
    delete_file,
    get_file_url,
    get_signed_file_url
)

from common.validators.file_validators import (
    validate_identity_proof_file,
)

from ..models import Employee, EmployeeIdentityProof


IDENTITY_PROOF_FOLDER = (
    "al-naaz/employees/identity-proofs"
)


@transaction.atomic
def create_identity_proof(
    *,
    employee: Employee,
    document_type: str,
    document_number: str,
    file,
    uploaded_by,
) -> EmployeeIdentityProof:

    if EmployeeIdentityProof.objects.filter(
        employee=employee
    ).exists():
        raise ValueError(
            "This employee already has an identity proof."
        )

    if not file:
        raise ValueError(
            "Identity proof file is required."
        )

    # Validate before uploading to Cloudinary
    validate_identity_proof_file(file)

    try:
        upload_result = upload_file(
            file,
            folder=IDENTITY_PROOF_FOLDER,
            resource_type="auto",
        )

    except CloudinaryStorageError:
        raise ValueError(
            "Failed to upload identity proof."
        )

    try:
        identity_proof = (
            EmployeeIdentityProof.objects.create(
                employee=employee,
                document_type=document_type,
                document_number=document_number,
                cloudinary_public_id=(
                    upload_result["public_id"]
                ),
                cloudinary_resource_type=(
                upload_result["resource_type"]
                ),
                original_filename=(
                    upload_result["original_filename"]
                    or file.name
                ),
                mime_type=(
                    getattr(file, "content_type", "")
                    or ""
                ),
                file_size=(
                    upload_result["bytes"]
                ),
                uploaded_by=uploaded_by,
            )
        )

    except Exception:

        # Database creation failed after Cloudinary
        # upload, so remove the orphaned Cloudinary file.
        try:
            delete_file(
                upload_result["public_id"],
                resource_type=(
                    upload_result["resource_type"]
                ),
            )
        except CloudinaryStorageError:
            pass

        raise

    return identity_proof


def get_identity_proof_url(
    *,
    employee: Employee,
) -> str:

    try:
        identity_proof = employee.identity_proof
    except EmployeeIdentityProof.DoesNotExist:
        raise ValueError(
            "Identity proof not found for this employee."
        )

    return get_file_url(
        identity_proof.cloudinary_public_id,
        resource_type="image",
    )


# -----------------------------------------------------------for front end to see adhaar --   

def get_identity_proof_file_url(
    *,
    employee: Employee,
) -> str:

    try:
        identity_proof = employee.identity_proof

    except EmployeeIdentityProof.DoesNotExist:
        raise ValueError(
            "Identity proof not found for this employee."
        )

    return get_signed_file_url(
        identity_proof.cloudinary_public_id,
        resource_type=(
            identity_proof.cloudinary_resource_type
        ),
    )
