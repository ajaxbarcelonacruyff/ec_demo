"""
Fix event ordering within sessions to match realistic user behavior.

Issues fixed:
1. login/sign_up appearing before first page_view
   -> Move first page_view to right after session_start/first_visit
2. session_start not at position 0
   -> Ensure session_start is always first (or after first_visit)
"""
import json
import glob
import os
from collections import defaultdict


def fix_session_order(events: list[dict]) -> list[dict]:
    """Fix event ordering within a single session."""
    if len(events) <= 1:
        return events

    evts = sorted(events, key=lambda x: x["event_timestamp"])
    names = [e["event_name"] for e in evts]

    # Already correct? Quick check
    has_login_issue = False
    if "page_view" in names:
        pv_idx = names.index("page_view")
        for n in names[:pv_idx]:
            if n in ("login", "sign_up"):
                has_login_issue = True
                break

    has_ss_issue = False
    if "first_visit" in names:
        if names[0] != "first_visit":
            has_ss_issue = True
        elif len(names) > 1 and names[1] != "session_start":
            has_ss_issue = True
    elif "session_start" in names and names[0] != "session_start":
        has_ss_issue = True

    if not has_login_issue and not has_ss_issue:
        return evts

    # Rebuild the event order
    # Step 1: Extract special events
    first_visit_evt = None
    session_start_evt = None
    first_page_view_evt = None
    login_evt = None
    signup_evt = None
    remaining = []

    for e in evts:
        name = e["event_name"]
        if name == "first_visit" and first_visit_evt is None:
            first_visit_evt = e
        elif name == "session_start" and session_start_evt is None:
            session_start_evt = e
        elif name == "page_view" and first_page_view_evt is None:
            first_page_view_evt = e
        elif name == "login" and login_evt is None and first_page_view_evt is None:
            # Only extract login if it's before first page_view
            login_evt = e
        elif name == "sign_up" and signup_evt is None and first_page_view_evt is None:
            signup_evt = e
        else:
            remaining.append(e)

    # Step 2: Build correct order
    # first_visit -> session_start -> page_view (landing) -> login/sign_up -> rest
    ordered = []
    base_ts = evts[0]["event_timestamp"]

    if first_visit_evt:
        first_visit_evt["event_timestamp"] = base_ts
        ordered.append(first_visit_evt)
        base_ts += 1000000  # +1 second

    if session_start_evt:
        session_start_evt["event_timestamp"] = base_ts
        ordered.append(session_start_evt)
        base_ts += 2000000  # +2 seconds

    if first_page_view_evt:
        first_page_view_evt["event_timestamp"] = base_ts
        ordered.append(first_page_view_evt)
        base_ts += 2000000  # +2 seconds

    if login_evt:
        login_evt["event_timestamp"] = base_ts
        ordered.append(login_evt)
        base_ts += 1000000

    if signup_evt:
        signup_evt["event_timestamp"] = base_ts
        ordered.append(signup_evt)
        base_ts += 1000000

    # Step 3: Ensure remaining events have timestamps after the reordered ones
    if remaining:
        min_remaining_ts = remaining[0]["event_timestamp"]
        if min_remaining_ts <= base_ts:
            offset = base_ts - min_remaining_ts + 1000000
            for e in remaining:
                e["event_timestamp"] += offset

    ordered.extend(remaining)

    # Update batch_event_index to match new order
    for i, e in enumerate(ordered):
        e["batch_event_index"] = i

    return ordered


def fix_file(input_path: str, output_path: str) -> dict:
    """Fix event ordering in a single JSONL file. Returns stats."""
    # Group events by session
    sessions = defaultdict(list)
    session_order = []  # Track insertion order
    seen_sessions = set()

    with open(input_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            sid = None
            for p in e.get("event_params", []):
                if p["key"] == "ga_session_id":
                    sid = p["value"].get("int_value")
                    break
            key = (e["user_pseudo_id"], sid or 0)
            sessions[key].append(e)
            if key not in seen_sessions:
                session_order.append(key)
                seen_sessions.add(key)

    # Fix each session
    fixed_count = 0
    all_events = []
    for key in session_order:
        events = sessions[key]
        original_names = [
            e["event_name"] for e in sorted(events, key=lambda x: x["event_timestamp"])
        ]
        fixed = fix_session_order(events)
        fixed_names = [e["event_name"] for e in fixed]
        if original_names != fixed_names:
            fixed_count += 1
        all_events.extend(fixed)

    # Sort all events by timestamp for the file
    all_events.sort(key=lambda x: x["event_timestamp"])

    # Write output
    with open(output_path, "w") as f:
        for e in all_events:
            f.write(json.dumps(e, ensure_ascii=False, separators=(",", ":")) + "\n")

    return {
        "total_sessions": len(sessions),
        "fixed_sessions": fixed_count,
        "total_events": len(all_events),
    }


def main():
    input_dir = "output"
    output_dir = "output_fixed"
    os.makedirs(output_dir, exist_ok=True)

    files = sorted(glob.glob(os.path.join(input_dir, "events_*.jsonl")))
    total_fixed = 0
    total_sessions = 0

    for fpath in files:
        fname = os.path.basename(fpath)
        out_path = os.path.join(output_dir, fname)
        stats = fix_file(fpath, out_path)
        total_fixed += stats["fixed_sessions"]
        total_sessions += stats["total_sessions"]
        if stats["fixed_sessions"] > 0:
            print(
                f"  {fname}: {stats['fixed_sessions']}/{stats['total_sessions']} sessions fixed"
            )

    print(f"\nTotal: {total_fixed}/{total_sessions} sessions fixed")
    print(f"Output written to {output_dir}/")


if __name__ == "__main__":
    main()
