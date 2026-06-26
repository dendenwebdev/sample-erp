#!/usr/bin/env python3
"""
orders_api.py — Strangled Orders API

This is the new Django-style API endpoint for the Orders domain,
implemented using Python's stdlib http.server so it requires no pip installs.

In a real migration this would be a Django view. The structure here mirrors
what you'd build in Django: request parsing, validation, DB write, response.

EXERCISE: Two endpoints need to be implemented.

Endpoint 1 (required): POST /orders
  - Accepts JSON body (see schema below)
  - Creates an order in the database
  - Returns JSON: {"order_id": int, "order_number": str}

Endpoint 2 (stretch goal): GET /orders/{id}
  - Returns the order header and lines for a given order_id
  - Returns JSON with order details
  - Returns 404 if order not found

Run with: python3 strangled/orders_api.py
The server listens on http://localhost:8001

Request body schema for POST /orders:
{
    "customer_id":  int,          -- required
    "required_date": str | null,  -- optional, "YYYY-MM-DD"
    "ship_addr1":   str,          -- optional
    "ship_city":    str,          -- optional
    "ship_state":   str,          -- optional
    "ship_zip":     str,          -- optional
    "customer_po":  str,          -- optional
    "notes":        str,          -- optional
    "entered_by":   str,          -- optional, defaults to "api"
    "lines": [                    -- required, at least one line
        {
            "item_id":     int,   -- required
            "qty_ordered": float, -- required, must be > 0
            "unit_price":  float, -- required, must be >= 0
            "discount_pct":float  -- optional, defaults to 0.0
        }
    ]
}
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

# ---------------------------------------------------------------------------
# Database path: same DB the legacy app uses
# ---------------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'erp.db')


def get_db():
    """Return a fresh SQLite connection to the shared ERP database."""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------------------------------------------------------------------
# Business logic
# ---------------------------------------------------------------------------

def _get_next_order_number(conn):
    """Generate the next order number. Duplicated from legacy/db.py intentionally:
    during migration both systems need to generate non-colliding order numbers.
    In the real migration you'd use a sequence table or database sequence.
    For this exercise the shared DB means duplicates are unlikely in a workshop.
    """
    import datetime
    year = datetime.date.today().year
    cur = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE order_number LIKE ?",
        (f'ORD-{year}-%',)
    )
    count = cur.fetchone()[0]
    return f'ORD-{year}-{count + 1:05d}'


def create_order_in_db(payload):
    """
    EXERCISE: Implement this function.

    It receives a validated payload dict (same structure as the JSON body)
    and must:
    1. Open a DB connection
    2. Generate an order number
    3. Calculate subtotal, tax (8%), freight ($25 flat), total
    4. INSERT into orders table
    5. INSERT into order_lines for each line
    6. Optionally update inventory.qty_reserved
    7. Commit and return (order_id, order_number)

    Raise ValueError with a descriptive message if validation fails
    (e.g., customer not found, item not found, qty <= 0).

    Starter code below — fill in the TODOs.
    """
    import datetime

    conn = get_db()
    try:
        customer_id = payload['customer_id']

        # TODO: validate customer exists and is active
        # cur = conn.execute("SELECT ...", (customer_id,))
        # customer = cur.fetchone()
        # if not customer:
        #     raise ValueError(f"Customer {customer_id} not found")
        customer = conn.execute(
            "SELECT customer_id FROM customers WHERE customer_id = ? AND is_active = 1",
            (customer_id,),
        ).fetchone()
        if not customer:
            raise ValueError(f"Customer {customer_id} not found or is inactive")

        lines = payload.get('lines', [])
        if not lines:
            raise ValueError("Order must have at least one line")

        # TODO: validate each line's item_id exists and qty > 0
        # for line in lines:
        #     item = conn.execute("SELECT ...", (line['item_id'],)).fetchone()
        #     if not item:
        #         raise ValueError(f"Item {line['item_id']} not found")
        #     if line['qty_ordered'] <= 0:
        #         raise ValueError("qty_ordered must be positive")

        # TODO: calculate subtotal
        # subtotal = 0.0
        # prepared_lines = []
        # for i, line in enumerate(lines):
        #     ...
        subtotal = 0.0
        prepared_lines = []
        for i, line in enumerate(lines):
            item = conn.execute(
                "SELECT item_id FROM inventory WHERE item_id = ?", (line['item_id'],)
            ).fetchone()
            if not item:
                raise ValueError(f"Item {line['item_id']} not found")

            line_total = line['qty_ordered'] * line['unit_price'] * (1 - line['discount_pct'] / 100.0)
            subtotal += line_total
            prepared_lines.append({
                'line_number':  i + 1,
                'item_id':      line['item_id'],
                'qty_ordered':  line['qty_ordered'],
                'unit_price':   line['unit_price'],
                'discount_pct': line['discount_pct'],
                'line_total':   round(line_total, 2),
            })

        # TODO: calculate tax, freight, total
        # tax_amount     = round(subtotal * 0.08, 2)
        # freight_amount = 25.00
        # total_amount   = round(subtotal + tax_amount + freight_amount, 2)
        tax_amount = round(subtotal * 0.08, 2)
        freight_amount = 25.00
        total_amount = round(subtotal + tax_amount + freight_amount, 2)

        # TODO: get next order number
        # order_number = _get_next_order_number(conn)
        order_number = _get_next_order_number(conn)
        order_date = datetime.date.today().isoformat()

        # TODO: insert into orders table
        # cur = conn.execute("INSERT INTO orders (...) VALUES (...)", (...))
        # order_id = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO orders "
            "(order_number, customer_id, order_date, required_date, status, "
            " ship_addr1, ship_city, ship_state, ship_zip, "
            " subtotal, tax_amount, freight_amount, total_amount, "
            " notes, entered_by, customer_po) "
            "VALUES (?, ?, ?, ?, 'OPEN', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                order_number, customer_id, order_date, payload['required_date'],
                payload['ship_addr1'], payload['ship_city'], payload['ship_state'], payload['ship_zip'],
                round(subtotal, 2), tax_amount, freight_amount, total_amount,
                payload['notes'], payload['entered_by'], payload['customer_po'],
            ),
        )
        order_id = cur.lastrowid

        # TODO: insert order lines
        # for line in prepared_lines:
        #     conn.execute("INSERT INTO order_lines (...) VALUES (...)", (...))
        for line in prepared_lines:
            conn.execute(
                "INSERT INTO order_lines "
                "(order_id, line_number, item_id, qty_ordered, qty_shipped, "
                " unit_price, discount_pct, line_total) "
                "VALUES (?, ?, ?, ?, 0.0, ?, ?, ?)",
                (
                    order_id, line['line_number'], line['item_id'],
                    line['qty_ordered'], line['unit_price'],
                    line['discount_pct'], line['line_total'],
                ),
            )
            conn.execute(
                "UPDATE inventory SET qty_reserved = qty_reserved + ? WHERE item_id = ?",
                (line['qty_ordered'], line['item_id']),
            )

        # TODO: commit
        # conn.commit()
        conn.commit()

        # TODO: return actual values
        # raise NotImplementedError(
        #     "create_order_in_db() is not yet implemented. "
        #     "This is the exercise: implement this function."
        # )
        return order_id, order_number

    finally:
        conn.close()


def get_order_from_db(order_id):
    """
    STRETCH GOAL: Implement this function.

    Fetch an order by ID. Return a dict suitable for JSON serialisation:
    {
        "order_id": int,
        "order_number": str,
        "customer_id": int,
        "order_date": str,
        "status": str,
        "total_amount": float,
        "lines": [
            {
                "line_number": int,
                "item_id": int,
                "sku": str,
                "description": str,
                "qty_ordered": float,
                "unit_price": float,
                "discount_pct": float,
                "line_total": float
            },
            ...
        ]
    }
    Return None if the order is not found.
    """
    # TODO: implement
    raise NotImplementedError("get_order_from_db() is not yet implemented (stretch goal).")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_create_order_payload(body):
    """Validate and normalise the POST /orders request body.
    Returns a cleaned payload dict or raises ValueError with a message.
    """
    if not isinstance(body, dict):
        raise ValueError("Request body must be a JSON object")

    customer_id = body.get('customer_id')
    if customer_id is None:
        raise ValueError("customer_id is required")
    if not isinstance(customer_id, int):
        try:
            customer_id = int(customer_id)
        except (ValueError, TypeError):
            raise ValueError("customer_id must be an integer")

    lines_raw = body.get('lines')
    if not lines_raw or not isinstance(lines_raw, list):
        raise ValueError("lines must be a non-empty array")

    validated_lines = []
    for i, line in enumerate(lines_raw):
        if not isinstance(line, dict):
            raise ValueError(f"lines[{i}] must be an object")

        item_id = line.get('item_id')
        if item_id is None:
            raise ValueError(f"lines[{i}].item_id is required")
        try:
            item_id = int(item_id)
        except (ValueError, TypeError):
            raise ValueError(f"lines[{i}].item_id must be an integer")

        qty = line.get('qty_ordered')
        if qty is None:
            raise ValueError(f"lines[{i}].qty_ordered is required")
        try:
            qty = float(qty)
        except (ValueError, TypeError):
            raise ValueError(f"lines[{i}].qty_ordered must be a number")
        if qty <= 0:
            raise ValueError(f"lines[{i}].qty_ordered must be positive")

        price = line.get('unit_price')
        if price is None:
            raise ValueError(f"lines[{i}].unit_price is required")
        try:
            price = float(price)
        except (ValueError, TypeError):
            raise ValueError(f"lines[{i}].unit_price must be a number")
        if price < 0:
            raise ValueError(f"lines[{i}].unit_price must be non-negative")

        discount = line.get('discount_pct', 0.0)
        try:
            discount = float(discount)
        except (ValueError, TypeError):
            raise ValueError(f"lines[{i}].discount_pct must be a number")

        validated_lines.append({
            'item_id':     item_id,
            'qty_ordered': qty,
            'unit_price':  price,
            'discount_pct':discount,
        })

    return {
        'customer_id':  customer_id,
        'required_date':body.get('required_date') or None,
        'ship_addr1':   str(body.get('ship_addr1', '') or ''),
        'ship_city':    str(body.get('ship_city', '') or ''),
        'ship_state':   str(body.get('ship_state', '') or ''),
        'ship_zip':     str(body.get('ship_zip', '') or ''),
        'customer_po':  str(body.get('customer_po', '') or ''),
        'notes':        str(body.get('notes', '') or ''),
        'entered_by':   str(body.get('entered_by', 'api') or 'api'),
        'lines':        validated_lines,
    }


# ---------------------------------------------------------------------------
# HTTP request handler
# ---------------------------------------------------------------------------

class OrdersHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Override to include a timestamp in the log line
        import datetime
        ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{ts}] {self.address_string()} {format % args}")

    def send_json(self, status_code, data):
        body = json.dumps(data, indent=2).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        length = int(self.headers.get('Content-Length', 0))
        if length == 0:
            return None
        raw = self.rfile.read(length)
        return json.loads(raw.decode('utf-8'))

    def do_GET(self):
        # Route: GET /orders/{id}
        if self.path.startswith('/orders/'):
            parts = self.path.split('/')
            if len(parts) == 3 and parts[2].isdigit():
                order_id = int(parts[2])
                try:
                    order = get_order_from_db(order_id)
                    if order is None:
                        self.send_json(404, {'error': f'Order {order_id} not found'})
                    else:
                        self.send_json(200, order)
                except NotImplementedError as e:
                    self.send_json(501, {'error': str(e)})
                except Exception as e:
                    self.send_json(500, {'error': str(e)})
                return

        # Route: GET /health (useful for verifying the server is up)
        if self.path == '/health':
            self.send_json(200, {'status': 'ok', 'service': 'orders-api'})
            return

        self.send_json(404, {'error': f'Not found: {self.path}'})

    def do_POST(self):
        # Route: POST /orders
        if self.path == '/orders':
            try:
                raw_body = self.read_json_body()
                if raw_body is None:
                    self.send_json(400, {'error': 'Request body is required'})
                    return

                payload = validate_create_order_payload(raw_body)
                order_id, order_number = create_order_in_db(payload)
                self.send_json(201, {
                    'order_id':     order_id,
                    'order_number': order_number,
                })

            except ValueError as e:
                self.send_json(400, {'error': str(e)})
            except NotImplementedError as e:
                self.send_json(501, {'error': str(e)})
            except json.JSONDecodeError as e:
                self.send_json(400, {'error': f'Invalid JSON: {e}'})
            except Exception as e:
                print(f"  ERROR: {e}", file=sys.stderr)
                self.send_json(500, {'error': 'Internal server error'})
            return

        self.send_json(404, {'error': f'Not found: {self.path}'})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    PORT = 8001
    server = HTTPServer(('localhost', PORT), OrdersHandler)
    print(f"Orders API listening on http://localhost:{PORT}")
    print(f"Using database: {os.path.abspath(DB_PATH)}")
    print()
    print("Available endpoints:")
    print(f"  POST http://localhost:{PORT}/orders        — create an order (EXERCISE)")
    print(f"  GET  http://localhost:{PORT}/orders/{{id}}  — get an order (stretch goal)")
    print(f"  GET  http://localhost:{PORT}/health        — health check")
    print()
    print("Press Ctrl+C to stop.")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
