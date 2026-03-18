#!/usr/bin/env python3
"""GA4 ecommerce demo data generator - CLI entry point."""

import argparse
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from ga4_schema import event_to_jsonl
from user_journeys import create_user_pool, generate_day_events
from utils import NZ_TZ


def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="GA4 ecommerce demo data generator")
    parser.add_argument("-c", "--config", default="config.yaml", help="Config file path")
    parser.add_argument("--start", help="Override start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="Override end date (YYYY-MM-DD)")
    parser.add_argument("--users", type=int, help="Override total users")
    parser.add_argument("--seed", type=int, help="Random seed")
    args = parser.parse_args()

    config = load_config(args.config)

    # Apply overrides
    start_str = args.start or config["date_range"]["start"]
    end_str = args.end or config["date_range"]["end"]
    total_users = args.users or config["users"]["total"]
    seed = args.seed or config.get("settings", {}).get("seed", 42)

    random.seed(seed)

    start_date = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=NZ_TZ)
    end_date = datetime.strptime(end_str, "%Y-%m-%d").replace(tzinfo=NZ_TZ)

    output_dir = Path(config.get("output", {}).get("directory", "./output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build generation config
    gen_config = {
        "daily_active_ratio": config["users"]["daily_active_ratio"],
        "sessions_per_day_range": config["users"]["sessions_per_day_range"],
        "funnel": config.get("funnel", {}),
        "stream_id": config.get("settings", {}).get("stream_id", "1234567890"),
        "currency": config.get("settings", {}).get("currency", "JPY"),
    }

    # Create user pool
    print(f"Creating {total_users} users...")
    users = create_user_pool(total_users, config["users"]["logged_in_ratio"])

    # Generate day by day
    current_date = start_date
    total_events = 0
    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        events = generate_day_events(users, current_date, gen_config)

        filename = f"events_{date_str}.jsonl"
        filepath = output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            for event in events:
                f.write(event_to_jsonl(event) + "\n")

        total_events += len(events)
        print(f"  {date_str}: {len(events):,} events -> {filepath}")
        current_date += timedelta(days=1)

    print(f"\nDone! Total: {total_events:,} events, {(end_date - start_date).days + 1} days")


if __name__ == "__main__":
    main()
