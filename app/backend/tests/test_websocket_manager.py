"""Tests for the WebSocket connection manager."""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.websocket.manager import ConnectionManager


@pytest.fixture
def manager():
    return ConnectionManager()


@pytest.fixture
def mock_websocket():
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def tenant_a():
    return uuid.uuid4()


@pytest.fixture
def tenant_b():
    return uuid.uuid4()


@pytest.fixture
def user_a():
    return uuid.uuid4()


@pytest.fixture
def user_b():
    return uuid.uuid4()


class TestConnect:
    @pytest.mark.asyncio
    async def test_connect_accepts_websocket(self, manager, mock_websocket, tenant_a, user_a):
        conn_id = await manager.connect(mock_websocket, tenant_a, user_a)
        mock_websocket.accept.assert_called_once()
        assert isinstance(conn_id, str)
        assert manager.active_connection_count == 1

    @pytest.mark.asyncio
    async def test_multiple_connections_tracked(self, manager, tenant_a, user_a, user_b):
        ws1, ws2 = AsyncMock(), AsyncMock()
        await manager.connect(ws1, tenant_a, user_a)
        await manager.connect(ws2, tenant_a, user_b)
        assert manager.active_connection_count == 2


class TestDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, manager, mock_websocket, tenant_a, user_a):
        conn_id = await manager.connect(mock_websocket, tenant_a, user_a)
        manager.disconnect(conn_id)
        assert manager.active_connection_count == 0

    def test_disconnect_nonexistent_does_not_raise(self, manager):
        manager.disconnect("nonexistent-id")

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up_tenant_mapping(self, manager, mock_websocket, tenant_a, user_a):
        conn_id = await manager.connect(mock_websocket, tenant_a, user_a)
        manager.disconnect(conn_id)
        assert tenant_a not in manager._tenant_connections


class TestBroadcastToTenant:
    @pytest.mark.asyncio
    async def test_broadcasts_to_all_tenant_connections(self, manager, tenant_a, user_a, user_b):
        ws1, ws2 = AsyncMock(), AsyncMock()
        await manager.connect(ws1, tenant_a, user_a)
        await manager.connect(ws2, tenant_a, user_b)

        await manager.broadcast_to_tenant(tenant_a, "test:event", {"key": "value"})

        expected = json.dumps({"type": "test:event", "data": {"key": "value"}})
        ws1.send_text.assert_called_once_with(expected)
        ws2.send_text.assert_called_once_with(expected)

    @pytest.mark.asyncio
    async def test_does_not_broadcast_to_other_tenants(self, manager, tenant_a, tenant_b, user_a, user_b):
        ws_a, ws_b = AsyncMock(), AsyncMock()
        await manager.connect(ws_a, tenant_a, user_a)
        await manager.connect(ws_b, tenant_b, user_b)

        await manager.broadcast_to_tenant(tenant_a, "test:event", {})

        ws_a.send_text.assert_called_once()
        ws_b.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_failed_send_gracefully(self, manager, tenant_a, user_a):
        ws = AsyncMock()
        ws.send_text.side_effect = Exception("Connection lost")
        conn_id = await manager.connect(ws, tenant_a, user_a)

        await manager.broadcast_to_tenant(tenant_a, "test:event", {})
        assert manager.active_connection_count == 0

    @pytest.mark.asyncio
    async def test_broadcast_to_empty_tenant(self, manager, tenant_a):
        await manager.broadcast_to_tenant(tenant_a, "test:event", {})


class TestSendToUser:
    @pytest.mark.asyncio
    async def test_sends_only_to_target_user(self, manager, tenant_a, user_a, user_b):
        ws_a, ws_b = AsyncMock(), AsyncMock()
        await manager.connect(ws_a, tenant_a, user_a)
        await manager.connect(ws_b, tenant_a, user_b)

        await manager.send_to_user(user_a, "personal:event", {"msg": "hi"})

        expected = json.dumps({"type": "personal:event", "data": {"msg": "hi"}})
        ws_a.send_text.assert_called_once_with(expected)
        ws_b.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_to_all_user_connections(self, manager, tenant_a, user_a):
        ws1, ws2 = AsyncMock(), AsyncMock()
        await manager.connect(ws1, tenant_a, user_a)
        await manager.connect(ws2, tenant_a, user_a)

        await manager.send_to_user(user_a, "event", {})
        assert ws1.send_text.call_count == 1
        assert ws2.send_text.call_count == 1
