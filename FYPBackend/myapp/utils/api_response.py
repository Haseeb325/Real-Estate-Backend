from rest_framework import status
from rest_framework.response import Response


def success_response(data=None, message="Success", status_code=status.HTTP_200_OK):
    payload = {
        "message": message,
        "data": data if data is not None else {},
        "status": status_code,
    }
    return Response(payload, status=status_code)


def error_response(message="Error", data=None, status_code=status.HTTP_400_BAD_REQUEST):
    payload = {
        "message": message,
        "data": data if data is not None else {},
        "status": status_code,
    }
    return Response(payload, status=status_code)
