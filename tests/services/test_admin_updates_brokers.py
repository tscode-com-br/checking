"""Tests for realtime broker infrastructure — Task B1."""
import asyncio
import json

import pytest

from sistema.app.services.admin_updates import (
    AdminUpdatesBroker,
    admin_updates_broker,
    notify_web_check_data_changed,
    start_realtime_brokers,
    stop_realtime_brokers,
    transport_updates_broker,
    web_check_updates_broker,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sync_publish_and_drain(broker: AdminUpdatesBroker, reason: str = "test", **meta: object) -> list[dict]:
    """Subscribe, publish, drain the in-memory queue synchronously."""
    loop = asyncio.new_event_loop()
    try:
        sub_id, queue = broker.subscribe()
        try:
            broker.publish(reason=reason, metadata=meta if meta else None)
            # Drain up to 10 items without blocking
            results = []
            while not queue.empty():
                raw = queue.get_nowait()
                results.append(json.loads(raw))
            return results
        finally:
            broker.unsubscribe(sub_id)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# test_web_check_broker_publish_fanout
# ---------------------------------------------------------------------------


def test_web_check_broker_publish_fanout():
    """subscribe → publish → payload is delivered to the subscriber queue."""
    loop = asyncio.new_event_loop()
    try:
        sub_id, queue = web_check_updates_broker.subscribe()
        try:
            notify_web_check_data_changed("accident_opened", metadata={"accident_id": 42})

            assert not queue.empty(), "Queue should have at least one item after publish"
            raw = queue.get_nowait()
            payload = json.loads(raw)

            assert payload["reason"] == "accident_opened"
            assert payload["accident_id"] == 42
            assert "event_id" in payload
            assert "emitted_at" in payload
        finally:
            web_check_updates_broker.unsubscribe(sub_id)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# test_web_check_broker_isolated_from_admin
# ---------------------------------------------------------------------------


def test_web_check_broker_isolated_from_admin():
    """Publishing to admin_updates_broker must NOT reach web_check_updates_broker."""
    loop = asyncio.new_event_loop()
    try:
        # Subscribe on web_check broker BEFORE publishing to admin broker
        web_sub_id, web_queue = web_check_updates_broker.subscribe()
        admin_sub_id, admin_queue = admin_updates_broker.subscribe()
        try:
            # Publish only to admin broker
            admin_updates_broker.publish(reason="admin_only_event")

            # Admin subscriber should receive it
            assert not admin_queue.empty(), "Admin subscriber should receive the event"
            admin_payload = json.loads(admin_queue.get_nowait())
            assert admin_payload["reason"] == "admin_only_event"

            # Web subscriber must NOT receive it (different channel / broker instance)
            assert web_queue.empty(), (
                "web_check_updates_broker subscriber should NOT receive admin broker events"
            )
        finally:
            web_check_updates_broker.unsubscribe(web_sub_id)
            admin_updates_broker.unsubscribe(admin_sub_id)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# test_start_stop_all_brokers
# ---------------------------------------------------------------------------


def test_start_stop_all_brokers():
    """start_realtime_brokers() and stop_realtime_brokers() complete without error.

    In SQLite dev mode the brokers skip Postgres LISTEN/NOTIFY, so start/stop
    are no-ops — but must not raise.
    """
    # Should not raise regardless of DB backend
    start_realtime_brokers()
    stop_realtime_brokers()


# ---------------------------------------------------------------------------
# Extra: verify the three broker objects are distinct instances
# ---------------------------------------------------------------------------


def test_three_brokers_are_distinct_instances():
    assert admin_updates_broker is not transport_updates_broker
    assert admin_updates_broker is not web_check_updates_broker
    assert transport_updates_broker is not web_check_updates_broker


def test_web_check_broker_channel_name():
    """Channel name is set correctly (accessible via internal attribute for introspection)."""
    assert web_check_updates_broker._channel_name == "checking_web_check_updates"
