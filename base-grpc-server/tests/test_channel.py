import pytest

from core.grpc_server.channel import GrpcChannelPool


@pytest.mark.asyncio
async def test_channel_pool_round_robin_and_close() -> None:
    pool = GrpcChannelPool("localhost:50051", size=2)

    first = pool.get_channel()
    second = pool.get_channel()

    assert first is not second
    assert pool.get_channel() is first

    await pool.close()


def test_channel_pool_requires_positive_size() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        GrpcChannelPool("localhost:50051", size=0)
