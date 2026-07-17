import grpc
from fastapi import Request

from core.schemas.server.exception import ErrorResponseException

GRPC_HTTP_STATUS_CODE_MAP: dict[grpc.StatusCode, int] = {
    grpc.StatusCode.DEADLINE_EXCEEDED: 504,
    grpc.StatusCode.UNAVAILABLE: 503,
    grpc.StatusCode.UNAUTHENTICATED: 401,
    grpc.StatusCode.PERMISSION_DENIED: 403,
}


def build_grpc_metadata(request: Request) -> list[tuple[str, str]]:
    route = request.scope.get("route")
    route_path = route.path if route else request.url.path
    token = request.headers.get("authorization", "")
    client_id = request.headers.get("x-client-id", "")
    access_token = request.query_params.get("access_token", "")
    query_client_id = request.query_params.get("client_id", "")

    if access_token and not token:
        token = (
            access_token
            if access_token.lower().startswith("bearer ")
            else f"Bearer {access_token}"
        )
    if query_client_id and not client_id:
        client_id = query_client_id

    return [
        ("authorization", token),
        ("client_id", client_id),
        ("route_path", route_path),
        ("http_method", request.method),
    ]


def grpc_error_response(error: grpc.RpcError) -> ErrorResponseException:
    return ErrorResponseException(
        status_code=GRPC_HTTP_STATUS_CODE_MAP.get(error.code(), 500),
        message="gRPC upstream request failed",
    )
