# my-app gRPC Server

[Vietnamese Version](README.vi.md)

Reusable gRPC-only server template using the shared `core/grpc_server` package.

## Setup

```bash
cp app/env.example app/.env
make init-project
```

## Commands

```bash
make proto
make start-grpc-server
make test
make open-test-coverage
```

`make proto` generates Python protobuf, type stubs, and gRPC stubs from
`core/grpc_server/proto`, then rewrites imports for `core.grpc_server.generated`.

## Run The gRPC Server

Copy the environment template, generate the stubs after changing any `.proto`
file, then start the server:

```bash
cp app/env.example app/.env
make proto
make start-grpc-server
```

The default listener is `0.0.0.0:50051`. Override the bind address for a local
run without editing `app/.env`:

```bash
GRPC_HOST=127.0.0.1 GRPC_PORT=50052 make start-grpc-server
```

The included health RPC is `my_app.health.v1.HealthService/Check` and returns
`SERVING`. Press `Ctrl-C` to stop the process; the server handles `SIGINT` and
`SIGTERM` and closes gracefully.

## Structure

- `app/settings`: service configuration and environment loading.
- `../core` or `core`: shared infrastructure based on `onflow-e-invoice/core`.
- `core/grpc_server/proto`: protobuf contracts.
- `core/grpc_server/generated`: generated protobuf and gRPC code.
- `core/grpc_server/servicers`: gRPC request handlers.
- `core/grpc_server/services`: application services called by servicers.
- `core/grpc_server/channel.py`: reusable asynchronous client channel pool.
- `core/grpc_server/client.py`: health client example.
- `core/grpc_server/server.py`: server startup and servicer registration.
- `core/grpc_server/otelemetry.py`: optional OTLP tracing for gRPC server and client.

## Shared Core

This template no longer contains its own `core/` directory. Inside
`webapp_FastAPI`, commands load `../core` automatically. For a standalone
service, copy the shared core into the service root:

```bash
cp -R ../webapp_FastAPI/base-grpc-server ../my-app
cp -R ../webapp_FastAPI/core ../my-app/core
cd ../my-app
```

## Health Example

`HealthService` is registered at `my_app.health.v1.HealthService/Check`.
The servicer delegates to `HealthService`, which returns `SERVING`. Use this
flow as the reference for a new contract: add proto, generate code, add a
service, add a servicer, then register it in `GrpcServer`.

Configure the server and optional client in `app/.env`:

```env
GRPC_HOST=0.0.0.0
GRPC_PORT=50051
GRPC_CLIENT_TARGET=127.0.0.1:50051
OPENTELEMETRY_ENDPOINT=
```
