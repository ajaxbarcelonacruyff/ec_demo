#!/usr/bin/env python3
"""GA4 ecommerce demo data generator - CLI entry point."""

import argparse
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from ga4_schema import event_to_jsonl
from user_journeys import create_user_pool, generate_day_events
from utils import NZ_TZ

# Probability that a purchase will be refunded (3-14 days later)
REFUND_RATE = 0.05


def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="GA4 ecommerce demo data generator")
    parser.add_argument("-c", "--config", default="config.yaml", help="Config file path")
    parser.add_argument("--start",  help="Override start date (YYYY-MM-DD)")
    parser.add_argument("--end",    help="Override end date (YYYY-MM-DD)")
    parser.add_argument("--users",  type=int, help="Override total users")
    parser.add_argument("--seed",   type=int, help="Random seed")
    args = parser.parse_args()

    config = load_config(args.config)

    start_str   = args.start or config["date_range"]["start"]
    end_str     = args.end   or config["date_range"]["end"]
    total_users = args.users or config["users"]["total"]
    seed        = args.seed  or config.get("settings", {}).get("seed", 42)

    random.seed(seed)

    start_date = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=NZ_TZ)
    end_date   = datetime.strptime(end_str,   "%Y-%m-%d").replace(tzinfo=NZ_TZ)

    output_dir = Path(config.get("output", {}).get("directory", "./output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    gen_config = {
        "daily_active_ratio":    config["users"]["daily_active_ratio"],
        "sessions_per_day_range":config["users"]["sessions_per_day_range"],
        "funnel":                config.get("funnel", {}),
        "stream_id":             config.get("settings", {}).get("stream_id", "1234567890"),
        "currency":              config.get("settings", {}).get("currency", "JPY"),
    }

    print(f"Creating {total_users} users...")
    users = create_user_pool(total_users, config["users"]["logged_in_ratio"])

    # pending_refunds: list of {purchase_info, refund_date}
    pending_refunds: list[dict] = []

    current_date = start_date
    total_events = 0

    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")

        # Collect refunds due today
        due_today   = [r for r in pending_refunds if r["refund_date"].date() <= current_date.date()]
        pending_refunds = [r for r in pending_refunds if r["refund_date"].date() > current_date.date()]

        events, new_purchases = generate_day_events(
            users,
            current_date,
            gen_config,
            due_refunds=[r["info"] for r in due_today],
        )

        # Schedule future refunds for a portion of today's purchases
        for p_info in new_purchases:
            if random.random() < REFUND_RATE:
                refund_date = current_date + timedelta(days=random.randint(3, 14))
                if refund_date <= end_date:
                    pending_refunds.append({"info": p_info, "refund_date": refund_date})

        filepath = output_dir / f"events_{date_str}.jsonl"
        with open(filepath, "w", encoding="utf-8") as f:
            for event in events:
                f.write(event_to_jsonl(event) + "\n")

        total_events += len(events)
        refund_note  = f" (+ {len(due_today)} refunds)" if due_today else ""
        print(f"  {date_str}: {len(events):,} events{refund_note} -> {filepath}")

        current_date += timedelta(days=1)

    print(f"\nDone! Total: {total_events:,} events over {(end_date - start_date).days + 1} days")


if __name__ == "__main__":
    main()
