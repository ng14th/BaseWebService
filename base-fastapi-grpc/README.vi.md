# my-app

[English Version](README.md)

FastAPI service template có tích hợp gRPC client cho my-app.

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
- `app/rpc/proto`: Các protobuf contract nguồn, được nhóm theo domain.
- `app/rpc/generated`: Mã Python protobuf và gRPC stub sinh từ `app/rpc/proto`.
- `app/rpc/channel.py`: Channel pool gRPC bất đồng bộ có thể tái sử dụng.
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

- **Sinh gRPC Stub**:
  ```bash
  make proto
  ```
  Sinh mã Python, type stub và gRPC từ mọi file `.proto` trong
  `app/rpc/proto`. Import của mã sinh được chuẩn hóa theo package
  `app.rpc.generated`.

- **Mở báo cáo Coverage**:
  ```bash
  make open-test-coverage
  ```
  Mở bản báo cáo test coverage (dạng HTML) bằng trình duyệt mặc định.

## Cấu hình

Dự án đọc biến môi trường từ file `app/.env` hoặc từ hệ thống.
Xem `app/env.example` để cấu hình DB, HTTP connector, FastAPI, gRPC và monitoring.

## gRPC

Template có sẵn contract tối giản `app/rpc/proto/health/health.proto`. Thêm
contract mới dưới `app/rpc/proto`, chạy `make proto`, sau đó commit các file
tương ứng trong `app/rpc/generated`.

Để bật channel pool gRPC dùng chung, cấu hình target:

```env
GRPC_TARGET=localhost:50051
GRPC_POOL_SIZE=1
GRPC_TIMEOUT_SECONDS=20
```

Khi `GRPC_TARGET` rỗng, FastAPI khởi động mà không tạo gRPC channel. Khi đã bật,
truy cập pool qua `request.app.state.grpc_channel_pool`.

`GET /api/v1/health/grpc` là luồng gateway tham khảo:

- `app/api/health/dependencies.py` tạo `HealthServiceStub` từ channel pool.
- `app/api/common/grpc.py` tạo metadata của request cho upstream gRPC.
- `app/api/health/services.py` gọi generated stub và map lỗi gRPC.
- `app/api/health/views.py` kết hợp dependency auth, rate-limit, stub và service.

Gọi ví dụ với các header gateway bắt buộc:

```bash
curl http://localhost:8989/api/v1/health/grpc \
  -H 'Authorization: Bearer access-token' \
  -H 'X-Client-ID: client-1'
```

Các endpoint có sẵn khi chạy:
- `GET /`
- `GET /api/v1/health`
- `GET /api/docs`
