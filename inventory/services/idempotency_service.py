import hashlib
import json
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException

from ..models import IdempotencyRecord


class IdempotencyConflict(APIException):
    status_code = 409
    default_detail = "Idempotency conflict."
    default_code = "idempotency_conflict"


def _normalize_payload(value):
    """
    Convert request data into a deterministic JSON-serializable structure.
    This ensures the same payload always produces the same hash.
    """

    if isinstance(value, dict):
        return {
            str(key): _normalize_payload(val)
            for key, val in sorted(value.items(), key=lambda item: str(item[0]))
        }

    if isinstance(value, (list, tuple)):
        return [_normalize_payload(item) for item in value]

    if hasattr(value, "lists"):
        return {
            str(key): sorted(
                str(item)
                for item in values
            )
            for key, values in sorted(
                value.lists(),
                key=lambda item: str(item[0]),
            )
        }

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


def generate_request_hash(request_data):
    """
    Generate SHA-256 hash from the request payload.
    """

    normalized_data = _normalize_payload(request_data)

    serialized_data = json.dumps(
        normalized_data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(
        serialized_data.encode("utf-8")
    ).hexdigest()


def get_idempotency_key(request):
    """
    Read and validate the Idempotency-Key HTTP header.
    """

    key = request.headers.get("Idempotency-Key")

    if not key:
        raise IdempotencyConflict(
            "Idempotency-Key header is required."
        )

    key = key.strip()

    if not key:
        raise IdempotencyConflict(
            "Idempotency-Key header cannot be empty."
        )

    if len(key) > 255:
        raise IdempotencyConflict(
            "Idempotency-Key cannot exceed 255 characters."
        )

    return key


def start_idempotent_operation(
    *,
    request,
    operation,
):
    """
    Start an idempotent operation.

    Returns:

        record, True
            New operation. Caller should execute the business operation.

        record, False
            Existing completed operation. Caller should replay
            the original resource.

    A PENDING operation means another request is currently processing
    the same idempotency key.
    """

    key = get_idempotency_key(request)

    request_hash = generate_request_hash(request.data)

    with transaction.atomic():

        record, created = IdempotencyRecord.objects.get_or_create(
            key=key,
            defaults={
                "operation": operation,
                "request_hash": request_hash,
                "user": request.user,
                "status": IdempotencyRecord.Status.PENDING,
                "expires_at": timezone.now() + timedelta(hours=24),
            },
        )

        if created:
            return record, True

        # Lock the existing record.
        record = (
            IdempotencyRecord.objects
            .select_for_update()
            .get(pk=record.pk)
        )

        # Same key cannot be used by another user.
        if record.user_id != request.user.id:
            raise IdempotencyConflict(
                "This Idempotency-Key has already been used by another user."
            )

        # Same key cannot be used for another operation.
        if record.operation != operation:
            raise IdempotencyConflict(
                "This Idempotency-Key has already been used for another operation."
            )

        # Same key + different request body is invalid.
        if record.request_hash != request_hash:
            raise IdempotencyConflict(
                "This Idempotency-Key was already used with different request data."
            )

        # Operation already completed.
        if record.status == IdempotencyRecord.Status.COMPLETED:
            return record, False

        # Another request is currently processing it.
        raise IdempotencyConflict(
            "This request is already being processed."
        )


def complete_idempotent_operation(
    *,
    record,
    resource_type,
    resource_id,
    response_status_code,
):
    """
    Mark the idempotent operation as successfully completed.
    """

    record.status = IdempotencyRecord.Status.COMPLETED
    record.resource_type = resource_type
    record.resource_id = resource_id
    record.response_status_code = response_status_code
    record.completed_at = timezone.now()

    record.save(
        update_fields=[
            "status",
            "resource_type",
            "resource_id",
            "response_status_code",
            "completed_at",
        ]
    )