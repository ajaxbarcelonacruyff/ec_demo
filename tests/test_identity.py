"""Unit tests for identity module — Person/Device model, SessionIdentity, build_purchase_info.

TDD: These tests are written BEFORE the implementation.
"""

import random
from datetime import date, datetime

import pytest

_SIM_START = date(2025, 1, 1)


# ---------------------------------------------------------------------------
# SessionIdentity tests
# ---------------------------------------------------------------------------

class TestSessionIdentity:
    """Tests for the login/logout state machine."""

    def test_starts_with_null_user_id(self):
        from identity import SessionIdentity
        sid = SessionIdentity(person_user_id="U123456")
        assert sid.current_user_id is None
        assert sid.is_logged_in is False

    def test_login_sets_user_id(self):
        from identity import SessionIdentity
        sid = SessionIdentity(person_user_id="U123456")
        sid.login()
        assert sid.current_user_id == "U123456"
        assert sid.is_logged_in is True

    def test_logout_clears_user_id(self):
        from identity import SessionIdentity
        sid = SessionIdentity(person_user_id="U123456")
        sid.login()
        sid.logout()
        assert sid.current_user_id is None
        assert sid.is_logged_in is False

    def test_double_login_raises(self):
        from identity import SessionIdentity
        sid = SessionIdentity(person_user_id="U123456")
        sid.login()
        with pytest.raises(ValueError, match="Already logged in"):
            sid.login()

    def test_logout_without_login_raises(self):
        from identity import SessionIdentity
        sid = SessionIdentity(person_user_id="U123456")
        with pytest.raises(ValueError, match="Not logged in"):
            sid.logout()

    def test_guest_login_raises(self):
        from identity import SessionIdentity
        sid = SessionIdentity(person_user_id=None)
        with pytest.raises(ValueError, match="Guest persons cannot login"):
            sid.login()

    def test_login_logout_login_allowed(self):
        """Re-login after logout should work (force re-login at checkout)."""
        from identity import SessionIdentity
        sid = SessionIdentity(person_user_id="U123456")
        sid.login()
        sid.logout()
        sid.login()  # should not raise
        assert sid.current_user_id == "U123456"
        assert sid.is_logged_in is True

    def test_guest_always_anonymous(self):
        from identity import SessionIdentity
        sid = SessionIdentity(person_user_id=None)
        assert sid.current_user_id is None
        assert sid.is_logged_in is False


# ---------------------------------------------------------------------------
# create_persons_and_devices tests
# ---------------------------------------------------------------------------

class TestCreatePersonsAndDevices:
    """Tests for person/device graph construction."""

    def test_default_config_produces_1_to_1_mapping(self):
        from identity import create_persons_and_devices
        random.seed(42)
        persons, devices_index = create_persons_and_devices(
            total_users=50, logged_in_ratio=0.3, sim_start=_SIM_START,
            identity_cfg={},
        )
        assert len(persons) == 50
        for p in persons:
            assert len(p["device_ids"]) == 1
        # Each device has no shared users
        for d in devices_index.values():
            assert d["shared_person_ids"] == []

    def test_person_count_matches_total(self):
        from identity import create_persons_and_devices
        random.seed(42)
        persons, _ = create_persons_and_devices(
            total_users=100, logged_in_ratio=0.5, sim_start=_SIM_START,
            identity_cfg={},
        )
        assert len(persons) == 100

    def test_logged_in_ratio(self):
        from identity import create_persons_and_devices
        random.seed(42)
        persons, _ = create_persons_and_devices(
            total_users=200, logged_in_ratio=0.5, sim_start=_SIM_START,
            identity_cfg={},
        )
        with_uid = [p for p in persons if p["user_id"] is not None]
        # Allow 10% tolerance
        assert 80 <= len(with_uid) <= 120

    def test_multi_device_ratio(self):
        from identity import create_persons_and_devices
        random.seed(42)
        persons, devices_index = create_persons_and_devices(
            total_users=200, logged_in_ratio=0.5, sim_start=_SIM_START,
            identity_cfg={
                "multi_device_ratio": 1.0,
                "max_devices_per_user": 3,
            },
        )
        logged_in = [p for p in persons if p["user_id"] is not None]
        multi = [p for p in logged_in if len(p["device_ids"]) >= 2]
        # All logged-in users should have 2+ devices
        assert len(multi) == len(logged_in)

    def test_shared_device_ratio(self):
        from identity import create_persons_and_devices
        random.seed(42)
        persons, devices_index = create_persons_and_devices(
            total_users=200, logged_in_ratio=0.5, sim_start=_SIM_START,
            identity_cfg={
                "shared_device_ratio": 1.0,
                "max_users_per_device": 3,
            },
        )
        shared = [d for d in devices_index.values() if len(d["shared_person_ids"]) > 0]
        # Most devices should be shared (some might not have eligible candidates)
        assert len(shared) > len(devices_index) * 0.5

    def test_devices_index_object_identity(self):
        """All device references should point to the same object."""
        from identity import create_persons_and_devices
        random.seed(42)
        persons, devices_index = create_persons_and_devices(
            total_users=50, logged_in_ratio=0.5, sim_start=_SIM_START,
            identity_cfg={"shared_device_ratio": 0.5, "max_users_per_device": 2},
        )
        # For each person, their device_ids should refer to existing devices in the index
        for p in persons:
            for did in p["device_ids"]:
                assert did in devices_index

    def test_guest_persons_have_no_user_id(self):
        from identity import create_persons_and_devices
        random.seed(42)
        persons, _ = create_persons_and_devices(
            total_users=100, logged_in_ratio=0.0, sim_start=_SIM_START,
            identity_cfg={},
        )
        for p in persons:
            assert p["user_id"] is None

    def test_session_count_initialized_to_zero(self):
        from identity import create_persons_and_devices
        random.seed(42)
        persons, _ = create_persons_and_devices(
            total_users=10, logged_in_ratio=0.5, sim_start=_SIM_START,
            identity_cfg={},
        )
        for p in persons:
            assert p["session_count"] == 0

    def test_person_has_required_fields(self):
        from identity import create_persons_and_devices
        random.seed(42)
        persons, _ = create_persons_and_devices(
            total_users=10, logged_in_ratio=0.5, sim_start=_SIM_START,
            identity_cfg={},
        )
        required = {"person_id", "user_id", "device_ids", "session_count",
                     "purchase_propensity", "affinity_categories"}
        for p in persons:
            assert required.issubset(p.keys()), f"Missing keys: {required - p.keys()}"

    def test_device_has_required_fields(self):
        from identity import create_persons_and_devices
        random.seed(42)
        _, devices_index = create_persons_and_devices(
            total_users=10, logged_in_ratio=0.5, sim_start=_SIM_START,
            identity_cfg={},
        )
        required = {"user_pseudo_id", "device_profile", "geo_profile",
                     "first_touch_source", "owner_person_id", "shared_person_ids"}
        for d in devices_index.values():
            assert required.issubset(d.keys()), f"Missing keys: {required - d.keys()}"

    def test_logged_in_person_has_customer_attrs(self):
        from identity import create_persons_and_devices
        random.seed(42)
        persons, _ = create_persons_and_devices(
            total_users=50, logged_in_ratio=1.0,
            sim_start=datetime(2025, 1, 1).date(),
            identity_cfg={},
        )
        for p in persons:
            assert p.get("customer_id") is not None
            assert p.get("name") is not None
            assert p.get("email") is not None

    def test_bidirectional_shared_device_refs(self):
        """Shared device person_ids and person device_ids must be consistent."""
        from identity import create_persons_and_devices
        random.seed(42)
        persons, devices_index = create_persons_and_devices(
            total_users=100, logged_in_ratio=0.5, sim_start=_SIM_START,
            identity_cfg={"shared_device_ratio": 0.5, "max_users_per_device": 3},
        )
        person_by_id = {p["person_id"]: p for p in persons}
        for did, dev in devices_index.items():
            for shared_pid in dev["shared_person_ids"]:
                assert shared_pid in person_by_id
                assert did in person_by_id[shared_pid]["device_ids"]


# ---------------------------------------------------------------------------
# pick_session_device tests
# ---------------------------------------------------------------------------

class TestPickSessionDevice:

    def test_single_device_always_returned(self):
        from identity import create_persons_and_devices, pick_session_device
        random.seed(42)
        persons, devices_index = create_persons_and_devices(
            total_users=10, logged_in_ratio=0.5, sim_start=_SIM_START,
            identity_cfg={},
        )
        p = persons[0]
        for _ in range(50):
            dev = pick_session_device(p, devices_index)
            assert dev["user_pseudo_id"] == p["device_ids"][0]

    def test_multi_device_primary_bias(self):
        """Primary device should be selected ~70% of the time."""
        from identity import create_persons_and_devices, pick_session_device
        random.seed(42)
        persons, devices_index = create_persons_and_devices(
            total_users=50, logged_in_ratio=1.0, sim_start=_SIM_START,
            identity_cfg={"multi_device_ratio": 1.0, "max_devices_per_user": 3},
        )
        # Find a person with 2+ devices
        multi_person = next(p for p in persons if len(p["device_ids"]) >= 2)
        primary_id = multi_person["device_ids"][0]
        primary_count = 0
        trials = 1000
        for _ in range(trials):
            dev = pick_session_device(multi_person, devices_index)
            if dev["user_pseudo_id"] == primary_id:
                primary_count += 1
        # Should be roughly 70% (allow 60-80% range)
        ratio = primary_count / trials
        assert 0.60 <= ratio <= 0.80, f"Primary ratio={ratio:.2f}, expected ~0.70"

    def test_returns_device_from_index(self):
        from identity import create_persons_and_devices, pick_session_device
        random.seed(42)
        persons, devices_index = create_persons_and_devices(
            total_users=10, logged_in_ratio=0.5, sim_start=_SIM_START,
            identity_cfg={},
        )
        for p in persons:
            dev = pick_session_device(p, devices_index)
            assert dev["user_pseudo_id"] in devices_index


# ---------------------------------------------------------------------------
# get_identity_config tests
# ---------------------------------------------------------------------------

class TestGetIdentityConfig:

    def test_absent_section_returns_backward_compat_defaults(self):
        from identity import get_identity_config
        cfg = get_identity_config({})
        assert cfg["early_login_rate"] == 0.55
        assert cfg["late_login_rate"] == 0.0
        assert cfg["mid_session_logout_rate"] == 0.0
        assert cfg["multi_device_ratio"] == 0.0
        assert cfg["shared_device_ratio"] == 0.0

    def test_explicit_values_preserved(self):
        from identity import get_identity_config
        cfg = get_identity_config({
            "identity": {
                "early_login_rate": 0.60,
                "late_login_rate": 0.25,
                "mid_session_logout_rate": 0.05,
            }
        })
        assert cfg["early_login_rate"] == 0.60
        assert cfg["late_login_rate"] == 0.25
        assert cfg["mid_session_logout_rate"] == 0.05

    def test_partial_section_fills_defaults(self):
        from identity import get_identity_config
        cfg = get_identity_config({"identity": {"early_login_rate": 0.80}})
        assert cfg["early_login_rate"] == 0.80
        assert cfg["late_login_rate"] == 0.0  # default


# ---------------------------------------------------------------------------
# build_purchase_info tests
# ---------------------------------------------------------------------------

class TestBuildPurchaseInfo:

    def test_user_id_always_real(self):
        """purchase_info must use person's real user_id, not session state."""
        from identity import build_purchase_info
        info = build_purchase_info(
            person={"user_id": "U999"},
            device={"user_pseudo_id": "123.456"},
            cart_items=[{"item_id": "SKU001", "price": 1000, "quantity": 1}],
            cart_subtotal=1000,
            order_coupon=None,
            discount_total=0,
            ship_fee=550,
            shipping_tier="standard",
            payment_type="credit_card",
            currency="JPY",
            purchase_datetime=datetime(2025, 1, 15, 12, 0, 0),
            session_id=12345,
            session_number=1,
        )
        assert info["user_id"] == "U999"

    def test_all_required_fields_present(self):
        from identity import build_purchase_info
        info = build_purchase_info(
            person={"user_id": "U001"},
            device={"user_pseudo_id": "111.222"},
            cart_items=[{"item_id": "SKU001", "price": 2000, "quantity": 2}],
            cart_subtotal=4000,
            order_coupon="SAVE10",
            discount_total=400,
            ship_fee=0,
            shipping_tier="standard",
            payment_type="credit_card",
            currency="JPY",
            purchase_datetime=datetime(2025, 1, 15, 12, 0, 0),
            session_id=99999,
            session_number=3,
        )
        required = {
            "user_pseudo_id", "user_id", "transaction_id",
            "order_datetime", "subtotal", "coupon_code",
            "discount_amount", "shipping_fee", "shipping_tier",
            "tax_amount", "total_amount", "payment_type",
            "currency", "items", "session_id", "session_number",
        }
        assert required.issubset(info.keys())

    def test_tax_calculation(self):
        from identity import build_purchase_info
        info = build_purchase_info(
            person={"user_id": "U001"},
            device={"user_pseudo_id": "111.222"},
            cart_items=[{"item_id": "SKU001", "price": 10000, "quantity": 1}],
            cart_subtotal=10000,
            order_coupon=None,
            discount_total=0,
            ship_fee=550,
            shipping_tier="standard",
            payment_type="credit_card",
            currency="JPY",
            purchase_datetime=datetime(2025, 1, 15, 12, 0, 0),
            session_id=1,
            session_number=1,
        )
        # tax = round((10000 - 0 + 550) * 0.10) = 1055
        assert info["tax_amount"] == 1055
        # total = 10000 - 0 + 550 + 1055 = 11605
        assert info["total_amount"] == 11605
