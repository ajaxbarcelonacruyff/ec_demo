# Identity Model: user_id and user_pseudo_id

> **[Japanese version (日本語版)](IDENTITY_MODEL_ja.md)**

This document defines how `user_id` and `user_pseudo_id` behave in ec_demo's generated data, and the consistency rules between GA4 events and relational tables (orders, customers).

---

## Terminology

| Term | Description |
|------|-------------|
| **Person** | A real human who may own multiple devices. Has a `user_id` if registered (logged-in user), or no `user_id` (guest). |
| **Device** | A browser/app instance identified by `user_pseudo_id` (GA4 client ID). Bound to physical hardware. |
| **Session** | A single visit. Identified by `user_pseudo_id` + `ga_session_id`. |
| **Login state** | Whether the user is authenticated within a session. Controls whether `user_id` appears on events. |

---

## Person-Device Relationship

In real GA4 data, the relationship between `user_id` and `user_pseudo_id` is **many-to-many**:

```
Person (user_id)          Device (user_pseudo_id)
================          ======================
    U-001  ──────────────── DPID-AAA  (PC)
       \                 /
        \──────────────── DPID-BBB  (smartphone)
                         /
    U-002  ─────────────── DPID-BBB  (shared device)
        \
         \────────────────  DPID-CCC  (tablet)
```

### Multi-device users

A single person uses multiple devices. The same `user_id` appears with different `user_pseudo_id` values across sessions.

| Scenario | Example |
|----------|---------|
| PC at work, phone at home | `user_id=U-001` with `user_pseudo_id=AAA` (PC), `user_pseudo_id=BBB` (phone) |
| Phone + tablet | `user_id=U-002` with `user_pseudo_id=CCC` (phone), `user_pseudo_id=DDD` (tablet) |

**Configuration:**

```yaml
identity:
  multi_device_ratio: 0.25     # 25% of logged-in users own 2+ devices
  max_devices_per_user: 3      # Maximum devices per person
```

### Shared devices

A single device is used by multiple persons. The same `user_pseudo_id` appears with different `user_id` values across sessions.

| Scenario | Example |
|----------|---------|
| Family sharing a home PC | `user_pseudo_id=AAA` with `user_id=U-001` (Monday), `user_id=U-002` (Tuesday) |

**Configuration:**

```yaml
identity:
  shared_device_ratio: 0.05      # 5% of devices are shared
  max_users_per_device: 3        # Maximum persons per shared device
```

**Note:** `user_id` never changes within a single session. Shared device switching only occurs across separate sessions.

### Device properties

`device_profile` (OS, browser, screen size) and `geo_profile` (country, region, city) are bound to the **device**, not the person. When person B uses person A's device, the device properties remain the same (household sharing model).

---

## Session Identity State Machine

Every session follows a strict login-gated identity model. `user_id` on GA4 events is controlled exclusively by `login` and `logout` event boundaries.

### State transitions

```
SESSION START
  │
  │  user_id = NULL  (all sessions start anonymous)
  │
  ▼
  ┌─── Browse anonymously ───┐
  │  page_view (user_id=NULL) │
  │  search    (user_id=NULL) │
  └──────────┬───────────────┘
             │
             ▼
     ┌── LOGIN event ──┐
     │  user_id = U-xxx │
     └───────┬─────────┘
             │
             │  user_id = U-xxx on ALL events
             │
             ▼
  ┌─── Authenticated browsing + ecommerce ───┐
  │  add_to_cart      (user_id=U-xxx)         │
  │  begin_checkout   (user_id=U-xxx)         │
  │  purchase         (user_id=U-xxx)         │
  └──────────┬───────────────────────────────┘
             │
             ▼  (optional)
     ┌── LOGOUT event ──┐
     │  user_id = NULL   │
     └───────┬──────────┘
             │
             │  user_id = NULL on ALL events
             │
             ▼
  ┌─── Anonymous browsing ───┐
  │  page_view (user_id=NULL) │
  └──────────────────────────┘
             │
             ▼
         SESSION END
```

### Invariants (non-negotiable)

| # | Rule | Description |
|---|------|-------------|
| 1 | **purchase requires user_id** | Every `purchase` event has a non-NULL `user_id`. |
| 2 | **login before ecommerce** | A `login` or `sign_up` event must precede any ecommerce event (`add_to_cart`, `begin_checkout`, `purchase`, etc.) within the same session. |
| 3 | **user_id frozen after login** | From `login`/`sign_up` until `logout` or session end, the same `user_id` appears on ALL events. |
| 4 | **NULL after logout** | After a `logout` event, `user_id` is NULL on all subsequent events until the next `login`. |
| 5 | **No non-NULL to non-NULL change** | `user_id` never changes from one non-NULL value to a different non-NULL value within a session. Transitions are only `NULL -> U-xxx` (login) or `U-xxx -> NULL` (logout). |

### Login timing

For persons with a `user_id`, login fires at one of three timings:

| Timing | Default rate | Description |
|--------|-------------|-------------|
| **Early login** | 60% | Login during initial browsing, after landing page_view |
| **Late login** | 25% | Login just before ecommerce events (at add_to_cart) |
| **No login** | 15% | Fully anonymous session. No ecommerce. No purchase. |

First-time sessions emit `sign_up` instead of `login` (same identity semantics).

**Configuration:**

```yaml
identity:
  early_login_rate: 0.60
  late_login_rate: 0.25
  mid_session_logout_rate: 0.05
```

### Forced re-login at checkout

If a user logs out mid-session and subsequently reaches the checkout flow, a `login` event is injected before `begin_checkout`. This models the common Japanese EC site behavior of requiring authentication at checkout.

---

## Canonical Event Sequences

### A. Returning user, early login, purchase

```
session_start       (user_id=NULL)
page_view /         (user_id=NULL)    ← landing page
login               (user_id=U-001)   ← identity set
page_view /category (user_id=U-001)
view_item_list      (user_id=U-001)
select_item         (user_id=U-001)
page_view /product  (user_id=U-001)
view_item           (user_id=U-001)
add_to_cart         (user_id=U-001)
view_cart           (user_id=U-001)
begin_checkout      (user_id=U-001)
add_shipping_info   (user_id=U-001)
add_payment_info    (user_id=U-001)
purchase            (user_id=U-001)   ← user_id guaranteed non-NULL
```

### B. Returning user, late login, purchase

```
session_start       (user_id=NULL)
page_view /         (user_id=NULL)
page_view /category (user_id=NULL)
view_item_list      (user_id=NULL)
view_item           (user_id=NULL)
login               (user_id=U-001)   ← login just before ecommerce
add_to_cart         (user_id=U-001)
begin_checkout      (user_id=U-001)
purchase            (user_id=U-001)
```

### C. Logged-in user, no login this session (anonymous browse)

```
session_start       (user_id=NULL)
page_view /         (user_id=NULL)
page_view /category (user_id=NULL)
view_item           (user_id=NULL)
                    ← no login, no ecommerce, no purchase
```

### D. First-time user, sign_up, purchase

```
first_visit         (user_id=NULL)
session_start       (user_id=NULL)
page_view /         (user_id=NULL)
sign_up             (user_id=U-002)   ← sign_up instead of login
page_view /product  (user_id=U-002)
add_to_cart         (user_id=U-002)
purchase            (user_id=U-002)
```

### E. Login, purchase, then logout and anonymous browsing

```
session_start       (user_id=NULL)
page_view /         (user_id=NULL)
login               (user_id=U-001)
add_to_cart         (user_id=U-001)
purchase            (user_id=U-001)
logout              (user_id=NULL)    ← identity cleared
page_view /sale     (user_id=NULL)
page_view /product  (user_id=NULL)
```

### F. Noise session (GA4 tracking lost, order still recorded)

```
GA4 events:
  session_start     (user_id=NULL)
  page_view /       (user_id=NULL)
  page_view /browse (user_id=NULL)
  ← no login, no ecommerce events in GA4

orders.csv:
  order_id=TXN-xxx, customer_id=U-001, total_amount=12345
  ← order exists in relational tables
```

### G. Guest user (no account)

```
session_start       (user_id=NULL)
page_view /         (user_id=NULL)
page_view /category (user_id=NULL)
view_item           (user_id=NULL)
                    ← no login possible, no purchase
```

---

## GA4 Events and Orders Data Consistency

### Rules

| Direction | Rule |
|-----------|------|
| **GA4 purchase -> orders** | Every GA4 `purchase` event's `user_id`, `transaction_id`, revenue, and items **MUST exactly match** the corresponding `orders` / `order_items` records. |
| **orders -> GA4 purchase** | Orders records **MAY exist** without a corresponding GA4 `purchase` event. This represents tracking loss (ad blockers, consent refusal, network errors). |

### Single source of truth

Both the GA4 `purchase` event and the `orders`/`order_items` records are derived from a single `purchase_info` dict. This guarantees field-level consistency:

```
purchase_info (single source of truth)
    │
    ├──→ GA4 purchase event    (emitted when not a noise session)
    │     transaction_id  ← purchase_info["transaction_id"]
    │     user_id         ← purchase_info["user_id"]
    │     value           ← purchase_info["total_amount"]
    │     items           ← purchase_info["items"]
    │
    └──→ orders.csv + order_items.csv  (always written)
          order_id        ← purchase_info["transaction_id"]
          customer_id     ← purchase_info["user_id"]
          total_amount    ← purchase_info["total_amount"]
          items           ← purchase_info["items"]
```

### Consistency fields

| Field | GA4 purchase event | orders.csv | Match required |
|-------|-------------------|------------|----------------|
| Transaction ID | `event_params.transaction_id` | `order_id` | Exact |
| User ID | `user_id` | `customer_id` | Exact |
| Revenue | `event_params.value` | `total_amount` | Exact |
| Tax | `event_params.tax` | `tax_amount` | Exact |
| Shipping | `event_params.shipping` | `shipping_fee` | Exact |
| Items | `items[].item_id`, `quantity` | `order_items.product_id`, `quantity` | Exact |

---

## Noise Model

### Session-level tracking loss (`null_user_id_rate`)

Simulates scenarios where GA4 tracking is blocked (ad blockers, consent refusal, etc.).

| Aspect | Behavior |
|--------|----------|
| GA4 events | Only anonymous page_views emitted (no login, no ecommerce events) |
| Orders data | Purchase **still recorded** in orders/order_items with real user_id |
| Effect | Creates "orders without GA4 attribution" -- realistic data gap |

**Configuration:**

```yaml
noise:
  null_user_id_rate: 0.05    # 5% of sessions from logged-in users
```

### Individual event loss (`ga4_event_loss_rate`)

Simulates individual events being lost in transit (network errors, sampling).

| Aspect | Behavior |
|--------|----------|
| GA4 events | Random events dropped (except `session_start`) |
| Orders data | Unaffected |
| Effect | Creates gaps in event sequences (e.g., `add_to_cart` present but `view_item` missing) |

**Configuration:**

```yaml
noise:
  ga4_event_loss_rate: 0.03   # 3% of individual events
```

---

## Identity Resolution

### The problem

Because sessions start anonymous and login occurs mid-session, analysts need to stitch `user_pseudo_id` to `user_id` for cross-device attribution.

### SQL approach

The included `v_identity_resolution.sql` view resolves each `user_pseudo_id` to the most frequently associated `user_id`:

```sql
-- For each device (user_pseudo_id), find the user_id
-- that appeared most frequently in logged-in sessions.
SELECT
  user_pseudo_id,
  user_id AS resolved_user_id,
  session_count AS logged_in_sessions
FROM (
  SELECT
    user_pseudo_id,
    user_id,
    COUNT(DISTINCT ga_session_id) AS session_count,
    ROW_NUMBER() OVER (
      PARTITION BY user_pseudo_id
      ORDER BY COUNT(DISTINCT ga_session_id) DESC
    ) AS rn
  FROM events
  WHERE user_id IS NOT NULL
  GROUP BY user_pseudo_id, user_id
)
WHERE rn = 1
```

### Known limitations

| Scenario | Behavior |
|----------|----------|
| **Shared device, equal activity** | When two users are equally active on one device, the resolution picks arbitrarily. |
| **Guest on shared device** | Guest sessions are misattributed to the primary user. This is intentional -- it mirrors real-world identity resolution limitations. |
| **Cookie reset** | This model treats `user_pseudo_id` as permanently bound to a device. Real GA4 resets `user_pseudo_id` on cookie clear or app reinstall. |

---

## Configuration Reference

All identity-related settings:

```yaml
users:
  logged_in_ratio: 0.30         # Ratio of persons with user_id

identity:
  multi_device_ratio: 0.25      # % of logged-in users with 2+ devices
  max_devices_per_user: 3
  shared_device_ratio: 0.05     # % of devices shared by 2+ persons
  max_users_per_device: 3
  early_login_rate: 0.60        # Login during initial browse
  late_login_rate: 0.25         # Login at cart/checkout
  mid_session_logout_rate: 0.05 # Logout after purchase

noise:
  null_user_id_rate: 0.05       # Session-level GA4 tracking loss
  ga4_event_loss_rate: 0.03     # Individual event loss
```

**Tip:** For attribution analysis demos, set `logged_in_ratio >= 0.50` to increase cross-device signal volume.

---

## Impact on Analysis

| Analysis Type | What This Model Enables |
|---------------|------------------------|
| **Cross-device attribution** | Same `user_id` across multiple `user_pseudo_id` values. Touchpoints span PC and mobile. |
| **Identity stitching** | Anonymous sessions (pre-login) can be linked to known users via `user_pseudo_id`. |
| **Data quality assessment** | Orders without GA4 events reveal tracking gaps. |
| **Funnel analysis** | Login timing (early/late) affects where users enter the measured funnel. |
| **Shared device detection** | Multiple `user_id` values on one `user_pseudo_id` indicate shared devices. |
