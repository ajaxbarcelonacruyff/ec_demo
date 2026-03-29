"""Integration tests validating the 5 identity invariants on generated data.

Generates a small dataset and validates every event against the strict rules.
"""

import json
import random
from collections import defaultdict
from datetime import date, datetime

import pytest

from identity import (
    create_persons_and_devices,
    get_identity_config,
    pick_session_device,
)
from user_journeys import generate_day_events
from utils import NZ_TZ

_ECOMMERCE_EVENTS = {
    "add_to_cart", "remove_from_cart", "view_cart",
    "begin_checkout", "add_shipping_info", "add_payment_info", "purchase",
}


def _generate_test_data(
    total_users: int = 100,
    days: int = 3,
    seed: int = 42,
    identity_overrides: dict | None = None,
    noise_overrides: dict | None = None,
) -> tuple[list[dict], list[dict]]:
    """Generate test data and return (all_events, all_purchases)."""
    random.seed(seed)

    identity_cfg = {
        "early_login_rate": 0.60,
        "late_login_rate": 0.25,
        "mid_session_logout_rate": 0.05,
        "multi_device_ratio": 0.25,
        "max_devices_per_user": 3,
        "shared_device_ratio": 0.05,
        "max_users_per_device": 3,
    }
    if identity_overrides:
        identity_cfg.update(identity_overrides)

    noise_cfg = {
        "null_user_id_rate": 0.05,
        "ga4_event_loss_rate": 0.0,  # disable for invariant tests
        "bot_session_rate": 0.02,
        "payment_failure_rate": 0.08,
    }
    if noise_overrides:
        noise_cfg.update(noise_overrides)

    persons, devices_index = create_persons_and_devices(
        total_users, logged_in_ratio=0.5, sim_start=date(2025, 1, 1),
        identity_cfg=identity_cfg,
    )

    config = {
        "daily_active_ratio": 0.30,
        "sessions_per_day_range": [1, 3],
        "funnel": {
            "browse_to_view_item": 0.70,
            "view_item_to_add_to_cart": 0.30,
            "add_to_cart_to_remove": 0.10,
            "add_to_cart_to_checkout": 0.60,
            "checkout_to_purchase": 0.75,
            "promotion_probability": 0.15,
        },
        "stream_id": "1234567890",
        "currency": "JPY",
        "noise": noise_cfg,
        "identity": identity_cfg,
        "devices_index": devices_index,
        "day_of_week_weights": {},
        "campaigns": [],
    }

    start = datetime(2025, 1, 1, tzinfo=NZ_TZ)
    all_events = []
    all_purchases = []

    for d in range(days):
        target = start + __import__("datetime").timedelta(days=d)
        events, purchases = generate_day_events(persons, target, config)
        all_events.extend(events)
        all_purchases.extend(purchases)

    return all_events, all_purchases


def _group_by_session(events: list[dict]) -> dict[str, list[dict]]:
    """Group events by session key (user_pseudo_id + ga_session_id)."""
    sessions = defaultdict(list)
    for ev in events:
        upid = ev.get("user_pseudo_id", "")
        ga_sid = None
        for p in ev.get("event_params", []):
            if p.get("key") == "ga_session_id":
                ga_sid = p.get("value", {}).get("int_value")
                break
        if ga_sid is not None:
            key = f"{upid}.{ga_sid}"
            sessions[key].append(ev)
    return dict(sessions)


class TestInvariant1PurchaseHasUserId:

    def test_every_purchase_has_user_id(self):
        events, _ = _generate_test_data(total_users=100, days=5, seed=42)
        purchase_events = [e for e in events if e["event_name"] == "purchase"]
        for ev in purchase_events:
            assert ev.get("user_id") is not None, (
                f"Purchase event has user_id=None: txn={_get_param(ev, 'transaction_id')}"
            )


class TestInvariant2LoginBeforeEcommerce:

    def test_login_precedes_ecommerce(self):
        events, _ = _generate_test_data(total_users=100, days=5, seed=42)
        sessions = _group_by_session(events)
        for session_key, session_events in sessions.items():
            login_seen = False
            for ev in session_events:
                if ev["event_name"] in ("login", "sign_up"):
                    login_seen = True
                if ev["event_name"] in _ECOMMERCE_EVENTS:
                    assert login_seen, (
                        f"Ecommerce event '{ev['event_name']}' before login "
                        f"in session {session_key}"
                    )


class TestInvariant3UserIdFrozenAfterLogin:

    def test_same_user_id_from_login_to_logout(self):
        events, _ = _generate_test_data(total_users=100, days=5, seed=42)
        sessions = _group_by_session(events)
        for session_key, session_events in sessions.items():
            logged_in_uid = None
            for ev in session_events:
                if ev["event_name"] in ("login", "sign_up"):
                    logged_in_uid = ev.get("user_id")
                    assert logged_in_uid is not None
                elif ev["event_name"] == "logout":
                    logged_in_uid = None
                elif logged_in_uid is not None:
                    assert ev.get("user_id") == logged_in_uid, (
                        f"user_id changed from {logged_in_uid} to {ev.get('user_id')} "
                        f"in session {session_key} at event {ev['event_name']}"
                    )


class TestInvariant4NullAfterLogout:

    def test_user_id_null_after_logout(self):
        events, _ = _generate_test_data(total_users=200, days=5, seed=123)
        sessions = _group_by_session(events)
        for session_key, session_events in sessions.items():
            post_logout = False
            for ev in session_events:
                if ev["event_name"] == "logout":
                    post_logout = True
                elif ev["event_name"] in ("login", "sign_up"):
                    post_logout = False
                elif post_logout:
                    assert ev.get("user_id") is None, (
                        f"user_id={ev.get('user_id')} after logout "
                        f"in session {session_key} at event {ev['event_name']}"
                    )


class TestInvariant5NoNonNullToNonNull:

    def test_no_user_id_switch(self):
        events, _ = _generate_test_data(total_users=100, days=5, seed=42)
        sessions = _group_by_session(events)
        for session_key, session_events in sessions.items():
            prev_uid = None
            for ev in session_events:
                uid = ev.get("user_id")
                if prev_uid is not None and uid is not None and prev_uid != uid:
                    pytest.fail(
                        f"user_id changed from {prev_uid} to {uid} "
                        f"in session {session_key} at event {ev['event_name']}"
                    )
                prev_uid = uid


class TestNoiseModel:

    def test_noise_session_no_purchase_events_in_ga4(self):
        """With 100% noise, GA4 should have no purchase events."""
        events, purchases = _generate_test_data(
            total_users=50, days=3, seed=42,
            noise_overrides={"null_user_id_rate": 1.0},
        )
        purchase_events = [e for e in events if e["event_name"] == "purchase"]
        assert len(purchase_events) == 0

    def test_noise_session_no_login_events(self):
        """With 100% noise, GA4 should have no login events."""
        events, _ = _generate_test_data(
            total_users=50, days=3, seed=42,
            noise_overrides={"null_user_id_rate": 1.0},
        )
        login_events = [e for e in events if e["event_name"] in ("login", "sign_up")]
        assert len(login_events) == 0

    def test_noise_session_all_user_ids_null(self):
        """With 100% noise, all GA4 events should have user_id=NULL."""
        events, _ = _generate_test_data(
            total_users=50, days=3, seed=42,
            noise_overrides={"null_user_id_rate": 1.0},
        )
        for ev in events:
            assert ev.get("user_id") is None

    def test_noise_session_orders_still_recorded(self):
        """With 100% noise, orders should still be generated."""
        _, purchases = _generate_test_data(
            total_users=100, days=5, seed=42,
            noise_overrides={"null_user_id_rate": 1.0},
            identity_overrides={"early_login_rate": 0.90, "late_login_rate": 0.09},
        )
        # With high login rates and enough users/days, some orders should exist
        assert len(purchases) > 0, "Noise sessions should still generate orders"

    def test_noise_orders_have_real_user_id(self):
        """Noise session orders must have the person's real user_id."""
        _, purchases = _generate_test_data(
            total_users=100, days=5, seed=42,
            noise_overrides={"null_user_id_rate": 1.0},
            identity_overrides={"early_login_rate": 0.90, "late_login_rate": 0.09},
        )
        for p in purchases:
            assert p["user_id"] is not None, "Noise purchase must have real user_id"


class TestDataConsistency:

    def test_ga4_purchase_matches_orders(self):
        """Every GA4 purchase event must match its purchase_info."""
        events, purchases = _generate_test_data(total_users=100, days=5, seed=42)
        purchase_events = [e for e in events if e["event_name"] == "purchase"]

        # Build lookup by transaction_id
        p_info_by_txn = {p["transaction_id"]: p for p in purchases}

        for ev in purchase_events:
            txn_id = _get_param(ev, "transaction_id")
            assert txn_id is not None, "Purchase event must have transaction_id"
            assert txn_id in p_info_by_txn, (
                f"GA4 purchase txn={txn_id} has no matching order"
            )
            p_info = p_info_by_txn[txn_id]
            assert ev.get("user_id") == p_info["user_id"], (
                f"user_id mismatch: GA4={ev.get('user_id')}, order={p_info['user_id']}"
            )

    def test_orders_may_lack_ga4_purchase(self):
        """With noise, some orders should lack GA4 purchase events."""
        events, purchases = _generate_test_data(
            total_users=100, days=5, seed=42,
            noise_overrides={"null_user_id_rate": 0.50},
        )
        ga4_txn_ids = {
            _get_param(e, "transaction_id")
            for e in events
            if e["event_name"] == "purchase"
        }
        orders_without_ga4 = [p for p in purchases if p["transaction_id"] not in ga4_txn_ids]
        # With 50% noise, some orders should lack GA4 events
        if len(purchases) > 0:
            assert len(orders_without_ga4) > 0, (
                "With 50% noise, some orders should lack GA4 purchase events"
            )


class TestMultiDevice:

    def test_same_user_id_different_pseudo_ids(self):
        """Multi-device users should produce events with same user_id but different pseudo_ids."""
        events, _ = _generate_test_data(
            total_users=100, days=5, seed=42,
            identity_overrides={"multi_device_ratio": 1.0, "max_devices_per_user": 3},
        )
        # Group by user_id, collect distinct pseudo_ids
        user_pseudo_ids = defaultdict(set)
        for ev in events:
            uid = ev.get("user_id")
            upid = ev.get("user_pseudo_id")
            if uid:
                user_pseudo_ids[uid].add(upid)

        multi_device_users = {uid: pids for uid, pids in user_pseudo_ids.items() if len(pids) > 1}
        assert len(multi_device_users) > 0, "Should have users with multiple devices"


def _get_param(event: dict, key: str):
    """Extract a parameter value from event_params."""
    for p in event.get("event_params", []):
        if p.get("key") == key:
            v = p.get("value", {})
            return v.get("string_value") or v.get("float_value") or v.get("int_value")
    return None
