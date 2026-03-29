#!/usr/bin/env python3
"""GA4 ecommerce demo data generator - CLI entry point.

Outputs:
  output/events_YYYYMMDD.jsonl  - GA4 events (one file per day)
  output/customers.csv          - customer master  (customer_id == user_id)
  output/products.csv           - product master   (product_id == item_id)
  output/orders.csv             - order header     (order_id   == transaction_id)
  output/order_items.csv        - order line items (product_id == item_id)
"""

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from ga4_schema import event_to_jsonl
from identity import create_persons_and_devices, get_identity_config
from user_journeys import generate_day_events
from tables import (
    write_customers_csv,
    write_products_csv,
    write_orders_csv,
    write_order_items_csv,
)
from utils import NZ_TZ

# 5 % of purchases are refunded 3-14 days later
REFUND_RATE = 0.05


def load_config(config_path: str) -> dict:
    p = Path(config_path)
    if not p.exists():
        print(f"Error: config file not found: {config_path}", file=__import__('sys').stderr)
        raise SystemExit(1)
    if p.suffix not in (".yaml", ".yml"):
        print(f"Error: config file must be .yaml or .yml: {config_path}", file=__import__('sys').stderr)
        raise SystemExit(1)
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_config(cfg: dict) -> None:
    """Validate config values have correct types and ranges."""
    errors: list[str] = []

    # Required top-level sections
    for section in ("date_range", "users"):
        if section not in cfg:
            errors.append(f"Missing required section: '{section}'")
    if errors:
        _exit_with_errors(errors)

    # date_range
    dr = cfg["date_range"]
    for key in ("start", "end"):
        val = dr.get(key)
        if not isinstance(val, str):
            errors.append(f"date_range.{key} must be a string, got: {val!r}")
        else:
            try:
                datetime.strptime(val, "%Y-%m-%d")
            except ValueError:
                errors.append(f"date_range.{key} must be YYYY-MM-DD format, got: {val!r}")

    # users
    users = cfg["users"]
    total = users.get("total")
    if not isinstance(total, int) or total <= 0:
        errors.append(f"users.total must be a positive integer, got: {total!r}")

    for ratio_key in ("logged_in_ratio", "daily_active_ratio"):
        val = users.get(ratio_key)
        if not isinstance(val, (int, float)) or not (0.0 <= val <= 1.0):
            errors.append(f"users.{ratio_key} must be a float between 0 and 1, got: {val!r}")

    sess_range = users.get("sessions_per_day_range")
    if not (isinstance(sess_range, list) and len(sess_range) == 2
            and all(isinstance(x, int) and x > 0 for x in sess_range)):
        errors.append(
            f"users.sessions_per_day_range must be a list of two positive integers, got: {sess_range!r}"
        )
    elif sess_range[0] > sess_range[1]:
        errors.append(
            f"users.sessions_per_day_range[0] must be <= [1], got: {sess_range}"
        )

    # funnel rates (optional section, but validate if present)
    funnel = cfg.get("funnel", {})
    for fkey, fval in funnel.items():
        if not isinstance(fval, (int, float)) or not (0.0 <= fval <= 1.0):
            errors.append(f"funnel.{fkey} must be a float between 0 and 1, got: {fval!r}")

    # identity (optional section)
    identity = cfg.get("identity", {})
    for ratio_key in ("multi_device_ratio", "shared_device_ratio",
                       "early_login_rate", "late_login_rate", "mid_session_logout_rate"):
        val = identity.get(ratio_key)
        if val is not None and (not isinstance(val, (int, float)) or not (0.0 <= val <= 1.0)):
            errors.append(f"identity.{ratio_key} must be a float between 0 and 1, got: {val!r}")
    for int_key in ("max_devices_per_user", "max_users_per_device"):
        val = identity.get(int_key)
        if val is not None and (not isinstance(val, int) or val < 1):
            errors.append(f"identity.{int_key} must be a positive integer, got: {val!r}")
    early = identity.get("early_login_rate", 0.0)
    late = identity.get("late_login_rate", 0.0)
    if isinstance(early, (int, float)) and isinstance(late, (int, float)) and early + late > 1.0:
        errors.append(f"identity.early_login_rate + late_login_rate must be <= 1.0, got: {early + late}")

    # noise: validate ga4_event_loss_rate
    noise = cfg.get("noise", {})
    for noise_key in ("null_user_id_rate", "ga4_event_loss_rate", "bot_session_rate", "payment_failure_rate"):
        val = noise.get(noise_key)
        if val is not None and (not isinstance(val, (int, float)) or not (0.0 <= val <= 1.0)):
            errors.append(f"noise.{noise_key} must be a float between 0 and 1, got: {val!r}")

    if errors:
        _exit_with_errors(errors)


def _exit_with_errors(errors: list[str]) -> None:
    import sys
    print("Config validation errors:", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description="GA4 ecommerce demo data generator")
    parser.add_argument("-c", "--config", default="config.yaml")
    parser.add_argument("--start",  help="Override start date (YYYY-MM-DD)")
    parser.add_argument("--end",    help="Override end date (YYYY-MM-DD)")
    parser.add_argument("--users",  type=int, help="Override total users")
    parser.add_argument("--seed",   type=int, help="Random seed")
    args = parser.parse_args()

    config = load_config(args.config)
    validate_config(config)

    start_str   = args.start or config["date_range"]["start"]
    end_str     = args.end   or config["date_range"]["end"]
    total_users = args.users if args.users is not None else config["users"]["total"]
    seed        = args.seed  if args.seed  is not None else config.get("settings", {}).get("seed", 42)

    random.seed(seed)

    start_date = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=NZ_TZ)
    end_date   = datetime.strptime(end_str,   "%Y-%m-%d").replace(tzinfo=NZ_TZ)

    output_dir = Path(config.get("output", {}).get("directory", "./output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    # Normalize day_of_week_weights keys to int
    raw_dow = config.get("day_of_week_weights", {})
    dow_weights = {int(k): v for k, v in raw_dow.items()}

    gen_config = {
        "daily_active_ratio":     config["users"]["daily_active_ratio"],
        "sessions_per_day_range": config["users"]["sessions_per_day_range"],
        "funnel":                 config.get("funnel", {}),
        "stream_id":              config.get("settings", {}).get("stream_id", "1234567890"),
        "currency":               config.get("settings", {}).get("currency", "JPY"),
        "day_of_week_weights":    dow_weights,
        "campaigns":              config.get("campaigns", []),
        "noise":                  config.get("noise", {}),
    }

    # ------------------------------------------------------------------ identity
    identity_cfg = get_identity_config(config)
    gen_config["identity"] = identity_cfg

    print(f"Creating {total_users} persons and devices...")
    persons, devices_index = create_persons_and_devices(
        total_users,
        config["users"]["logged_in_ratio"],
        sim_start=start_date.date(),
        identity_cfg=identity_cfg,
    )
    gen_config["devices_index"] = devices_index

    multi_device_count = sum(1 for p in persons if len(p["device_ids"]) > 1)
    shared_device_count = sum(1 for d in devices_index.values() if d["shared_person_ids"])
    logged_in_count = sum(1 for p in persons if p["user_id"] is not None)
    print(f"  {logged_in_count} logged-in, {multi_device_count} multi-device, "
          f"{shared_device_count} shared devices, {len(devices_index)} total devices")

    # ------------------------------------------------------------------ events
    pending_refunds: list[dict] = []
    all_purchases:   list[dict] = []
    refunded_ids:    set[str]   = set()

    current_date = start_date
    total_events = 0

    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")

        due_today      = [r for r in pending_refunds if r["refund_date"].date() <= current_date.date()]
        pending_refunds = [r for r in pending_refunds if r["refund_date"].date() >  current_date.date()]

        events, new_purchases = generate_day_events(
            persons,
            current_date,
            gen_config,
            due_refunds=[r["info"] for r in due_today],
        )

        for r in due_today:
            refunded_ids.add(r["info"]["transaction_id"])

        all_purchases.extend(new_purchases)
        for p in new_purchases:
            if random.random() < REFUND_RATE:
                refund_date = current_date + timedelta(days=random.randint(3, 14))
                if refund_date <= end_date:
                    pending_refunds.append({"info": p, "refund_date": refund_date})

        filepath = output_dir / f"events_{date_str}.jsonl"
        with open(filepath, "w", encoding="utf-8") as f:
            for event in events:
                f.write(event_to_jsonl(event) + "\n")

        total_events += len(events)
        refund_note   = f" (+ {len(due_today)} refunds)" if due_today else ""
        print(f"  {date_str}: {len(events):,} events{refund_note} -> {filepath.name}")

        current_date += timedelta(days=1)

    # ------------------------------------------------------------------ tables
    print("\nWriting relational tables...")

    n_customers  = write_customers_csv(persons, output_dir / "customers.csv")
    n_products   = write_products_csv(output_dir / "products.csv")
    n_orders     = write_orders_csv(all_purchases, refunded_ids, output_dir / "orders.csv")
    n_order_items= write_order_items_csv(all_purchases, output_dir / "order_items.csv")

    days = (end_date - start_date).days + 1
    print(f"\n{'='*55}")
    print(f"  events (JSONL) : {total_events:>8,} rows  ({days} files)")
    print(f"  customers      : {n_customers:>8,} rows  -> customers.csv")
    print(f"  products       : {n_products:>8,} rows  -> products.csv")
    print(f"  orders         : {n_orders:>8,} rows  -> orders.csv  ({len(refunded_ids)} refunded)")
    print(f"  order_items    : {n_order_items:>8,} rows  -> order_items.csv")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
