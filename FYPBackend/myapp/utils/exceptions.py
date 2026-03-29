from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        status_code = response.status_code

        if isinstance(response.data, dict):
            message = response.data.get("message") or response.data.get("detail") or "Error"
            # Remove DRF internal keys from data payload
            data = {k: v for k, v in response.data.items() if k not in ["message", "detail"]}

            if not data:
                data = {}
        else:
            message = str(response.data)
            data = {}

        payload = {
            "message": message,
            "data": data,
            "status": status_code,
        }
        return Response(payload, status=status_code)

    return Response(
        {
            "message": "Internal server error",
            "data": {},
            "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
