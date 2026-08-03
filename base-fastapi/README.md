# my-app

[Vietnamese Version](README.vi.md)

FastAPI service template for my-app.

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
- `app/db_models/models`: SQLAlchemy models. `common.py` provides timestamp and audit mixins.
- `app/db_models/migrations`: Alembic migration environment.
- `app/tools`: Utility tools (e.g., PDF generation).
- `../core` or `core`: Shared infrastructure based on `onflow-e-invoice/core`.
- `tests/`: Project unit and integration tests.

## Shared Core

This template no longer contains its own `core/` directory. Inside
`webapp_FastAPI`, commands load `../core` automatically. For a standalone
service, copy the shared core into the service root:

```bash
cp -R ../webapp_FastAPI/base-fastapi ../my-app
cp -R ../webapp_FastAPI/core ../my-app/core
cd ../my-app
```

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

- **Open Coverage Report**:
  ```bash
  make open-test-coverage
  ```
  Opens the HTML test coverage report in your default browser.

## Configuration

Settings are loaded from environment variables or `app/.env`.
See `app/env.example` for the DB, HTTP connector, FastAPI, and monitoring keys.

Endpoints available upon running:
- `GET /`
- `GET /api/v1/health`
- `GET /api/docs`

## Docker

From the `webapp_FastAPI` root:

```bash
docker build -f base-fastapi/Dockerfile --build-arg APP_DIR=base-fastapi -t my-app .
```

From a standalone copied service root containing `app/`, `core/`, and
`Dockerfile`:

```bash
docker build -t my-app .
```
