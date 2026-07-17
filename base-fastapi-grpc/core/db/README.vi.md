# Quản lý Database Session

Thư mục này chứa hệ thống quản lý session (kết nối) cơ sở dữ liệu. Kiến trúc này được thiết kế để hỗ trợ tối đa cho cả ngữ cảnh chạy API (HTTP Request) và ngữ cảnh chạy ngầm (Background Task/Worker).

Có **2 cách chính** để khởi tạo database session tùy thuộc vào ngữ cảnh code của bạn.

---

## 1. Sử dụng FastAPI Dependencies (Dành cho API Routers)

**Ngữ cảnh:** Sử dụng cách này khi bạn viết các endpoint API trong FastAPI Router.
**Tại sao:** Cơ chế `Depends()` của FastAPI sẽ tự động nhúng session vào router, tự động quản lý vòng đời (mở connection, tự động commit/rollback khi kết thúc request, và đóng connection). Bạn không cần phải mở bằng tay `async with`.

### Các loại Dependency:
- `Depends(get_read_session)`: Dùng cho các tác vụ CHỈ ĐỌC (GET). Nó sẽ điều hướng query vào DB Replica (nếu có cấu hình) để giảm tải cho DB Master.
- `Depends(get_write_session)`: Dùng cho các tác vụ làm thay đổi dữ liệu (POST, PUT, DELETE). Trực tiếp trỏ vào DB Master.
- `Depends(get_auto_session)`: Tự động điều hướng giữa DB Read và DB Write dựa trên loại lệnh SQL đang được thực thi.

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.dependencies import get_auto_session, get_read_session
from app.application.user_service import UserService

router = APIRouter()

# 1. API Đọc dữ liệu
@router.get("/{user_id}")
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_read_session) 
):
    service = UserService(session)
    return await service.get_user_by_id(user_id)

# 2. API Ghi dữ liệu
@router.post("/")
async def create_user(
    payload: dict,
    session: AsyncSession = Depends(get_auto_session)
):
    service = UserService(session)
    return await service.create_new_user(payload)
```

---

## 2. Sử dụng `session_scope` (Dành cho Background Tasks, Celery, gRPC, Cronjobs)

**Ngữ cảnh:** Sử dụng cách này ở những nơi **KHÔNG CÓ HTTP Request** (ví dụ: Celery worker, scripts chạy định kỳ, Kafka consumers...).
**Tại sao:** Do `Depends()` của FastAPI không hoạt động bên ngoài router, bạn phải tự mở và quản lý kết nối DB bằng tay thông qua `async with session_scope()`. Khi thoát ra khỏi block `with`, hệ thống sẽ tự động commit/rollback và đóng kết nối an toàn.

### Ví dụ:

```python
from app.db.session_manager import session_scope
from app.application.user_service import UserService

async def process_background_job(user_id: int):
    # Tự mở scope quản lý DB connection
    # mode có thể là "auto", "read", hoặc "write"
    async with session_scope(mode="write") as session:
        service = UserService(session)
        await service.update_user_status(user_id, status="PROCESSED")
        # Session sẽ tự động được commit và đóng kết nối khi thoát khỏi block này
```
