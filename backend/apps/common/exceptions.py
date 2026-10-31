from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    if isinstance(exc, ProtectedError):
        return Response(
            {"detail": "This record has business history. Archive it instead."}, status=409
        )
    if isinstance(exc, IntegrityError):
        return Response(
            {
                "detail": "A conflicting record already exists or a business constraint was violated."
            },
            status=409,
        )
    return drf_exception_handler(exc, context)
