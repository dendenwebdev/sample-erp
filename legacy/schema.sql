-- ERP Database Schema
-- This reflects a 25-year-old schema: wide tables, nullable everything,
-- naming conventions that made sense in 1999, accumulated columns that
-- nobody is sure are still used.

CREATE TABLE IF NOT EXISTS customers (
    customer_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_code       TEXT NOT NULL UNIQUE,           -- legacy short code, e.g. "ACME001"
    company_name    TEXT NOT NULL,
    contact_name    TEXT,
    contact_phone   TEXT,
    contact_email   TEXT,
    billing_addr1   TEXT,
    billing_addr2   TEXT,
    billing_city    TEXT,
    billing_state   TEXT,
    billing_zip     TEXT,
    billing_country TEXT DEFAULT 'US',
    credit_limit    REAL DEFAULT 0.0,
    credit_used     REAL DEFAULT 0.0,
    is_active       INTEGER DEFAULT 1,              -- 1 = active, 0 = inactive (no booleans in old schema)
    created_date    TEXT,                           -- stored as text: 'YYYY-MM-DD'
    notes           TEXT,
    -- These columns were added in 2008 and nobody is sure if they're used
    legacy_erp_id   TEXT,
    region_code     TEXT
);

CREATE TABLE IF NOT EXISTS inventory (
    item_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    sku             TEXT NOT NULL UNIQUE,
    description     TEXT NOT NULL,
    unit_of_measure TEXT DEFAULT 'EA',              -- EA, BOX, CASE, LB, etc.
    qty_on_hand     REAL DEFAULT 0.0,
    qty_reserved    REAL DEFAULT 0.0,               -- qty spoken for by open orders
    reorder_point   REAL DEFAULT 0.0,
    reorder_qty     REAL DEFAULT 0.0,
    unit_cost       REAL DEFAULT 0.0,
    unit_price      REAL DEFAULT 0.0,
    warehouse_loc   TEXT,                           -- e.g. "A3-B12"
    is_active       INTEGER DEFAULT 1,
    last_count_date TEXT,
    -- Vendor fields added in 2003, sometimes populated, sometimes not
    preferred_vendor TEXT,
    vendor_sku       TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    order_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number    TEXT NOT NULL UNIQUE,           -- e.g. "ORD-2024-00042"
    customer_id     INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date      TEXT NOT NULL,
    required_date   TEXT,
    shipped_date    TEXT,
    status          TEXT DEFAULT 'OPEN',            -- OPEN, PICKING, SHIPPED, INVOICED, CLOSED, CANCELLED
    ship_addr1      TEXT,
    ship_addr2      TEXT,
    ship_city       TEXT,
    ship_state      TEXT,
    ship_zip        TEXT,
    ship_country    TEXT DEFAULT 'US',
    subtotal        REAL DEFAULT 0.0,
    tax_amount      REAL DEFAULT 0.0,
    freight_amount  REAL DEFAULT 0.0,
    total_amount    REAL DEFAULT 0.0,
    notes           TEXT,
    -- Added 2011: who entered the order
    entered_by      TEXT,
    -- Added 2015: PO number from the customer
    customer_po     TEXT
);

CREATE TABLE IF NOT EXISTS order_lines (
    line_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL REFERENCES orders(order_id),
    line_number     INTEGER NOT NULL,
    item_id         INTEGER NOT NULL REFERENCES inventory(item_id),
    qty_ordered     REAL NOT NULL,
    qty_shipped     REAL DEFAULT 0.0,
    unit_price      REAL NOT NULL,
    discount_pct    REAL DEFAULT 0.0,
    line_total      REAL NOT NULL,
    notes           TEXT
);
