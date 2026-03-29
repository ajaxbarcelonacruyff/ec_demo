"""Identity model: Person-Device many-to-many, SessionIdentity state machine.

Separates "person" (a real human with optional user_id) from "device"
(a browser/app with user_pseudo_id). Supports multi-device users,
shared devices, and login-gated session identity.
"""

import random
from dataclasses import dataclass, field
from datetime import datetime

from utils import generate_user_pseudo_id, generate_user_id, generate_transaction_id
from device_geo import pick_device, pick_geo
from traffic_sources import pick_traffic_source
from product_catalog import CATEGORIES
from tables import generate_customer_attrs


# ---------------------------------------------------------------------------
# Backward-compatible defaults (approximate current code behavior)
# ---------------------------------------------------------------------------

_IDENTITY_DEFAULTS = {
    "early_login_rate": 0.55,
    "late_login_rate": 0.0,
    "mid_session_logout_rate": 0.0,
    "multi_device_ratio": 0.0,
    "max_devices_per_user": 1,
    "shared_device_ratio": 0.0,
    "max_users_per_device": 1,
}


def get_identity_config(config: dict) -> dict:
    """Extract identity config from top-level config, applying defaults."""
    section = config.get("identity", None)
    if section is None:
        return dict(_IDENTITY_DEFAULTS)
    result = dict(_IDENTITY_DEFAULTS)
    result.update(section)
    return result


# ---------------------------------------------------------------------------
# SessionIdentity — login/logout state machine
# ---------------------------------------------------------------------------

@dataclass
class SessionIdentity:
    """Tracks login state within a single session.

    ALL sessions start with user_id=None.
    Only login() can set user_id.
    Only logout() can clear user_id.
    user_id never changes from non-None A to non-None B.
    """
    person_user_id: str | None
    _current_user_id: str | None = field(default=None, init=False, repr=False)
    _logged_in: bool = field(default=False, init=False, repr=False)

    @property
    def current_user_id(self) -> str | None:
        return self._current_user_id

    @property
    def is_logged_in(self) -> bool:
        return self._logged_in

    def login(self) -> None:
        if self.person_user_id is None:
            raise ValueError("Guest persons cannot login")
        if self._logged_in:
            raise ValueError("Already logged in")
        self._current_user_id = self.person_user_id
        self._logged_in = True

    def logout(self) -> None:
        if not self._logged_in:
            raise ValueError("Not logged in")
        self._current_user_id = None
        self._logged_in = False


# ---------------------------------------------------------------------------
# Person-Device graph construction
# ---------------------------------------------------------------------------

def create_persons_and_devices(
    total_users: int,
    logged_in_ratio: float,
    sim_start: "datetime | None",
    identity_cfg: dict,
) -> tuple[list[dict], dict[str, dict]]:
    """Build persons and devices with many-to-many relationships.

    Returns (persons, devices_index) where devices_index maps
    user_pseudo_id -> device dict. All references are by object identity.
    """
    multi_device_ratio = identity_cfg.get("multi_device_ratio", 0.0)
    max_devices = identity_cfg.get("max_devices_per_user", 1)
    shared_device_ratio = identity_cfg.get("shared_device_ratio", 0.0)
    max_shared_users = identity_cfg.get("max_users_per_device", 1)

    persons: list[dict] = []
    devices_index: dict[str, dict] = {}

    # Phase 1: Create persons with primary devices
    for i in range(total_users):
        person_id = f"P{i + 1:06d}"
        user_id = generate_user_id() if random.random() < logged_in_ratio else None

        upid = generate_user_pseudo_id()
        device = {
            "user_pseudo_id": upid,
            "device_profile": pick_device(),
            "geo_profile": pick_geo(),
            "first_touch_source": pick_traffic_source(),
            "owner_person_id": person_id,
            "shared_person_ids": [],
        }
        devices_index[upid] = device

        person = {
            "person_id": person_id,
            "user_id": user_id,
            "device_ids": [upid],
            "session_count": 0,
            "purchase_propensity": random.betavariate(2, 5),
            "affinity_categories": random.sample(
                CATEGORIES,
                min(random.choices([1, 2, 3], weights=[40, 40, 20], k=1)[0], len(CATEGORIES)),
            ),
        }
        if user_id:
            person.update(generate_customer_attrs(user_id, sim_start))
        persons.append(person)

    # Phase 2: Multi-device assignment
    if multi_device_ratio > 0 and max_devices > 1:
        logged_in_persons = [p for p in persons if p["user_id"] is not None]
        multi_count = int(len(logged_in_persons) * multi_device_ratio)
        if multi_count > 0:
            selected = random.sample(logged_in_persons, min(multi_count, len(logged_in_persons)))
            for person in selected:
                extra_count = random.randint(1, max_devices - 1)
                for _ in range(extra_count):
                    upid = generate_user_pseudo_id()
                    device = {
                        "user_pseudo_id": upid,
                        "device_profile": pick_device(),
                        "geo_profile": pick_geo(),
                        "first_touch_source": pick_traffic_source(),
                        "owner_person_id": person["person_id"],
                        "shared_person_ids": [],
                    }
                    devices_index[upid] = device
                    person["device_ids"].append(upid)

    # Phase 3: Shared device assignment
    if shared_device_ratio > 0 and max_shared_users > 1:
        all_device_ids = list(devices_index.keys())
        shared_count = int(len(all_device_ids) * shared_device_ratio)
        if shared_count > 0:
            shared_targets = random.sample(all_device_ids, min(shared_count, len(all_device_ids)))
            logged_in_persons = [p for p in persons if p["user_id"] is not None]
            person_by_id = {p["person_id"]: p for p in persons}

            for did in shared_targets:
                device = devices_index[did]
                owner_id = device["owner_person_id"]
                candidates = [p for p in logged_in_persons if p["person_id"] != owner_id]
                if not candidates:
                    continue
                n_additional = random.randint(1, min(2, max_shared_users - 1))
                additional = random.sample(candidates, min(n_additional, len(candidates)))
                for p in additional:
                    device["shared_person_ids"].append(p["person_id"])
                    if did not in p["device_ids"]:
                        p["device_ids"].append(did)

    return persons, devices_index


# ---------------------------------------------------------------------------
# Device selection
# ---------------------------------------------------------------------------

def pick_session_device(person: dict, devices_index: dict[str, dict]) -> dict:
    """Pick a device for this session (70% primary, 30% secondary)."""
    device_ids = person["device_ids"]
    if len(device_ids) == 1:
        return devices_index[device_ids[0]]
    n_secondary = len(device_ids) - 1
    weights = [0.70] + [0.30 / n_secondary] * n_secondary
    chosen_id = random.choices(device_ids, weights=weights, k=1)[0]
    return devices_index[chosen_id]


# ---------------------------------------------------------------------------
# Purchase info — single source of truth
# ---------------------------------------------------------------------------

_TAX_RATE = 0.10


def build_purchase_info(
    *,
    person: dict,
    device: dict,
    cart_items: list[dict],
    cart_subtotal: float,
    order_coupon: str | None,
    discount_total: float,
    ship_fee: float,
    shipping_tier: str,
    payment_type: str,
    currency: str,
    purchase_datetime: datetime,
    session_id: int,
    session_number: int,
) -> dict:
    """Build the single-source-of-truth purchase_info dict.

    Used to derive BOTH GA4 purchase event params AND orders/order_items rows.
    user_id is ALWAYS the person's real user_id (for orders table integrity).
    """
    tax = round((cart_subtotal - discount_total + ship_fee) * _TAX_RATE)
    total = cart_subtotal - discount_total + ship_fee + tax

    return {
        "user_pseudo_id": device["user_pseudo_id"],
        "user_id": person["user_id"],
        "transaction_id": generate_transaction_id(),
        "order_datetime": purchase_datetime,
        "subtotal": cart_subtotal,
        "coupon_code": order_coupon,
        "discount_amount": discount_total,
        "shipping_fee": ship_fee,
        "shipping_tier": shipping_tier,
        "tax_amount": tax,
        "total_amount": total,
        "payment_type": payment_type,
        "currency": currency,
        "items": cart_items,
        "session_id": session_id,
        "session_number": session_number,
    }
