"""GA4 BigQuery Export schema event builder and JSONL serializer."""

import json
from datetime import datetime


def ep(key: str, *, string_value: str = None, int_value: int = None,
       float_value: float = None) -> dict:
    """Build a single event_param entry."""
    param = {"key": key, "value": {}}
    if string_value is not None:
        param["value"]["string_value"] = string_value
    if int_value is not None:
        param["value"]["int_value"] = int_value
    if float_value is not None:
        param["value"]["float_value"] = float_value
    return param


def up(key: str, *, string_value: str = None, int_value: int = None) -> dict:
    """Build a single user_property entry."""
    prop = {"key": key, "value": {}}
    if string_value is not None:
        prop["value"]["string_value"] = string_value
    if int_value is not None:
        prop["value"]["int_value"] = int_value
    return prop


def build_event(
    event_name: str,
    event_timestamp: int,
    event_date: str,
    user_pseudo_id: str,
    event_params: list[dict],
    user_properties: list[dict],
    device: dict,
    geo: dict,
    traffic_source: dict,
    collected_traffic_source: dict = None,
    platform: str = "WEB",
    stream_id: str = "1234567890",
    user_id: str = None,
    user_first_touch_timestamp: int = None,
    items: list[dict] = None,
    ecommerce: dict = None,
    privacy_info: dict = None,
) -> dict:
    """Build a complete GA4 event row."""
    event = {
        "event_date": event_date,
        "event_timestamp": event_timestamp,
        "event_name": event_name,
        "user_pseudo_id": user_pseudo_id,
        "platform": platform,
        "stream_id": stream_id,
        "event_params": event_params,
        "user_properties": user_properties,
        "device": device,
        "geo": geo,
        "traffic_source": traffic_source,
    }

    if user_id:
        event["user_id"] = user_id
    if user_first_touch_timestamp:
        event["user_first_touch_timestamp"] = user_first_touch_timestamp
    if collected_traffic_source:
        event["collected_traffic_source"] = collected_traffic_source
    if items:
        event["items"] = items
    if ecommerce:
        event["ecommerce"] = ecommerce
    if privacy_info:
        event["privacy_info"] = privacy_info

    return event


def event_to_jsonl(event: dict) -> str:
    """Serialize event dict to a single JSONL line."""
    return json.dumps(event, ensure_ascii=False, separators=(",", ":"))
