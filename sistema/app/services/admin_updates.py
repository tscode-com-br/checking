import asyncio
import json
from datetime import datetime, timezone
from uuid import uuid4


class AdminUpdatesBroker:
    def __init__(self) -> None:
        self._subscribers: dict[str, asyncio.Queue[str]] = {}

    def subscribe(self) -> tuple[str, asyncio.Queue[str]]:
        subscriber_id = str(uuid4())
        self._subscribers[subscriber_id] = asyncio.Queue(maxsize=20)
        return subscriber_id, self._subscribers[subscriber_id]

    def unsubscribe(self, subscriber_id: str) -> None:
        self._subscribers.pop(subscriber_id, None)

    def publish(self, reason: str = "refresh", *, metadata: dict[str, object] | None = None) -> None:
        payload_dict: dict[str, object] = {
            "reason": reason,
            "emitted_at": datetime.now(timezone.utc).isoformat(),
        }
        if metadata:
            payload_dict.update({key: value for key, value in metadata.items() if value is not None})

        payload = json.dumps(payload_dict)

        for queue in list(self._subscribers.values()):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass

            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                continue


admin_updates_broker = AdminUpdatesBroker()
transport_updates_broker = AdminUpdatesBroker()


def notify_admin_data_changed(reason: str = "refresh", *, metadata: dict[str, object] | None = None) -> None:
    admin_updates_broker.publish(reason=reason, metadata=metadata)


def notify_transport_data_changed(reason: str = "refresh", *, metadata: dict[str, object] | None = None) -> None:
    transport_updates_broker.publish(reason=reason, metadata=metadata)