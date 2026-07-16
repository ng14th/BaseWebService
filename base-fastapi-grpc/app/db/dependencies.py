from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from .session_manager import managed_session


async def get_read_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with managed_session(
        request.app.state.read_session_factory,
        "read",
    ) as session:
        yield session


async def get_write_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with managed_session(
        request.app.state.write_session_factory,
        "write",
    ) as session:
        yield session


async def get_auto_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with managed_session(
        request.app.state.auto_session_factory,
        "auto",
    ) as session:
        yield session


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async for session in get_auto_session(request):
        yield session


# How to use
# @router.put("/")
# async def function_name(
#     session: AsyncSession = Depends(get_auto_session),
#     read_session: AsyncSession = Depends(get_read_session),
#     write_session: AsyncSession = Depends(get_write_session),
# ) -> None:
#     repo = OrderRepository(session)
#     await repo.get_by_id(3250)
