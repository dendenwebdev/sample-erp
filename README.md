# Sample ERP — Strangler Fig Workshop Exercise

This project is a lightweight ERP that mirrors the architecture of the C++ desktop ERP
your team is migrating: a Python application that connects directly to a SQLite database
with no web layer. You will apply the Strangler Fig Pattern to it during the workshop.

## What this simulates

| This project | Real migration |
|---|---|
| `legacy/app.py` | The C++ desktop application |
| `legacy/db.py` | Direct SQL calls embedded in C++ code |
| `legacy/erp.db` (generated) | The SQL Server production database |
| `strangled/orders_api.py` | The new Django Orders service |

## Prerequisites

- Python 3.6 or later
- No pip installs required for the legacy app
- The `strangled/orders_api.py` stub also uses stdlib only (`http.server`, `sqlite3`)

## Setup

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd sample-erp

# 2. Run the legacy app — it creates and seeds the database automatically
python3 legacy/app.py
```

The database file `erp.db` is created one level above `legacy/` (at `sample-erp/erp.db`)
on first run. Both the legacy app and the new API use this same file.

## Running the legacy app

```bash
python3 legacy/app.py
```

You will see a CLI menu. Navigate using the numbered options. Try:
1. List customers
2. List inventory
3. Create an order (note which function you're in — you'll be modifying it)

## Running the Orders API stub

In a separate terminal:

```bash
python3 strangled/orders_api.py
```

The server starts on `http://localhost:8001`. You can verify it with:

```bash
curl http://localhost:8001/health
```

Until you implement `create_order_in_db()`, the `POST /orders` endpoint returns
`501 Not Implemented`.

## Directory structure

```
sample-erp/
  legacy/
    app.py          # CLI application — the "C++ desktop app"
    db.py           # Direct SQLite access — the embedded SQL of the C++ app
    schema.sql      # Database schema (loaded automatically on first run)
    seed.sql        # Sample data (loaded automatically on first run)
  strangled/
    orders_api.py   # New Orders API — stdlib HTTP server, no Flask
    README.md       # What has been strangled and what is next
  README.md         # This file
```

---

## Workshop Exercise

### Context

The team has agreed that **Orders** is the first domain to strangle. This was chosen
because order creation is self-contained: it reads customers and inventory (reads only)
and writes to the orders and order_lines tables. No other domain writes to those tables.

### Your task

You have **15 minutes** in breakout rooms of 3 (one navigator, two reviewers — rotate
navigator at 7 minutes).

#### Step 1 — Implement `POST /orders` in `strangled/orders_api.py`

Open `strangled/orders_api.py` and find the `create_order_in_db()` function.
It is currently a stub that raises `NotImplementedError`.

Implement it. It receives a validated `payload` dict with this structure:

```python
{
    "customer_id":  int,
    "required_date": str | None,
    "ship_addr1":   str,
    "ship_city":    str,
    "ship_state":   str,
    "ship_zip":     str,
    "customer_po":  str,
    "notes":        str,
    "entered_by":   str,
    "lines": [
        {
            "item_id":     int,
            "qty_ordered": float,
            "unit_price":  float,
            "discount_pct":float,
        },
        ...
    ]
}
```

It must:
1. Validate that the customer exists (query the `customers` table)
2. Validate that each `item_id` exists (query the `inventory` table)
3. Calculate `subtotal`, `tax_amount` (8%), `freight_amount` ($25 flat), `total_amount`
4. Generate an order number using `_get_next_order_number(conn)`
5. Insert into the `orders` table
6. Insert into `order_lines` for each line
7. Commit the transaction
8. Return `(order_id, order_number)` as a tuple

See `legacy/db.py`'s `create_order()` function as a reference for the SQL and the schema.

#### Step 2 — Update `legacy/app.py` to call the API

Open `legacy/app.py` and find the `screen_create_order()` function.

There is a clearly marked block:
```
# STRANGLER FIG EXERCISE: THIS BLOCK IS WHAT YOU WILL REPLACE.
```

Replace the `db.create_order(...)` call with an HTTP POST to the API:

```python
import urllib.request

url = 'http://localhost:8001/orders'
body = json.dumps({
    'customer_id':  customer_id,
    'required_date':required_date or None,
    'ship_addr1':   ship_addr1,
    'ship_city':    ship_city,
    'ship_state':   ship_state,
    'ship_zip':     ship_zip,
    'customer_po':  customer_po,
    'notes':        notes,
    'entered_by':   entered_by,
    'lines':        lines,
}).encode('utf-8')

req = urllib.request.Request(
    url, data=body,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
with urllib.request.urlopen(req) as resp:
    result = json.loads(resp.read().decode('utf-8'))

order_id     = result['order_id']
order_number = result['order_number']
```

You will also need to `import json` at the top of `app.py` (it is not imported yet).

#### Step 3 — Verify end-to-end

With the API server running in one terminal:
```bash
python3 strangled/orders_api.py
```

Run the legacy app in another terminal:
```bash
python3 legacy/app.py
```

1. Choose "Orders" -> "Create order"
2. Fill in the fields
3. **Confirm the request hit the API**: look at the API server terminal — you should see
   a log line like `[2024-01-15 14:23:01] 127.0.0.1 POST /orders 201`
4. **Confirm the order is in the database**: choose "Orders" -> "List orders" in the
   legacy app — the new order should appear

#### Stretch goal — `GET /orders/{id}`

Implement `get_order_from_db(order_id)` in `strangled/orders_api.py`.

Then update `screen_view_order()` in `legacy/app.py` to call `GET /orders/{id}` instead
of `db.get_order()` and `db.get_order_lines()` when viewing an order.

---

## Debrief questions

- What did you have to change in `legacy/app.py`?
- Did you have to touch anything outside of `screen_create_order()`?
- What would you have to do differently if `create_order` was also decrementing inventory inline?
- What would break if you shut down the API server while the legacy app is running?
