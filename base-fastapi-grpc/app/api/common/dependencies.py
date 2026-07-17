from fastapi import Request, status

from core.schemas.server.exception import ErrorResponseException


def check_required_auth_header(request: Request):
    token = request.headers.get("Authorization")
    client_id = request.headers.get("X-Client-ID")

    if not token or not client_id:
        raise ErrorResponseException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="Authorization header and X-Client-ID header are required",
        )
    return True


def check_request_id(request: Request):
    x_request_id = request.headers.get("x-request-id")
    if not x_request_id:
        raise ErrorResponseException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Header X-Request-ID is required",
        )
    return x_request_id
