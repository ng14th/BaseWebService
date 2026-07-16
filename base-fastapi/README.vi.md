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
- `app/db`: Cấu hình SQLAlchemy async database và session helper.
- `app/db/models`: Để trống để bạn tự tạo model.
- `app/tools`: Công cụ tiện ích (VD: tạo PDF).
- `tests/`: Chứa các test unit và integration cho dự án.

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
