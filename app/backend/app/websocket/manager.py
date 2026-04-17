import json
import uuid
from dataclasses import dataclass

from fastapi import WebSocket

from app.logging_config import get_logger

logger = get_logger("websocket.manager")


@dataclass
class ConnectionInfo:
    websocket: WebSocket
    tenant_id: uuid.UUID
    user_id: uuid.UUID


class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, ConnectionInfo] = {}
        self._tenant_connections: dict[uuid.UUID, set[str]] = {}

    @property
    def active_connection_count(self) -> int:
        return len(self._connections)

    async def connect(
        self,
        websocket: WebSocket,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> str:
        await websocket.accept()
        conn_id = str(uuid.uuid4())

        self._connections[conn_id] = ConnectionInfo(
            websocket=websocket,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        if tenant_id not in self._tenant_connections:
            self._tenant_connections[tenant_id] = set()
        self._tenant_connections[tenant_id].add(conn_id)

        logger.info(
            "Client connected: conn=%s tenant=%s user=%s (total=%d)",
            conn_id[:8], tenant_id, user_id, self.active_connection_count,
        )
        return conn_id

    def disconnect(self, conn_id: str) -> None:
        info = self._connections.pop(conn_id, None)
        if info and info.tenant_id in self._tenant_connections:
            self._tenant_connections[info.tenant_id].discard(conn_id)
            if not self._tenant_connections[info.tenant_id]:
                del self._tenant_connections[info.tenant_id]
            logger.info(
                "Client disconnected: conn=%s (total=%d)",
                conn_id[:8], self.active_connection_count,
            )

    async def broadcast_to_tenant(
        self,
        tenant_id: uuid.UUID,
        event_type: str,
        data: dict,
    ) -> None:
        message = json.dumps({"type": event_type, "data": data})
        conn_ids = self._tenant_connections.get(tenant_id, set()).copy()
        sent_count = 0
        for conn_id in conn_ids:
            info = self._connections.get(conn_id)
            if info:
                try:
                    await info.websocket.send_text(message)
                    sent_count += 1
                except Exception:
                    logger.warning("Failed to send to conn=%s, disconnecting", conn_id[:8])
                    self.disconnect(conn_id)

        logger.debug(
            "Broadcast event=%s to tenant=%s (%d/%d delivered)",
            event_type, tenant_id, sent_count, len(conn_ids),
        )

    async def send_to_user(
        self,
        user_id: uuid.UUID,
        event_type: str,
        data: dict,
    ) -> None:
        message = json.dumps({"type": event_type, "data": data})
        sent_count = 0
        for conn_id, info in list(self._connections.items()):
            if info.user_id == user_id:
                try:
                    await info.websocket.send_text(message)
                    sent_count += 1
                except Exception:
                    logger.warning("Failed to send to conn=%s, disconnecting", conn_id[:8])
                    self.disconnect(conn_id)

        logger.debug("Sent event=%s to user=%s (%d connections)", event_type, user_id, sent_count)


ws_manager = ConnectionManager()
