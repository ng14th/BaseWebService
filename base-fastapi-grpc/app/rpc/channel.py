import itertools
from typing import Any

import grpc


class GrpcChannelPool:
    def __init__(self, target: str, size: int = 1) -> None:
        if size < 1:
            raise ValueError("GrpcChannelPool size must be at least 1")

        self.channels = [
            grpc.aio.insecure_channel(
                target,
                options=self._build_channel_options(index),
            )
            for index in range(size)
        ]
        self._cycle = itertools.cycle(self.channels)

    def get_channel(self) -> grpc.aio.Channel:
        return next(self._cycle)

    async def close(self) -> None:
        for channel in self.channels:
            await channel.close()

    @staticmethod
    def _build_channel_options(index: int) -> list[tuple[str, Any]]:
        return [
            ("grpc.lb_policy_name", "round_robin"),
            ("grpc.keepalive_time_ms", 30000),
            ("grpc.keepalive_timeout_ms", 10000),
            ("grpc.keepalive_permit_without_calls", 1),
            ("grpc.primary_user_agent", f"my-app-grpc-client-{index}"),
        ]
