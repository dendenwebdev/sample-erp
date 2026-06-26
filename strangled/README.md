# Strangled Components — What Has Been Done and What Is Next

This directory contains the new Django-style API services that are replacing
the legacy ERP domain by domain.

---

## What has been strangled

### Orders domain — `orders_api.py` (COMPLETE)

**Status:** `POST /orders` is implemented and `legacy/app.py` routes order creation
through the API.  Test ran with orders_api.py running (order saved) and stopped (order did not save).

**What the facade intercepts:** Order creation (`POST /orders`).

**What still goes direct to DB:** Order reads (`screen_view_order` in `legacy/app.py`),
inventory reservation, customer lookup.

**The change made to the legacy app:**
- `legacy/app.py` `screen_create_order()` calls `http://localhost:8001/orders` via
  `urllib.request` instead of calling `db.create_order()` directly.
- No other function in the legacy app was modified.

**What the new API does:**
- Accepts `POST /orders` with a JSON payload
- Validates customer and inventory line items
- Calculates totals (subtotal, 8% tax, $25 flat freight)
- Generates order number in `ORD-YYYY-NNNNN` format
- Writes to the shared `erp.db` SQLite database

**Shared database note:**
The Django Orders API and the legacy app both write to the same `erp.db` file.
This is intentional during migration. The `orders` and `order_lines` tables are
now owned by the Orders API. The legacy app should not write to those tables directly.

---

## What has NOT been strangled yet

### Customers domain

- Still owned entirely by the legacy app
- The Orders API queries the `customers` table for validation but does not write to it
- Next step: extract `POST /customers` and `GET /customers`

### Inventory domain

- Still owned entirely by the legacy app
- Both order creation paths (legacy direct and new API) update `inventory.qty_reserved`
- This is a known inconsistency during migration: the reservation logic is duplicated
- Next step: extract inventory management to a dedicated service before addressing
  the reservation duplication

---

## Migration sequence rationale

The team chose Orders before Inventory before Customers based on dependency analysis:

1. **Orders** is extracted first because it is the primary domain delivering business value.
   The Orders service depends on Customers and Inventory for reads only — no write coupling.

2. **Inventory** comes second. Once Orders is live, inventory reservation can be unified
   in the Inventory service. The Orders service will call the Inventory service to reserve
   rather than writing directly to the inventory table.

3. **Customers** comes last because it is referenced by almost every other domain.
   Extracting it last means the API contract stabilises after the consuming domains are settled.

---

## Running what's here

```bash
# Start the Orders API
python3 strangled/orders_api.py

# In another terminal, verify it's up
curl http://localhost:8001/health

# Run the legacy app (it will call the API for order creation after the exercise)
python3 legacy/app.py
```

---

## Known issues and deliberate omissions

- **Authentication:** None. The C++ app was single-user and LAN-only. Auth will be added
  when the Next.js frontend is introduced.
- **Transactions across services:** When the Orders API creates an order and the legacy
  app's inventory reservation fails (or vice versa), the two writes are not in the same
  transaction. This is the "distributed transaction" problem. For the workshop, it is
  intentionally left unresolved — it's a real problem you'll face in the migration.
- **Order number collisions:** The order number generation in `orders_api.py` uses the
  same `COUNT(*)` approach as `legacy/db.py`. In production, use a database sequence or
  a dedicated number table with row-level locking.
- **No HTTPS:** The API runs on plain HTTP. Production deployment will terminate TLS
  at the load balancer.
   in the Inventory service. The Orders service will call the Inventory service to reserve
   rather than writing directly to the inventory table.

3. **Customers** comes last because it is referenced by almost every other domain.
   Extracting it last means the API contract stabilises after the consuming domains are settled.

---

## Running what's here

```bash
# Start the Orders API
python3 strangled/orders_api.py

# In another terminal, verify it's up
curl http://localhost:8001/health

# Run the legacy app (it will call the API for order creation after the exercise)
python3 legacy/app.py
```

---

## Known issues and deliberate omissions

- **Authentication:** None. The C++ app was single-user and LAN-only. Auth will be added
  when the Next.js frontend is introduced.
- **Transactions across services:** When the Orders API creates an order and the legacy
  app's inventory reservation fails (or vice versa), the two writes are not in the same
  transaction. This is the "distributed transaction" problem. For the workshop, it is
  intentionally left unresolved — it's a real problem you'll face in the migration.
- **Order number collisions:** The order number generation in `orders_api.py` uses the
  same `COUNT(*)` approach as `legacy/db.py`. In production, use a database sequence or
  a dedicated number table with row-level locking.
- **No HTTPS:** The API runs on plain HTTP. Production deployment will terminate TLS
  at the load balancer.
