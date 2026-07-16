"""Tests for app/infra/connectors/context.py"""
from app.infra.connectors.context import grpc_deadline_remaining


def test_grpc_deadline_remaining_default():
    """The context var exists and defaults to None"""
    token = grpc_deadline_remaining.set(None)
    assert grpc_deadline_remaining.get() is None
    grpc_deadline_remaining.reset(token)


def test_grpc_deadline_remaining_set():
    token = grpc_deadline_remaining.set(5.0)
    assert grpc_deadline_remaining.get() == 5.0
    grpc_deadline_remaining.reset(token)
