# my-app gRPC Server

[English Version](README.md)

Template gRPC server độc lập, tái sử dụng theo cấu trúc `tms-core/rpc`.

## Khởi tạo

```bash
cp app/env.example app/.env
make init-project
```

## Lệnh sử dụng

```bash
make proto
make start-grpc-server
make test
make open-test-coverage
```

`make proto` sinh mã Python protobuf, type stub và gRPC stub từ
`app/rpc/proto`, sau đó chuẩn hóa import về package `app.rpc.generated`.

## Chạy gRPC Server

Copy file môi trường, sinh lại stub sau mỗi lần thay đổi `.proto`, sau đó khởi
động server:

```bash
cp app/env.example app/.env
make proto
make start-grpc-server
```

Mặc định server lắng nghe tại `0.0.0.0:50051`. Có thể ghi đè địa chỉ bind khi
chạy local mà không cần sửa `app/.env`:

```bash
GRPC_HOST=127.0.0.1 GRPC_PORT=50052 make start-grpc-server
```

Health RPC có sẵn là `my_app.health.v1.HealthService/Check`, trả về `SERVING`.
Nhấn `Ctrl-C` để dừng process; server xử lý `SIGINT` và `SIGTERM` để đóng
graceful.

## Cấu trúc

- `app/rpc/proto`: protobuf contract.
- `app/rpc/generated`: mã protobuf và gRPC được sinh tự động.
- `app/rpc/servicers`: handler nhận request gRPC.
- `app/rpc/services`: service nghiệp vụ được servicer gọi.
- `app/rpc/channel.py`: channel pool client bất đồng bộ có thể tái sử dụng.
- `app/rpc/client.py`: ví dụ health client.
- `app/rpc/server.py`: khởi động server và đăng ký servicer.
- `app/infra/otelemetry.py`: tracing OTLP tùy chọn cho gRPC server/client.

## Ví dụ Health

`HealthService` được đăng ký tại `my_app.health.v1.HealthService/Check`.
Servicer gọi `HealthService` và trả trạng thái `SERVING`. Dùng luồng này làm
mẫu cho contract mới: thêm proto, generate code, thêm service, thêm servicer,
và đăng ký vào `GrpcServer`.

Cấu hình server và client tùy chọn tại `app/.env`:

```env
GRPC_HOST=0.0.0.0
GRPC_PORT=50051
GRPC_CLIENT_TARGET=127.0.0.1:50051
OPENTELEMETRY_ENDPOINT=
```
