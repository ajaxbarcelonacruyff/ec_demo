#!/usr/bin/env python3
"""BigQuery loader for ec_demo generated data.

Loads the following tables into a specified BigQuery dataset:
  events_YYYYMMDD  (JSONL, one table per day — matches GA4 export format)
  customers        (CSV)
  products         (CSV)
  orders           (CSV)
  order_items      (CSV)

Prerequisites:
  pip install google-cloud-bigquery

Authentication (choose one):
  # Option A: gcloud CLI (recommended for local use)
  gcloud auth application-default login

  # Option B: service account key file
  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json

Usage:
  python bigquery_load.py --project YOUR_PROJECT_ID --dataset ec_demo
  python bigquery_load.py --project YOUR_PROJECT_ID --dataset ec_demo \\
      --location asia-northeast1 --output-dir ./output
"""

import argparse
import sys
from pathlib import Path

from google.cloud import bigquery
from google.cloud.exceptions import NotFound


# ---------------------------------------------------------------------------
# Schema definitions
# ---------------------------------------------------------------------------

def _value_record(nullable=True):
    mode = "NULLABLE" if nullable else "REQUIRED"
    return bigquery.SchemaField("value", "RECORD", mode=mode, fields=[
        bigquery.SchemaField("string_value", "STRING"),
        bigquery.SchemaField("int_value",    "INTEGER"),
        bigquery.SchemaField("float_value",  "FLOAT"),
    ])


EVENTS_SCHEMA = [
    bigquery.SchemaField("event_date",                "STRING"),
    bigquery.SchemaField("event_timestamp",           "INTEGER"),
    bigquery.SchemaField("event_name",                "STRING"),
    bigquery.SchemaField("user_pseudo_id",            "STRING"),
    bigquery.SchemaField("user_id",                   "STRING"),
    bigquery.SchemaField("platform",                  "STRING"),
    bigquery.SchemaField("stream_id",                 "STRING"),
    bigquery.SchemaField("user_first_touch_timestamp","INTEGER"),
    bigquery.SchemaField("event_params", "RECORD", mode="REPEATED", fields=[
        bigquery.SchemaField("key", "STRING"),
        _value_record(),
    ]),
    bigquery.SchemaField("user_properties", "RECORD", mode="REPEATED", fields=[
        bigquery.SchemaField("key", "STRING"),
        _value_record(),
    ]),
    bigquery.SchemaField("device", "RECORD", fields=[
        bigquery.SchemaField("category",                  "STRING"),
        bigquery.SchemaField("operating_system",          "STRING"),
        bigquery.SchemaField("operating_system_version",  "STRING"),
        bigquery.SchemaField("language",                  "STRING"),
        bigquery.SchemaField("mobile_brand_name",         "STRING"),
        bigquery.SchemaField("mobile_model_name",         "STRING"),
        bigquery.SchemaField("mobile_marketing_name",     "STRING"),
        bigquery.SchemaField("is_limited_ad_tracking",    "STRING"),
        bigquery.SchemaField("web_info", "RECORD", fields=[
            bigquery.SchemaField("browser",         "STRING"),
            bigquery.SchemaField("browser_version", "STRING"),
            bigquery.SchemaField("hostname",        "STRING"),
        ]),
    ]),
    bigquery.SchemaField("geo", "RECORD", fields=[
        bigquery.SchemaField("continent",     "STRING"),
        bigquery.SchemaField("sub_continent", "STRING"),
        bigquery.SchemaField("country",       "STRING"),
        bigquery.SchemaField("region",        "STRING"),
        bigquery.SchemaField("city",          "STRING"),
    ]),
    bigquery.SchemaField("traffic_source", "RECORD", fields=[
        bigquery.SchemaField("source", "STRING"),
        bigquery.SchemaField("medium", "STRING"),
        bigquery.SchemaField("name",   "STRING"),
    ]),
    bigquery.SchemaField("collected_traffic_source", "RECORD", fields=[
        bigquery.SchemaField("manual_source",        "STRING"),
        bigquery.SchemaField("manual_medium",        "STRING"),
        bigquery.SchemaField("manual_campaign_name", "STRING"),
        bigquery.SchemaField("manual_content",       "STRING"),
        bigquery.SchemaField("gclid",                "STRING"),
    ]),
    bigquery.SchemaField("items", "RECORD", mode="REPEATED", fields=[
        bigquery.SchemaField("item_id",        "STRING"),
        bigquery.SchemaField("item_name",      "STRING"),
        bigquery.SchemaField("item_brand",     "STRING"),
        bigquery.SchemaField("item_category",  "STRING"),
        bigquery.SchemaField("item_category2", "STRING"),
        bigquery.SchemaField("item_category3", "STRING"),
        bigquery.SchemaField("price",          "FLOAT"),
        bigquery.SchemaField("quantity",       "INTEGER"),
        bigquery.SchemaField("index",          "INTEGER"),
        bigquery.SchemaField("coupon",         "STRING"),
        bigquery.SchemaField("discount",       "FLOAT"),
        bigquery.SchemaField("item_list_id",   "STRING"),
        bigquery.SchemaField("item_list_name", "STRING"),
        bigquery.SchemaField("promotion_id",   "STRING"),
        bigquery.SchemaField("promotion_name", "STRING"),
        bigquery.SchemaField("creative_name",  "STRING"),
        bigquery.SchemaField("creative_slot",  "STRING"),
    ]),
    bigquery.SchemaField("ecommerce", "RECORD", fields=[
        bigquery.SchemaField("transaction_id",     "STRING"),
        bigquery.SchemaField("purchase_revenue",   "FLOAT"),
        bigquery.SchemaField("total_item_quantity","INTEGER"),
        bigquery.SchemaField("unique_items",       "INTEGER"),
        bigquery.SchemaField("shipping_value",     "FLOAT"),
        bigquery.SchemaField("tax_value",          "FLOAT"),
    ]),
    bigquery.SchemaField("batch_page_id",      "INTEGER"),
    bigquery.SchemaField("batch_ordering_id",  "INTEGER"),
    bigquery.SchemaField("batch_event_index",  "INTEGER"),
    bigquery.SchemaField("session_traffic_source_last_click", "RECORD", fields=[
        bigquery.SchemaField("manual_campaign", "RECORD", fields=[
            bigquery.SchemaField("source",        "STRING"),
            bigquery.SchemaField("medium",        "STRING"),
            bigquery.SchemaField("campaign_name", "STRING"),
            bigquery.SchemaField("content",       "STRING"),
        ]),
        bigquery.SchemaField("google_ads_campaign", "RECORD", fields=[
            bigquery.SchemaField("customer_id",   "STRING"),
            bigquery.SchemaField("account_name",  "STRING"),
            bigquery.SchemaField("campaign_id",   "STRING"),
            bigquery.SchemaField("campaign_name", "STRING"),
            bigquery.SchemaField("ad_group_id",   "STRING"),
            bigquery.SchemaField("ad_group_name", "STRING"),
        ]),
    ]),
]

# CSV tables: schema is auto-detected from header + data
CSV_TABLES = ["customers", "products", "orders", "order_items"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure_dataset(client: bigquery.Client, dataset_ref: str, location: str):
    try:
        client.get_dataset(dataset_ref)
        print(f"  Dataset {dataset_ref} already exists.")
    except NotFound:
        ds = bigquery.Dataset(dataset_ref)
        ds.location = location
        client.create_dataset(ds)
        print(f"  Dataset {dataset_ref} created (location={location}).")


def load_csv(client: bigquery.Client, dataset_ref: str,
             table_name: str, filepath: Path) -> int:
    table_id = f"{dataset_ref}.{table_name}"
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    with open(filepath, "rb") as f:
        job = client.load_table_from_file(f, table_id, job_config=job_config)
    job.result()
    table = client.get_table(table_id)
    print(f"  {table_name}: {table.num_rows:,} rows loaded.")
    return table.num_rows


def load_events_jsonl(client: bigquery.Client, dataset_ref: str,
                      jsonl_files: list[Path]) -> int:
    """Load JSONL event files into date-sharded tables (events_YYYYMMDD).

    This matches the real GA4 BigQuery Export naming convention.
    """
    total = 0
    for filepath in sorted(jsonl_files):
        # filename: events_20250101.jsonl -> table: events_20250101
        table_name = filepath.stem          # "events_20250101"
        table_id   = f"{dataset_ref}.{table_name}"

        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            schema=EVENTS_SCHEMA,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )
        with open(filepath, "rb") as f:
            job = client.load_table_from_file(f, table_id, job_config=job_config)
        job.result()

        table = client.get_table(table_id)
        total += table.num_rows
        print(f"  {table_name}: {table.num_rows:,} rows loaded.")

    return total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Load ec_demo data into BigQuery")
    parser.add_argument("--project",    required=True, help="GCP project ID")
    parser.add_argument("--dataset",    required=True, help="BigQuery dataset name")
    parser.add_argument("--location",   default="asia-northeast1",
                        help="Dataset location (default: asia-northeast1)")
    parser.add_argument("--output-dir", default="./output",
                        help="Directory containing generated files (default: ./output)")
    parser.add_argument("--key-file",   default=None,
                        help="Path to service account key JSON (omit to use ADC)")
    args = parser.parse_args()

    output_dir  = Path(args.output_dir)
    dataset_ref = f"{args.project}.{args.dataset}"

    # Validate output directory
    if not output_dir.exists():
        print(f"Error: output directory '{output_dir}' not found. Run generate.py first.")
        sys.exit(1)

    # BigQuery client
    client_kwargs = {"project": args.project}
    if args.key_file:
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(args.key_file)
        client_kwargs["credentials"] = creds
    client = bigquery.Client(**client_kwargs)

    print(f"\n=== Loading ec_demo data into {dataset_ref} ===\n")

    # 1. Dataset
    print("[1/3] Ensuring dataset exists...")
    ensure_dataset(client, dataset_ref, args.location)

    # 2. CSV tables
    print("\n[2/3] Loading CSV tables...")
    csv_total = 0
    for table_name in CSV_TABLES:
        filepath = output_dir / f"{table_name}.csv"
        if not filepath.exists():
            print(f"  {table_name}: SKIP (file not found: {filepath})")
            continue
        csv_total += load_csv(client, dataset_ref, table_name, filepath)

    # 3. GA4 events (JSONL, date-sharded)
    print("\n[3/3] Loading GA4 events (date-sharded JSONL)...")
    jsonl_files = sorted(output_dir.glob("events_*.jsonl"))
    if not jsonl_files:
        print("  No JSONL files found. Run generate.py first.")
    else:
        events_total = load_events_jsonl(client, dataset_ref, jsonl_files)

    print(f"\n{'='*55}")
    print("  Done!")
    print(f"  Project : {args.project}")
    print(f"  Dataset : {args.dataset}")
    print(f"  Location: {args.location}")
    print(f"{'='*55}\n")
    print("BigQuery コンソール:")
    print(f"  https://console.cloud.google.com/bigquery?project={args.project}")


if __name__ == "__main__":
    main()
