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
- `app/db`: SQLAlchemy async database configuration and session helpers.
- `app/db/models`: Intentionally empty. Add database models here when needed.
- `app/tools`: Utility tools (e.g., PDF generation).
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
