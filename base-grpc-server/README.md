# my-app gRPC Server

[Vietnamese Version](README.vi.md)

Reusable gRPC-only server template based on the `tms-core/rpc` structure.

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
`app/rpc/proto`, then rewrites imports for `app.rpc.generated`.

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

- `app/rpc/proto`: protobuf contracts.
- `app/rpc/generated`: generated protobuf and gRPC code.
- `app/rpc/servicers`: gRPC request handlers.
- `app/rpc/services`: application services called by servicers.
- `app/rpc/channel.py`: reusable asynchronous client channel pool.
- `app/rpc/client.py`: health client example.
- `app/rpc/server.py`: server startup and servicer registration.
- `app/infra/otelemetry.py`: optional OTLP tracing for gRPC server and client.

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
