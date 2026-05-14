import asyncio
import json
import logging
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import text

from ..core.config import settings
from ..database import engine

try:
    import psycopg
    from psycopg import sql
except ImportError:  # pragma: no cover - psycopg is installed in runtime targets.
    psycopg = None
    sql = None


REALTIME_LOGGER = logging.getLogger("checking.realtime")
DEFAULT_SUBSCRIBER_QUEUE_SIZE = 20
RECENT_EVENT_ID_CAPACITY = 256
LISTENER_RECONNECT_INITIAL_SECONDS = 1.0
LISTENER_RECONNECT_MAX_SECONDS = 10.0


@dataclass(slots=True)
class _BrokerSubscriber:
    queue: asyncio.Queue[str]
    loop: asyncio.AbstractEventLoop | None


class AdminUpdatesBroker:
    def __init__(
        self,
        channel_name: str | None = None,
        *,
        queue_maxsize: int = DEFAULT_SUBSCRIBER_QUEUE_SIZE,
    ) -> None:
        self._channel_name = str(channel_name or "").strip() or None
        self._queue_maxsize = max(int(queue_maxsize), 1)
        self._subscribers: dict[str, _BrokerSubscriber] = {}
        self._subscribers_lock = threading.Lock()
        self._recent_event_ids: deque[str] = deque()
        self._recent_event_ids_set: set[str] = set()
        self._recent_event_ids_lock = threading.Lock()
        self._listener_stop_event = threading.Event()
        self._listener_thread: threading.Thread | None = None
        self._listener_thread_lock = threading.Lock()
        self._postgres_conninfo = self._build_postgres_conninfo()

    def _build_postgres_conninfo(self) -> str | None:
        if engine.url.get_backend_name() != "postgresql":
            return None
        driverless_url = engine.url.set(drivername="postgresql")
        return driverless_url.render_as_string(hide_password=False)

    def _supports_cross_worker(self) -> bool:
        return bool(self._channel_name and self._postgres_conninfo and psycopg is not None and sql is not None)

    def start(self) -> None:
        if not self._supports_cross_worker():
            return

        with self._listener_thread_lock:
            if self._listener_thread is not None and self._listener_thread.is_alive():
                return

            self._listener_stop_event.clear()
            self._listener_thread = threading.Thread(
                target=self._listen_for_notifications,
                name=f"realtime-broker-{self._channel_name}",
                daemon=True,
            )
            self._listener_thread.start()

    def stop(self) -> None:
        with self._listener_thread_lock:
            listener_thread = self._listener_thread
            self._listener_thread = None
            self._listener_stop_event.set()

        if listener_thread is not None and listener_thread.is_alive():
            listener_thread.join(timeout=5)

    def subscribe(self) -> tuple[str, asyncio.Queue[str]]:
        subscriber_id = str(uuid4())
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=self._queue_maxsize)
        with self._subscribers_lock:
            self._subscribers[subscriber_id] = _BrokerSubscriber(queue=queue, loop=loop)
        return subscriber_id, queue

    def unsubscribe(self, subscriber_id: str) -> None:
        with self._subscribers_lock:
            self._subscribers.pop(subscriber_id, None)

    def publish(self, reason: str = "refresh", *, metadata: dict[str, object] | None = None) -> None:
        payload = self._build_payload(reason=reason, metadata=metadata)
        self._publish_payload_locally(payload)

        if self._supports_cross_worker():
            self._publish_payload_to_postgres(payload)

    def _build_payload(self, *, reason: str, metadata: dict[str, object] | None) -> str:
        payload_dict: dict[str, object] = {
            "event_id": uuid4().hex,
            "reason": reason,
            "emitted_at": datetime.now(timezone.utc).isoformat(),
        }
        if metadata:
            payload_dict.update({key: value for key, value in metadata.items() if value is not None})
        return json.dumps(payload_dict)

    def _publish_payload_locally(self, payload: str) -> None:
        event_id = self._extract_event_id(payload)
        if event_id is not None:
            self._remember_event_id(event_id)
        self._fan_out_payload(payload)

    def _publish_payload_to_postgres(self, payload: str) -> bool:
        try:
            with engine.begin() as connection:
                connection.execute(
                    text("SELECT pg_notify(:channel, :payload)"),
                    {
                        "channel": self._channel_name,
                        "payload": payload,
                    },
                )
            return True
        except Exception as exc:
            REALTIME_LOGGER.warning(
                json.dumps(
                    {
                        "channel": self._channel_name,
                        "error": str(exc)[:300],
                        "event": "realtime_broker_publish_failed",
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )
            return False

    def _listen_for_notifications(self) -> None:
        if not self._supports_cross_worker():
            return

        reconnect_delay = LISTENER_RECONNECT_INITIAL_SECONDS

        while not self._listener_stop_event.is_set():
            try:
                assert psycopg is not None
                assert sql is not None
                assert self._postgres_conninfo is not None
                assert self._channel_name is not None

                with psycopg.connect(self._postgres_conninfo, autocommit=True) as connection:
                    connection.execute(
                        sql.SQL("LISTEN {};").format(sql.Identifier(self._channel_name))
                    )
                    REALTIME_LOGGER.info(
                        json.dumps(
                            {
                                "channel": self._channel_name,
                                "event": "realtime_broker_listener_connected",
                            },
                            separators=(",", ":"),
                            sort_keys=True,
                        )
                    )
                    reconnect_delay = LISTENER_RECONNECT_INITIAL_SECONDS

                    while not self._listener_stop_event.is_set():
                        for notification in connection.notifies(timeout=1.0):
                            self._dispatch_remote_payload(notification.payload)
            except Exception as exc:
                if self._listener_stop_event.is_set():
                    break

                REALTIME_LOGGER.warning(
                    json.dumps(
                        {
                            "channel": self._channel_name,
                            "error": str(exc)[:300],
                            "event": "realtime_broker_listener_retrying",
                            "retry_in_seconds": reconnect_delay,
                        },
                        separators=(",", ":"),
                        sort_keys=True,
                    )
                )
                self._listener_stop_event.wait(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, LISTENER_RECONNECT_MAX_SECONDS)

    def _dispatch_remote_payload(self, payload: str) -> None:
        event_id = self._extract_event_id(payload)
        if event_id is not None:
            if self._has_seen_event_id(event_id):
                return
            self._remember_event_id(event_id)

        self._fan_out_payload(payload)

    def _fan_out_payload(self, payload: str) -> None:
        with self._subscribers_lock:
            subscribers = list(self._subscribers.items())

        for subscriber_id, subscriber in subscribers:
            if subscriber.loop is None or subscriber.loop.is_closed():
                self._enqueue_payload(subscriber_id, payload)
                continue

            try:
                subscriber.loop.call_soon_threadsafe(self._enqueue_payload, subscriber_id, payload)
            except RuntimeError:
                self._enqueue_payload(subscriber_id, payload)

    def _enqueue_payload(self, subscriber_id: str, payload: str) -> None:
        with self._subscribers_lock:
            subscriber = self._subscribers.get(subscriber_id)

        if subscriber is None:
            return

        queue = subscriber.queue
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass

        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            return

    def _extract_event_id(self, payload: str) -> str | None:
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return None
        event_id = parsed.get("event_id")
        if isinstance(event_id, str) and event_id:
            return event_id
        return None

    def _has_seen_event_id(self, event_id: str) -> bool:
        with self._recent_event_ids_lock:
            return event_id in self._recent_event_ids_set

    def _remember_event_id(self, event_id: str) -> None:
        with self._recent_event_ids_lock:
            if event_id in self._recent_event_ids_set:
                return

            self._recent_event_ids.append(event_id)
            self._recent_event_ids_set.add(event_id)

            while len(self._recent_event_ids) > RECENT_EVENT_ID_CAPACITY:
                oldest_event_id = self._recent_event_ids.popleft()
                self._recent_event_ids_set.discard(oldest_event_id)


admin_updates_broker = AdminUpdatesBroker("checking_admin_updates")
transport_updates_broker = AdminUpdatesBroker("checking_transport_updates")
web_check_updates_broker = AdminUpdatesBroker("checking_web_check_updates")


def start_realtime_brokers() -> None:
    admin_updates_broker.start()
    transport_updates_broker.start()
    web_check_updates_broker.start()


def stop_realtime_brokers() -> None:
    admin_updates_broker.stop()
    transport_updates_broker.stop()
    web_check_updates_broker.stop()


def notify_admin_data_changed(reason: str = "refresh", *, metadata: dict[str, object] | None = None) -> None:
    admin_updates_broker.publish(reason=reason, metadata=metadata)


def notify_transport_data_changed(reason: str = "refresh", *, metadata: dict[str, object] | None = None) -> None:
    transport_updates_broker.publish(reason=reason, metadata=metadata)


def notify_web_check_data_changed(reason: str = "refresh", *, metadata: dict[str, object] | None = None) -> None:
    web_check_updates_broker.publish(reason=reason, metadata=metadata)