# Base Service Templates

This repository provides three reusable `my-app` templates. Copy the template
that matches the new service boundary, rename `my-app` values, then initialize
its Poetry environment.

| Template | Use when | Main command |
| --- | --- | --- |
| [`base-fastapi`](base-fastapi/README.md) | The service exposes HTTP APIs and uses the standard FastAPI infrastructure. | `make start` |
| [`base-fastapi-grpc`](base-fastapi-grpc/README.md) | The service exposes HTTP APIs and calls upstream services through gRPC. | `make start`, `make proto` |
| [`base-grpc-server`](base-grpc-server/README.md) | The service exposes gRPC contracts directly and does not need FastAPI. | `make start-grpc-server`, `make proto` |

## Choose A Template

### FastAPI

Use [`base-fastapi`](base-fastapi/README.md) for REST/HTTP services. It includes
FastAPI, database and Redis infrastructure, Celery, observability, coverage,
and pre-commit checks.

- [English README](base-fastapi/README.md)
- [Vietnamese README](base-fastapi/README.vi.md)

```bash
cp -R base-fastapi ../my-app
cd ../my-app
cp app/env.example app/.env
make init-project
make start
```

### FastAPI gRPC Gateway

Use [`base-fastapi-grpc`](base-fastapi-grpc/README.md) when an HTTP API needs a
gRPC client. It adds protobuf generation, an asynchronous channel pool, gRPC
metadata propagation, and the `GET /api/v1/health/grpc` reference flow.

- [English README](base-fastapi-grpc/README.md)
- [Vietnamese README](base-fastapi-grpc/README.vi.md)

```bash
cp -R base-fastapi-grpc ../my-app
cd ../my-app
cp app/env.example app/.env
make init-project
make proto
make start
```

### gRPC Server

Use [`base-grpc-server`](base-grpc-server/README.md) for a standalone gRPC
service. It includes protobuf generation, generated stubs, service and
servicer layers, a reusable gRPC client, graceful shutdown, and optional OTLP
instrumentation.

- [English README](base-grpc-server/README.md)
- [Vietnamese README](base-grpc-server/README.vi.md)

```bash
cp -R base-grpc-server ../my-app
cd ../my-app
cp app/env.example app/.env
make init-project
make proto
make start-grpc-server
```

## Shared Checks

Each template provides the same basic verification workflow:

```bash
poetry check
make test
poetry run pre-commit run --all-files
```

`make test` creates coverage and pytest HTML reports in `tests/htmlcov/`.
