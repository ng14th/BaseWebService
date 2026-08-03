# Base Service Templates

This repository provides three reusable `my-app` templates plus one shared
`core` package. The shared `core` package is based on `onflow-e-invoice/core`
and owns common FastAPI, DB, Redis, logging, rate-limit, HTTP connector,
circuit-breaker, and gRPC infrastructure.

```text
webapp_FastAPI/
  core/
  base-fastapi/
  base-fastapi-grpc/
  base-grpc-server/
```

| Template | Use when | Main command |
| --- | --- | --- |
| [`base-fastapi`](base-fastapi/README.md) | The service exposes HTTP APIs and uses the standard FastAPI infrastructure. | `make start` |
| [`base-fastapi-grpc`](base-fastapi-grpc/README.md) | The service exposes HTTP APIs and calls upstream services through gRPC. | `make start`, `make proto` |
| [`base-grpc-server`](base-grpc-server/README.md) | The service exposes gRPC contracts directly and does not need FastAPI. | `make start-grpc-server`, `make proto` |

## Shared Core

`core/` lives next to the base templates instead of inside each base. When you
work in this repository, the Makefiles automatically load `../core`.

When creating a new service from a template, copy both the selected base and the
shared core into the new service root:

```bash
cp -R base-fastapi ../my-app
cp -R core ../my-app/core
cd ../my-app
cp app/env.example app/.env
make init-project
```

For `base-fastapi-grpc` and `base-grpc-server`, protobuf source and generated
code live under `core/grpc_client` and `core/grpc_server`.

## Choose A Template

### FastAPI

Use [`base-fastapi`](base-fastapi/README.md) for REST/HTTP services. It includes
FastAPI, database and Redis infrastructure, Celery, observability, coverage,
and pre-commit checks.

- [English README](base-fastapi/README.md)
- [Vietnamese README](base-fastapi/README.vi.md)

```bash
cp -R base-fastapi ../my-app
cp -R core ../my-app/core
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
cp -R core ../my-app/core
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
cp -R core ../my-app/core
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

Build Docker images from a context that contains both the base folder and
`core/`:

```bash
docker build -f base-fastapi/Dockerfile --build-arg APP_DIR=base-fastapi -t my-app .
docker build -f base-fastapi-grpc/Dockerfile --build-arg APP_DIR=base-fastapi-grpc -t my-app .
```

After copying a base and `core/` into a standalone service root, run
`docker build -t my-app .` from that service root.
