# my-app

[English Version](README.md)

FastAPI service template cho my-app.

## Cài đặt dự án

1. **Cài đặt Poetry**: Cài đặt poetry thông qua `pip install poetry` hoặc theo tài liệu chính thức.
2. **Kích hoạt Environment**: Mở shell với môi trường ảo của dự án:
   ```bash
   poetry shell
   ```
3. **Khởi tạo Project**: Cài đặt các thư viện phụ thuộc và thiết lập pre-commit hooks:
   ```bash
   make init-project
   ```

## Cấu trúc Repository

- `app/api`: Định nghĩa các HTTP route và cấu hình FastAPI application.
- `app/domain`: Các domain entity và repository contract.
- `app/infra`: Các adapter hạ tầng, bao gồm outbound connector.
- `app/db_models/models`: SQLAlchemy model. `common.py` có sẵn timestamp và audit mixin.
- `app/db_models/migrations`: Alembic migration environment.
- `app/tools`: Công cụ tiện ích (VD: tạo PDF).
- `../core` hoặc `core`: Hạ tầng dùng chung theo chuẩn `onflow-e-invoice/core`.
- `tests/`: Chứa các test unit và integration cho dự án.

## Shared Core

Template này không còn chứa `core/` riêng bên trong base. Khi làm việc trong
repo `webapp_FastAPI`, Makefile tự load `../core`. Khi tạo service độc lập, copy
kèm shared core vào root của service:

```bash
cp -R ../webapp_FastAPI/base-fastapi ../my-app
cp -R ../webapp_FastAPI/core ../my-app/core
cd ../my-app
```

## Lệnh khởi chạy (Makefile)

Bạn có thể chạy các lệnh sau với `make`:

- **Khởi chạy Server**: 
  ```bash
  make start
  ```
  Chạy ứng dụng ở chế độ thông thường.

- **Chạy Test**:
  ```bash
  make test
  ```
  Chạy pytest có kèm theo báo cáo độ bao phủ (coverage report).

- **Mở báo cáo Coverage**:
  ```bash
  make open-test-coverage
  ```
  Mở bản báo cáo test coverage (dạng HTML) bằng trình duyệt mặc định.

## Cấu hình

Dự án đọc biến môi trường từ file `app/.env` hoặc từ hệ thống.
Xem `app/env.example` để cấu hình DB, HTTP connector, FastAPI và monitoring.

Các endpoint có sẵn khi chạy:
- `GET /`
- `GET /api/v1/health`
- `GET /api/docs`

## Docker

Từ root `webapp_FastAPI`:

```bash
docker build -f base-fastapi/Dockerfile --build-arg APP_DIR=base-fastapi -t my-app .
```

Từ service độc lập đã copy, có `app/`, `core/` và `Dockerfile` cùng cấp:

```bash
docker build -t my-app .
```
