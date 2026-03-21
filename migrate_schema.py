"""
Migrate existing JSONL event data to match the latest GA4 BigQuery export schema.
Adds missing fields with realistic default/null values, then uploads to BigQuery.
"""
import json
import glob
import os
import random


def migrate_event(event: dict) -> dict:
    """Add missing GA4 schema fields to an existing event dict."""

    # --- Top-level fields ---
    # event_value_in_usd: for purchase events, convert JPY to USD
    value_param = None
    for p in event.get("event_params", []):
        if p["key"] == "value":
            v = p.get("value", {})
            value_param = v.get("float_value") or v.get("int_value")
            break
    if value_param is not None:
        event["event_value_in_usd"] = round(value_param / 150.0, 6)

    # event_bundle_sequence_id
    event["event_bundle_sequence_id"] = event.get("batch_ordering_id", 0)

    # event_server_timestamp_offset (typically small, microseconds)
    event["event_server_timestamp_offset"] = random.randint(50000, 500000)

    # is_active_user
    event["is_active_user"] = True

    # --- event_params.value.double_value ---
    # GA4 uses double_value for high-precision floats; add alongside float_value
    for p in event.get("event_params", []):
        v = p.get("value", {})
        if "float_value" in v:
            v["double_value"] = v["float_value"]

    # --- user_properties: add double_value + set_timestamp_micros ---
    for up in event.get("user_properties", []):
        v = up.get("value", {})
        if "float_value" in v:
            v["double_value"] = v["float_value"]
        up["set_timestamp_micros"] = event.get(
            "user_first_touch_timestamp", event["event_timestamp"]
        )

    # --- device.advertising_id ---
    device = event.get("device")
    if device:
        device["advertising_id"] = None

    # --- geo.metro ---
    geo = event.get("geo")
    if geo:
        metro_map = {
            "Tokyo": "Tokyo",
            "Osaka": "Osaka",
            "Nagoya": "Nagoya",
            "Fukuoka": "Fukuoka",
            "Sapporo": "Sapporo",
            "Sendai": "Sendai",
            "Hiroshima": "Hiroshima",
            "Kyoto": "Kyoto",
            "Kobe": "Kobe",
            "Yokohama": "Tokyo",
        }
        city = geo.get("city", "")
        geo["metro"] = metro_map.get(city, "(not set)")

    # --- collected_traffic_source: add new fields ---
    cts = event.get("collected_traffic_source")
    if cts:
        cts.setdefault("manual_term", None)
        cts.setdefault("dclid", None)
        cts.setdefault("srsltid", None)
        cts.setdefault("manual_source_platform", None)
        cts.setdefault("manual_creative_format", None)
        cts.setdefault("manual_marketing_tactic", None)

    # --- session_traffic_source_last_click: expand manual_campaign + add ad platform records ---
    stslc = event.get("session_traffic_source_last_click")
    if stslc:
        mc = stslc.get("manual_campaign")
        if mc:
            mc.setdefault("term", None)
            mc.setdefault("source_platform", None)
            mc.setdefault("creative_format", None)
            mc.setdefault("marketing_tactic", None)
        # Ad platform campaign records (null for organic/direct traffic)
        stslc.setdefault("cross_channel_campaign", None)
        stslc.setdefault("sa360_campaign", None)
        stslc.setdefault("cm360_campaign", None)
        stslc.setdefault("dv360_campaign", None)

    # --- items: add new fields ---
    items = event.get("items")
    if items:
        for item in items:
            item.setdefault("item_variant", None)
            item.setdefault("item_category4", None)
            item.setdefault("item_category5", None)
            price = item.get("price")
            if price is not None:
                item["price_in_usd"] = round(price / 150.0, 6)
            else:
                item["price_in_usd"] = None
            # item_revenue = price * quantity for purchase events
            qty = item.get("quantity", 1)
            if event["event_name"] == "purchase" and price is not None:
                revenue = price * qty
                discount = item.get("discount", 0) or 0
                item["item_revenue"] = revenue - discount
                item["item_revenue_in_usd"] = round((revenue - discount) / 150.0, 6)
            else:
                item["item_revenue"] = None
                item["item_revenue_in_usd"] = None
            item.setdefault("location_id", None)
            item.setdefault("item_params", [])

    # --- ecommerce: add new fields ---
    ecom = event.get("ecommerce")
    if ecom:
        pr = ecom.get("purchase_revenue")
        if pr is not None:
            ecom["purchase_revenue_in_usd"] = round(pr / 150.0, 6)
        else:
            ecom["purchase_revenue_in_usd"] = None
        # refund fields
        if event["event_name"] == "refund":
            ecom.setdefault("refund_value", ecom.get("purchase_revenue"))
            rv = ecom.get("refund_value")
            ecom["refund_value_in_usd"] = round(rv / 150.0, 6) if rv else None
        else:
            ecom.setdefault("refund_value", None)
            ecom.setdefault("refund_value_in_usd", None)

    # --- privacy_info ---
    if not event.get("privacy_info"):
        event["privacy_info"] = {
            "ads_storage": "Yes",
            "analytics_storage": "Yes",
            "uses_transient_token": "No",
        }
    else:
        pi = event["privacy_info"]
        pi.setdefault("ads_storage", "Yes")
        pi.setdefault("analytics_storage", "Yes")
        pi.setdefault("uses_transient_token", "No")

    return event


def migrate_file(input_path: str, output_path: str) -> int:
    """Migrate a single JSONL file. Returns event count.

    Handles in-place migration (input_path == output_path) safely.
    """
    # Read all events first (required for in-place)
    events = []
    with open(input_path, "r") as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))

    count = 0
    with open(output_path, "w") as fout:
        for event in events:
            event = migrate_event(event)
            fout.write(
                json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
            )
            count += 1
    return count


def main():
    input_dir = "output"
    output_dir = "output_v2"
    os.makedirs(output_dir, exist_ok=True)

    files = sorted(glob.glob(os.path.join(input_dir, "events_*.jsonl")))
    total = 0
    for fpath in files:
        fname = os.path.basename(fpath)
        out_path = os.path.join(output_dir, fname)
        count = migrate_file(fpath, out_path)
        total += count
        print(f"  {fname}: {count} events migrated")

    print(f"\nTotal: {total} events migrated to {output_dir}/")


if __name__ == "__main__":
    main()
