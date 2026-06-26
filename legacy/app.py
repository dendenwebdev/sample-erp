#!/usr/bin/env python3
"""
app.py — Legacy ERP CLI Application

This is the "C++ desktop app" modelled in Python.
It mimics the behaviour of a 2-tier desktop ERP: no web layer,
the application connects directly to the SQLite database.

The code deliberately mirrors what 25-year-old C++ looks like:
- No abstraction beyond db.py (which is itself messy)
- UI logic and business decisions mixed together
- Input validation done inline with print statements
- Global state (the DB connection in db.py)

Run with: python3 app.py
"""

import json
import sys
import urllib.request

import db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clear():
    print("\n" + "=" * 60)


def prompt(label, default=None):
    if default is not None:
        val = input(f"  {label} [{default}]: ").strip()
        return val if val else default
    val = input(f"  {label}: ").strip()
    return val


def prompt_float(label, default=0.0):
    while True:
        raw = prompt(label, str(default))
        try:
            return float(raw)
        except ValueError:
            print("  ! Enter a number.")


def prompt_int(label):
    while True:
        raw = prompt(label)
        try:
            return int(raw)
        except ValueError:
            print("  ! Enter a whole number.")


# ---------------------------------------------------------------------------
# Customer screens
# ---------------------------------------------------------------------------

def screen_list_customers():
    clear()
    print("CUSTOMERS\n")
    rows = db.list_customers()
    if not rows:
        print("  (no customers)")
        return
    print(f"  {'ID':>4}  {'Code':<12}  {'Company':<30}  {'Contact':<20}  {'Active'}")
    print("  " + "-" * 80)
    for r in rows:
        active = "Yes" if r['is_active'] else "No"
        contact = r['contact_name'] or ""
        print(f"  {r['customer_id']:>4}  {r['cust_code']:<12}  {r['company_name']:<30}  {contact:<20}  {active}")


def screen_create_customer():
    clear()
    print("CREATE CUSTOMER\n")
    cust_code    = prompt("Customer code (e.g. ACME001)")
    company_name = prompt("Company name")
    contact_name = prompt("Contact name", "")
    contact_phone= prompt("Contact phone", "")
    contact_email= prompt("Contact email", "")
    billing_city = prompt("Billing city", "")
    billing_state= prompt("Billing state (2-letter)", "")
    credit_limit = prompt_float("Credit limit", 0.0)

    if not cust_code or not company_name:
        print("\n  ! Customer code and company name are required.")
        return

    try:
        cid = db.create_customer(
            cust_code, company_name, contact_name, contact_phone,
            contact_email, billing_city, billing_state, credit_limit
        )
        print(f"\n  Customer created. ID = {cid}")
    except Exception as e:
        print(f"\n  ! Error: {e}")


def menu_customers():
    while True:
        clear()
        print("CUSTOMERS\n")
        print("  1. List customers")
        print("  2. Create customer")
        print("  0. Back")
        choice = prompt("\nChoice")
        if choice == '1':
            screen_list_customers()
            input("\n  Press Enter to continue...")
        elif choice == '2':
            screen_create_customer()
            input("\n  Press Enter to continue...")
        elif choice == '0':
            break


# ---------------------------------------------------------------------------
# Inventory screens
# ---------------------------------------------------------------------------

def screen_list_inventory():
    clear()
    print("INVENTORY\n")
    rows = db.list_inventory()
    if not rows:
        print("  (no items)")
        return
    print(f"  {'ID':>4}  {'SKU':<18}  {'Description':<30}  {'UOM':<5}  {'On Hand':>8}  {'Reserved':>8}  {'Price':>8}")
    print("  " + "-" * 95)
    for r in rows:
        print(f"  {r['item_id']:>4}  {r['sku']:<18}  {r['description']:<30}  {r['unit_of_measure']:<5}  "
              f"  {r['qty_on_hand']:>8.1f}  {r['qty_reserved']:>8.1f}  {r['unit_price']:>8.2f}")


def screen_view_inventory_item():
    clear()
    print("VIEW INVENTORY ITEM\n")
    item_id = prompt_int("Item ID")
    item = db.get_inventory_item(item_id)
    if not item:
        print(f"  ! Item {item_id} not found.")
        return
    print()
    print(f"  SKU:            {item['sku']}")
    print(f"  Description:    {item['description']}")
    print(f"  Unit of Measure:{item['unit_of_measure']}")
    print(f"  On Hand:        {item['qty_on_hand']:.2f}")
    print(f"  Reserved:       {item['qty_reserved']:.2f}")
    print(f"  Available:      {item['qty_on_hand'] - item['qty_reserved']:.2f}")
    print(f"  Unit Cost:      ${item['unit_cost']:.2f}")
    print(f"  Unit Price:     ${item['unit_price']:.2f}")
    print(f"  Warehouse Loc:  {item['warehouse_loc'] or 'N/A'}")


def menu_inventory():
    while True:
        clear()
        print("INVENTORY\n")
        print("  1. List inventory")
        print("  2. View item detail")
        print("  0. Back")
        choice = prompt("\nChoice")
        if choice == '1':
            screen_list_inventory()
            input("\n  Press Enter to continue...")
        elif choice == '2':
            screen_view_inventory_item()
            input("\n  Press Enter to continue...")
        elif choice == '0':
            break


# ---------------------------------------------------------------------------
# Order screens
# ---------------------------------------------------------------------------

def screen_list_orders():
    clear()
    print("ORDERS\n")
    rows = db.list_orders()
    if not rows:
        print("  (no orders)")
        return
    print(f"  {'ID':>4}  {'Order #':<18}  {'Customer':<28}  {'Date':<12}  {'Status':<10}  {'Total':>10}")
    print("  " + "-" * 92)
    for r in rows:
        print(f"  {r['order_id']:>4}  {r['order_number']:<18}  {r['company_name']:<28}  "
              f"{r['order_date']:<12}  {r['status']:<10}  ${r['total_amount']:>9.2f}")


def screen_view_order():
    clear()
    print("VIEW ORDER\n")
    order_id = prompt_int("Order ID")
    order = db.get_order(order_id)
    if not order:
        print(f"  ! Order {order_id} not found.")
        return
    customer = db.get_customer(order['customer_id'])
    lines = db.get_order_lines(order_id)

    print()
    print(f"  Order Number:   {order['order_number']}")
    print(f"  Customer:       {customer['company_name'] if customer else 'UNKNOWN'}")
    print(f"  Order Date:     {order['order_date']}")
    print(f"  Required Date:  {order['required_date'] or 'N/A'}")
    print(f"  Status:         {order['status']}")
    print(f"  Customer PO:    {order['customer_po'] or 'N/A'}")
    print(f"  Entered By:     {order['entered_by'] or 'N/A'}")
    print()
    print(f"  Ship To:        {order['ship_addr1'] or ''}, {order['ship_city'] or ''}, "
          f"{order['ship_state'] or ''} {order['ship_zip'] or ''}")
    print()
    print(f"  {'#':>3}  {'SKU':<18}  {'Description':<28}  {'Qty':>6}  {'Price':>8}  {'Disc%':>5}  {'Total':>10}")
    print("  " + "-" * 88)
    for ln in lines:
        print(f"  {ln['line_number']:>3}  {ln['sku']:<18}  {ln['description']:<28}  "
              f"{ln['qty_ordered']:>6.1f}  ${ln['unit_price']:>7.2f}  {ln['discount_pct']:>4.1f}%  ${ln['line_total']:>9.2f}")
    print()
    print(f"  {'Subtotal:':>50}  ${order['subtotal']:>9.2f}")
    print(f"  {'Tax (8%):':>50}  ${order['tax_amount']:>9.2f}")
    print(f"  {'Freight:':>50}  ${order['freight_amount']:>9.2f}")
    print(f"  {'TOTAL:':>50}  ${order['total_amount']:>9.2f}")


def screen_create_order():
    """Create an order.

    THIS IS THE FUNCTION TO MODIFY IN THE EXERCISE.

    Currently it writes directly to the database via db.create_order().
    After strangling, it should call the Orders API instead.
    """
    clear()
    print("CREATE ORDER\n")

    # Show customers to pick from
    customers = db.list_customers()
    print("  Available customers:")
    for c in customers:
        if c['is_active']:
            print(f"    {c['customer_id']:>4}  {c['cust_code']:<12}  {c['company_name']}")
    print()

    customer_id = prompt_int("Customer ID")
    customer = db.get_customer(customer_id)
    if not customer:
        print(f"\n  ! Customer {customer_id} not found.")
        return
    if not customer['is_active']:
        print(f"\n  ! Customer '{customer['company_name']}' is inactive. Cannot create order.")
        return

    required_date = prompt("Required date (YYYY-MM-DD)", "")
    ship_addr1    = prompt("Ship address", customer['billing_addr1'] or "")
    ship_city     = prompt("Ship city",    customer['billing_city'] or "")
    ship_state    = prompt("Ship state",   customer['billing_state'] or "")
    ship_zip      = prompt("Ship ZIP",     customer['billing_zip'] or "")
    customer_po   = prompt("Customer PO #", "")
    notes         = prompt("Notes", "")
    entered_by    = prompt("Entered by", "clerk")

    # Line entry
    lines = []
    inventory = db.list_inventory()
    print("\n  Available inventory:")
    for item in inventory:
        avail = item['qty_on_hand'] - item['qty_reserved']
        print(f"    {item['item_id']:>4}  {item['sku']:<18}  {item['description']:<30}  "
              f"Avail: {avail:>6.1f}  Price: ${item['unit_price']:.2f}")

    print("\n  Enter order lines (enter 0 as Item ID to finish):")
    while True:
        print()
        item_id = prompt_int("  Item ID (0 to finish)")
        if item_id == 0:
            break
        item = db.get_inventory_item(item_id)
        if not item:
            print(f"    ! Item {item_id} not found.")
            continue

        qty = prompt_float(f"  Quantity (UOM: {item['unit_of_measure']})", 1.0)
        if qty <= 0:
            print("    ! Quantity must be positive.")
            continue

        price     = prompt_float("  Unit price", item['unit_price'])
        discount  = prompt_float("  Discount %", 0.0)

        lines.append({
            'item_id':     item_id,
            'qty_ordered': qty,
            'unit_price':  price,
            'discount_pct':discount,
        })
        line_total = qty * price * (1 - discount / 100.0)
        print(f"    Line total: ${line_total:.2f}")

    if not lines:
        print("\n  ! No lines entered. Order not created.")
        return

    try:
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
            method='POST',
        )
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))
        order_id = result['order_id']
        order_number = result['order_number']
        print(f"\n  Order created: {order_number} (ID {order_id})")
    except Exception as e:
        print(f"\n  ! Error creating order: {e}")


def menu_orders():
    while True:
        clear()
        print("ORDERS\n")
        print("  1. List orders")
        print("  2. View order detail")
        print("  3. Create order")
        print("  0. Back")
        choice = prompt("\nChoice")
        if choice == '1':
            screen_list_orders()
            input("\n  Press Enter to continue...")
        elif choice == '2':
            screen_view_order()
            input("\n  Press Enter to continue...")
        elif choice == '3':
            screen_create_order()
            input("\n  Press Enter to continue...")
        elif choice == '0':
            break


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def main():
    db.init_db()
    print("\nAcme ERP System v4.2.1")
    print("Legacy Edition — Copyright 1999-2024 Acme Corp")

    while True:
        clear()
        print("MAIN MENU\n")
        print("  1. Customers")
        print("  2. Inventory")
        print("  3. Orders")
        print("  0. Exit")
        choice = prompt("\nChoice")
        if choice == '1':
            menu_customers()
        elif choice == '2':
            menu_inventory()
        elif choice == '3':
            menu_orders()
        elif choice == '0':
            print("\nGoodbye.")
            sys.exit(0)


if __name__ == '__main__':
    main()
    rows = db.list_customers()
    if not rows:
        print("  (no customers)")
        return
    print(f"  {'ID':>4}  {'Code':<12}  {'Company':<30}  {'Contact':<20}  {'Active'}")
    print("  " + "-" * 80)
    for r in rows:
        active = "Yes" if r['is_active'] else "No"
        contact = r['contact_name'] or ""
        print(f"  {r['customer_id']:>4}  {r['cust_code']:<12}  {r['company_name']:<30}  {contact:<20}  {active}")


def screen_create_customer():
    clear()
    print("CREATE CUSTOMER\n")
    cust_code    = prompt("Customer code (e.g. ACME001)")
    company_name = prompt("Company name")
    contact_name = prompt("Contact name", "")
    contact_phone= prompt("Contact phone", "")
    contact_email= prompt("Contact email", "")
    billing_city = prompt("Billing city", "")
    billing_state= prompt("Billing state (2-letter)", "")
    credit_limit = prompt_float("Credit limit", 0.0)

    if not cust_code or not company_name:
        print("\n  ! Customer code and company name are required.")
        return

    try:
        cid = db.create_customer(
            cust_code, company_name, contact_name, contact_phone,
            contact_email, billing_city, billing_state, credit_limit
        )
        print(f"\n  Customer created. ID = {cid}")
    except Exception as e:
        print(f"\n  ! Error: {e}")


def menu_customers():
    while True:
        clear()
        print("CUSTOMERS\n")
        print("  1. List customers")
        print("  2. Create customer")
        print("  0. Back")
        choice = prompt("\nChoice")
        if choice == '1':
            screen_list_customers()
            input("\n  Press Enter to continue...")
        elif choice == '2':
            screen_create_customer()
            input("\n  Press Enter to continue...")
        elif choice == '0':
            break


# ---------------------------------------------------------------------------
# Inventory screens
# ---------------------------------------------------------------------------

def screen_list_inventory():
    clear()
    print("INVENTORY\n")
    rows = db.list_inventory()
    if not rows:
        print("  (no items)")
        return
    print(f"  {'ID':>4}  {'SKU':<18}  {'Description':<30}  {'UOM':<5}  {'On Hand':>8}  {'Reserved':>8}  {'Price':>8}")
    print("  " + "-" * 95)
    for r in rows:
        print(f"  {r['item_id']:>4}  {r['sku']:<18}  {r['description']:<30}  {r['unit_of_measure']:<5}  "
              f"  {r['qty_on_hand']:>8.1f}  {r['qty_reserved']:>8.1f}  {r['unit_price']:>8.2f}")


def screen_view_inventory_item():
    clear()
    print("VIEW INVENTORY ITEM\n")
    item_id = prompt_int("Item ID")
    item = db.get_inventory_item(item_id)
    if not item:
        print(f"  ! Item {item_id} not found.")
        return
    print()
    print(f"  SKU:            {item['sku']}")
    print(f"  Description:    {item['description']}")
    print(f"  Unit of Measure:{item['unit_of_measure']}")
    print(f"  On Hand:        {item['qty_on_hand']:.2f}")
    print(f"  Reserved:       {item['qty_reserved']:.2f}")
    print(f"  Available:      {item['qty_on_hand'] - item['qty_reserved']:.2f}")
    print(f"  Unit Cost:      ${item['unit_cost']:.2f}")
    print(f"  Unit Price:     ${item['unit_price']:.2f}")
    print(f"  Warehouse Loc:  {item['warehouse_loc'] or 'N/A'}")


def menu_inventory():
    while True:
        clear()
        print("INVENTORY\n")
        print("  1. List inventory")
        print("  2. View item detail")
        print("  0. Back")
        choice = prompt("\nChoice")
        if choice == '1':
            screen_list_inventory()
            input("\n  Press Enter to continue...")
        elif choice == '2':
            screen_view_inventory_item()
            input("\n  Press Enter to continue...")
        elif choice == '0':
            break


# ---------------------------------------------------------------------------
# Order screens
# ---------------------------------------------------------------------------

def screen_list_orders():
    clear()
    print("ORDERS\n")
    rows = db.list_orders()
    if not rows:
        print("  (no orders)")
        return
    print(f"  {'ID':>4}  {'Order #':<18}  {'Customer':<28}  {'Date':<12}  {'Status':<10}  {'Total':>10}")
    print("  " + "-" * 92)
    for r in rows:
        print(f"  {r['order_id']:>4}  {r['order_number']:<18}  {r['company_name']:<28}  "
              f"{r['order_date']:<12}  {r['status']:<10}  ${r['total_amount']:>9.2f}")


def screen_view_order():
    clear()
    print("VIEW ORDER\n")
    order_id = prompt_int("Order ID")
    order = db.get_order(order_id)
    if not order:
        print(f"  ! Order {order_id} not found.")
        return
    customer = db.get_customer(order['customer_id'])
    lines = db.get_order_lines(order_id)

    print()
    print(f"  Order Number:   {order['order_number']}")
    print(f"  Customer:       {customer['company_name'] if customer else 'UNKNOWN'}")
    print(f"  Order Date:     {order['order_date']}")
    print(f"  Required Date:  {order['required_date'] or 'N/A'}")
    print(f"  Status:         {order['status']}")
    print(f"  Customer PO:    {order['customer_po'] or 'N/A'}")
    print(f"  Entered By:     {order['entered_by'] or 'N/A'}")
    print()
    print(f"  Ship To:        {order['ship_addr1'] or ''}, {order['ship_city'] or ''}, "
          f"{order['ship_state'] or ''} {order['ship_zip'] or ''}")
    print()
    print(f"  {'#':>3}  {'SKU':<18}  {'Description':<28}  {'Qty':>6}  {'Price':>8}  {'Disc%':>5}  {'Total':>10}")
    print("  " + "-" * 88)
    for ln in lines:
        print(f"  {ln['line_number']:>3}  {ln['sku']:<18}  {ln['description']:<28}  "
              f"{ln['qty_ordered']:>6.1f}  ${ln['unit_price']:>7.2f}  {ln['discount_pct']:>4.1f}%  ${ln['line_total']:>9.2f}")
    print()
    print(f"  {'Subtotal:':>50}  ${order['subtotal']:>9.2f}")
    print(f"  {'Tax (8%):':>50}  ${order['tax_amount']:>9.2f}")
    print(f"  {'Freight:':>50}  ${order['freight_amount']:>9.2f}")
    print(f"  {'TOTAL:':>50}  ${order['total_amount']:>9.2f}")


def screen_create_order():
    """Create an order.

    THIS IS THE FUNCTION TO MODIFY IN THE EXERCISE.

    Currently it writes directly to the database via db.create_order().
    After strangling, it should call the Orders API instead.
    """
    clear()
    print("CREATE ORDER\n")

    # Show customers to pick from
    customers = db.list_customers()
    print("  Available customers:")
    for c in customers:
        if c['is_active']:
            print(f"    {c['customer_id']:>4}  {c['cust_code']:<12}  {c['company_name']}")
    print()

    customer_id = prompt_int("Customer ID")
    customer = db.get_customer(customer_id)
    if not customer:
        print(f"\n  ! Customer {customer_id} not found.")
        return
    if not customer['is_active']:
        print(f"\n  ! Customer '{customer['company_name']}' is inactive. Cannot create order.")
        return

    required_date = prompt("Required date (YYYY-MM-DD)", "")
    ship_addr1    = prompt("Ship address", customer['billing_addr1'] or "")
    ship_city     = prompt("Ship city",    customer['billing_city'] or "")
    ship_state    = prompt("Ship state",   customer['billing_state'] or "")
    ship_zip      = prompt("Ship ZIP",     customer['billing_zip'] or "")
    customer_po   = prompt("Customer PO #", "")
    notes         = prompt("Notes", "")
    entered_by    = prompt("Entered by", "clerk")

    # Line entry
    lines = []
    inventory = db.list_inventory()
    print("\n  Available inventory:")
    for item in inventory:
        avail = item['qty_on_hand'] - item['qty_reserved']
        print(f"    {item['item_id']:>4}  {item['sku']:<18}  {item['description']:<30}  "
              f"Avail: {avail:>6.1f}  Price: ${item['unit_price']:.2f}")

    print("\n  Enter order lines (enter 0 as Item ID to finish):")
    while True:
        print()
        item_id = prompt_int("  Item ID (0 to finish)")
        if item_id == 0:
            break
        item = db.get_inventory_item(item_id)
        if not item:
            print(f"    ! Item {item_id} not found.")
            continue

        qty = prompt_float(f"  Quantity (UOM: {item['unit_of_measure']})", 1.0)
        if qty <= 0:
            print("    ! Quantity must be positive.")
            continue

        price     = prompt_float("  Unit price", item['unit_price'])
        discount  = prompt_float("  Discount %", 0.0)

        lines.append({
            'item_id':     item_id,
            'qty_ordered': qty,
            'unit_price':  price,
            'discount_pct':discount,
        })
        line_total = qty * price * (1 - discount / 100.0)
        print(f"    Line total: ${line_total:.2f}")

    if not lines:
        print("\n  ! No lines entered. Order not created.")
        return

    # ---------------------------------------------------------------------------
    # STRANGLER FIG EXERCISE: THIS BLOCK IS WHAT YOU WILL REPLACE.
    #
    # Currently this calls db.create_order() directly.
    # After the exercise, this should call the Orders API via HTTP instead.
    #
    # The API call signature you're targeting:
    #   POST http://localhost:8001/orders
    #   Body (JSON): {
    #       "customer_id": int,
    #       "required_date": str,
    #       "ship_addr1": str,
    #       "ship_city": str,
    #       "ship_state": str,
    #       "ship_zip": str,
    #       "customer_po": str,
    #       "notes": str,
    #       "entered_by": str,
    #       "lines": [
    #           {"item_id": int, "qty_ordered": float,
    #            "unit_price": float, "discount_pct": float},
    #           ...
    #       ]
    #   }
    #   Response (JSON): {"order_id": int, "order_number": str}
    # ---------------------------------------------------------------------------
    try:
        order_id, order_number = db.create_order(
            customer_id=customer_id,
            required_date=required_date or None,
            ship_addr1=ship_addr1,
            ship_city=ship_city,
            ship_state=ship_state,
            ship_zip=ship_zip,
            notes=notes,
            entered_by=entered_by,
            customer_po=customer_po,
            lines=lines,
        )
        print(f"\n  Order created: {order_number} (ID {order_id})")
    except Exception as e:
        print(f"\n  ! Error creating order: {e}")
    # ---------------------------------------------------------------------------
    # END OF BLOCK TO REPLACE
    # ---------------------------------------------------------------------------


def menu_orders():
    while True:
        clear()
        print("ORDERS\n")
        print("  1. List orders")
        print("  2. View order detail")
        print("  3. Create order")
        print("  0. Back")
        choice = prompt("\nChoice")
        if choice == '1':
            screen_list_orders()
            input("\n  Press Enter to continue...")
        elif choice == '2':
            screen_view_order()
            input("\n  Press Enter to continue...")
        elif choice == '3':
            screen_create_order()
            input("\n  Press Enter to continue...")
        elif choice == '0':
            break


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def main():
    db.init_db()
    print("\nAcme ERP System v4.2.1")
    print("Legacy Edition — Copyright 1999-2024 Acme Corp")

    while True:
        clear()
        print("MAIN MENU\n")
        print("  1. Customers")
        print("  2. Inventory")
        print("  3. Orders")
        print("  0. Exit")
        choice = prompt("\nChoice")
        if choice == '1':
            menu_customers()
        elif choice == '2':
            menu_inventory()
        elif choice == '3':
            menu_orders()
        elif choice == '0':
            print("\nGoodbye.")
            sys.exit(0)


if __name__ == '__main__':
    main()
