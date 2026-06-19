"""
db.py — Direct database access layer.

This is NOT a clean abstraction. It is a faithful representation of what
25-year-old code looks like after many hands have touched it: some queries
use parameterized inputs, some build strings, the connection is global,
and there's no transaction management to speak of.

In the real C++ codebase, this is spread across hundreds of .cpp files.
Here it's consolidated into one file for the exercise, but it is deliberately
not abstracted — no ORM, no repository pattern, no Unit of Work.
"""

import sqlite3
import os

# Global connection — the C++ app held a persistent DB connection for the
# lifetime of the process. Same pattern here.
_conn = None

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'erp.db')


def get_connection():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH)
        _conn.row_factory = sqlite3.Row   # so rows behave like dicts
        _conn.execute("PRAGMA foreign_keys = ON")
    return _conn


def init_db():
    """Create schema and load seed data if the database doesn't exist yet."""
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    seed_path   = os.path.join(os.path.dirname(__file__), 'seed.sql')

    conn = get_connection()

    # Check if tables exist already
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'")
    if cur.fetchone() is not None:
        return  # already initialised

    with open(schema_path, 'r') as f:
        conn.executescript(f.read())

    with open(seed_path, 'r') as f:
        conn.executescript(f.read())

    conn.commit()


# ---------------------------------------------------------------------------
# CUSTOMERS
# ---------------------------------------------------------------------------

def list_customers():
    conn = get_connection()
    cur = conn.execute(
        "SELECT customer_id, cust_code, company_name, contact_name, contact_phone, is_active "
        "FROM customers ORDER BY company_name"
    )
    return cur.fetchall()


def get_customer(customer_id):
    conn = get_connection()
    cur = conn.execute(
        "SELECT * FROM customers WHERE customer_id = ?", (customer_id,)
    )
    return cur.fetchone()


def create_customer(cust_code, company_name, contact_name, contact_phone,
                    contact_email, billing_city, billing_state, credit_limit):
    conn = get_connection()
    # Note: no input validation, no duplicate check beyond the UNIQUE constraint
    cur = conn.execute(
        "INSERT INTO customers "
        "(cust_code, company_name, contact_name, contact_phone, contact_email, "
        " billing_city, billing_state, credit_limit, created_date, is_active) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, date('now'), 1)",
        (cust_code, company_name, contact_name, contact_phone,
         contact_email, billing_city, billing_state, credit_limit)
    )
    conn.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# INVENTORY
# ---------------------------------------------------------------------------

def list_inventory():
    conn = get_connection()
    cur = conn.execute(
        "SELECT item_id, sku, description, unit_of_measure, qty_on_hand, "
        "       qty_reserved, unit_price, is_active "
        "FROM inventory WHERE is_active = 1 ORDER BY sku"
    )
    return cur.fetchall()


def get_inventory_item(item_id):
    conn = get_connection()
    cur = conn.execute("SELECT * FROM inventory WHERE item_id = ?", (item_id,))
    return cur.fetchone()


def get_inventory_by_sku(sku):
    conn = get_connection()
    cur = conn.execute("SELECT * FROM inventory WHERE sku = ?", (sku,))
    return cur.fetchone()


def update_inventory_qty(item_id, qty_delta):
    """Adjust qty_on_hand by qty_delta (positive = receive, negative = ship).
    No concurrency control. The C++ app ran single-user so this was never a problem.
    """
    conn = get_connection()
    conn.execute(
        "UPDATE inventory SET qty_on_hand = qty_on_hand + ? WHERE item_id = ?",
        (qty_delta, item_id)
    )
    conn.commit()


def reserve_inventory(item_id, qty):
    """Increment qty_reserved when an order line is created."""
    conn = get_connection()
    conn.execute(
        "UPDATE inventory SET qty_reserved = qty_reserved + ? WHERE item_id = ?",
        (qty, item_id)
    )
    conn.commit()


# ---------------------------------------------------------------------------
# ORDERS
# ---------------------------------------------------------------------------

def list_orders():
    conn = get_connection()
    # Note: this JOIN was added by someone in 2009. It makes the query slower
    # but the customer name was useful in the order list.
    cur = conn.execute(
        "SELECT o.order_id, o.order_number, c.company_name, o.order_date, "
        "       o.status, o.total_amount "
        "FROM orders o "
        "JOIN customers c ON c.customer_id = o.customer_id "
        "ORDER BY o.order_date DESC"
    )
    return cur.fetchall()


def get_order(order_id):
    conn = get_connection()
    cur = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    return cur.fetchone()


def get_order_lines(order_id):
    conn = get_connection()
    cur = conn.execute(
        "SELECT ol.*, i.sku, i.description "
        "FROM order_lines ol "
        "JOIN inventory i ON i.item_id = ol.item_id "
        "WHERE ol.order_id = ? ORDER BY ol.line_number",
        (order_id,)
    )
    return cur.fetchall()


def get_next_order_number():
    """Generate the next order number in the ORD-YYYY-NNNNN format.
    This logic is inlined here because in the original C++ it was a stored procedure
    that was removed in a 2012 "upgrade" and never properly replaced.
    """
    import datetime
    year = datetime.date.today().year
    conn = get_connection()
    cur = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE order_number LIKE ?",
        (f'ORD-{year}-%',)
    )
    count = cur.fetchone()[0]
    return f'ORD-{year}-{count + 1:05d}'


def create_order(customer_id, required_date, ship_addr1, ship_city,
                 ship_state, ship_zip, notes, entered_by, customer_po, lines):
    """Create an order with its lines in a single transaction.

    `lines` is a list of dicts:
        { 'item_id': int, 'qty_ordered': float,
          'unit_price': float, 'discount_pct': float }

    Business logic is mixed directly into this function — no service layer.
    Subtotal, tax, and totals are calculated inline. Inventory reservation
    happens inside the same transaction (or it would, if the original developer
    had thought about it — they didn't, so it's a separate call below).
    """
    conn = get_connection()
    order_number = get_next_order_number()

    subtotal = 0.0
    prepared_lines = []
    for i, line in enumerate(lines):
        line_total = line['qty_ordered'] * line['unit_price'] * (1 - line['discount_pct'] / 100.0)
        subtotal += line_total
        prepared_lines.append({
            'line_number': i + 1,
            'item_id':     line['item_id'],
            'qty_ordered': line['qty_ordered'],
            'unit_price':  line['unit_price'],
            'discount_pct':line['discount_pct'],
            'line_total':  round(line_total, 2),
        })

    # Hardcoded 8% tax rate — this was a TODO in 1999 and is still a TODO
    tax_amount     = round(subtotal * 0.08, 2)
    freight_amount = 25.00  # flat rate, always
    total_amount   = round(subtotal + tax_amount + freight_amount, 2)

    import datetime
    order_date = datetime.date.today().isoformat()

    cur = conn.execute(
        "INSERT INTO orders "
        "(order_number, customer_id, order_date, required_date, status, "
        " ship_addr1, ship_city, ship_state, ship_zip, "
        " subtotal, tax_amount, freight_amount, total_amount, "
        " notes, entered_by, customer_po) "
        "VALUES (?, ?, ?, ?, 'OPEN', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (order_number, customer_id, order_date, required_date,
         ship_addr1, ship_city, ship_state, ship_zip,
         round(subtotal, 2), tax_amount, freight_amount, total_amount,
         notes, entered_by, customer_po)
    )
    order_id = cur.lastrowid

    for line in prepared_lines:
        conn.execute(
            "INSERT INTO order_lines "
            "(order_id, line_number, item_id, qty_ordered, qty_shipped, "
            " unit_price, discount_pct, line_total) "
            "VALUES (?, ?, ?, ?, 0.0, ?, ?, ?)",
            (order_id, line['line_number'], line['item_id'],
             line['qty_ordered'], line['unit_price'],
             line['discount_pct'], line['line_total'])
        )
        # Reserve inventory — this should be in the same transaction but isn't
        # because reserve_inventory() commits on its own. Classic legacy bug.
        reserve_inventory(line['item_id'], line['qty_ordered'])

    conn.commit()
    return order_id, order_number
