# Database Session Management

This directory contains the database session management system. The architecture is designed to support both FastAPI HTTP Request contexts and Background Task/Worker contexts efficiently.

There are **two primary ways** to acquire a database session depending on your execution context.

---

## 1. Using FastAPI Dependencies (For HTTP API Routers)

**Context:** Use this method when you are writing API endpoints in FastAPI routers.
**Why:** FastAPI's `Depends()` will automatically inject the session, manage the connection lifecycle, commit/rollback transactions, and close the session when the HTTP request finishes. You don't need to manually use `async with` blocks.

### Examples

- `Depends(get_read_session)`: For READ-ONLY operations. It routes to the Replica database (if configured) to reduce load on the Master database.
- `Depends(get_write_session)`: For operations that modify data (POST, PUT, DELETE). It explicitly routes to the Master database.
- `Depends(get_auto_session)`: Automatically routes between Read and Write databases based on the operations executed.

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.dependencies import get_auto_session, get_read_session
from app.application.user_service import UserService

router = APIRouter()

# 1. READ operation
@router.get("/{user_id}")
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_read_session) 
):
    service = UserService(session)
    return await service.get_user_by_id(user_id)

# 2. WRITE operation
@router.post("/")
async def create_user(
    payload: dict,
    session: AsyncSession = Depends(get_auto_session)
):
    service = UserService(session)
    return await service.create_new_user(payload)
```

---

## 2. Using `session_scope` (For Background Tasks, Celery, gRPC, Cronjobs)

**Context:** Use this method when there is **NO HTTP Request context** (e.g., inside a Celery worker, a background task, a startup script, or a message queue consumer).
**Why:** Since FastAPI's `Depends()` cannot be used outside of HTTP routers, you must manually open and manage the database connection scope using `async with session_scope()`. When exiting the `with` block, the system automatically commits/rollbacks and safely closes the connection.

### Example

```python
from app.db.session_manager import session_scope
from app.application.user_service import UserService

async def process_background_job(user_id: int):
    # Manually open a database session scope
    # mode can be "auto", "read", or "write"
    async with session_scope(mode="write") as session:
        service = UserService(session)
        await service.update_user_status(user_id, status="PROCESSED")
        # Session is automatically committed and closed when exiting this block
```
