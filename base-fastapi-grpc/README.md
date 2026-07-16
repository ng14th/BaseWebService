# my-app

[Vietnamese Version](README.vi.md)

FastAPI and gRPC client service template for my-app.

## Setup Project

1. **Install Poetry**: If you haven't already, install poetry using `pip install poetry` or follow the official documentation.
2. **Activate Environment**: Spawn a shell within the virtual environment using:
   ```bash
   poetry shell
   ```
3. **Initialize Project**: Install dependencies and setup pre-commit hooks:
   ```bash
   make init-project
   ```

## Repository Structure

- `app/api`: HTTP routes and FastAPI application wiring.
- `app/domain`: Domain entities and repository contracts.
- `app/infra`: Infrastructure adapters such as outbound connectors.
- `app/db`: SQLAlchemy async database configuration and session helpers.
- `app/db/models`: Intentionally empty. Add database models here when needed.
- `app/tools`: Utility tools (e.g., PDF generation).
- `app/rpc/proto`: Source protobuf contracts, grouped by domain.
- `app/rpc/generated`: Python protobuf and gRPC stubs generated from `app/rpc/proto`.
- `app/rpc/channel.py`: Reusable asynchronous gRPC channel pool.
- `tests/`: Project unit and integration tests.

## Available Commands

You can run the following commands using `make`:

- **Start Server**: 
  ```bash
  make start
  ```
  Runs the application in standard mode.

- **Run Tests**:
  ```bash
  make test
  ```
  Runs pytest with coverage report generation.

- **Generate gRPC Stubs**:
  ```bash
  make proto
  ```
  Generates Python, type stub, and gRPC code from every `.proto` file in
  `app/rpc/proto`. Generated imports are normalized for the `app.rpc.generated`
  package.

- **Open Coverage Report**:
  ```bash
  make open-test-coverage
  ```
  Opens the HTML test coverage report in your default browser.

## Configuration

Settings are loaded from environment variables or `app/.env`.
See `app/env.example` for the DB, HTTP connector, FastAPI, gRPC, and monitoring keys.

## gRPC

The template includes `app/rpc/proto/health/health.proto` as a minimal contract.
Add new contracts below `app/rpc/proto`, then run `make proto` and commit the
corresponding files from `app/rpc/generated`.

To enable the optional shared gRPC client pool, configure a target:

```env
GRPC_TARGET=localhost:50051
GRPC_POOL_SIZE=1
GRPC_TIMEOUT_SECONDS=20
```

When `GRPC_TARGET` is empty, the FastAPI service starts without creating gRPC
channels. Access an enabled pool through `request.app.state.grpc_channel_pool`.

`GET /api/v1/health/grpc` is the reference gateway flow:

- `app/api/health/dependencies.py` builds `HealthServiceStub` from the channel pool.
- `app/api/common/grpc.py` builds request metadata for the upstream call.
- `app/api/health/services.py` invokes the generated stub and maps gRPC errors.
- `app/api/health/views.py` composes the auth, rate-limit, stub, and service dependencies.

Call the example with the required gateway headers:

```bash
curl http://localhost:8989/api/v1/health/grpc \
  -H 'Authorization: Bearer access-token' \
  -H 'X-Client-ID: client-1'
```

Endpoints available upon running:
- `GET /`
- `GET /api/v1/health`
- `GET /api/docs`
