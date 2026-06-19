-- Seed data: realistic ERP sample data
-- Mimics the kind of data a manufacturing/distribution company would have
-- after 25 years of operation.

-- Customers
INSERT INTO customers
    (cust_code, company_name, contact_name, contact_phone, contact_email,
     billing_addr1, billing_city, billing_state, billing_zip, credit_limit, created_date, is_active)
VALUES
    ('ACME001', 'Acme Industrial Supply Co.', 'Road Runner', '555-0101', 'runner@acme.example',
     '1 Acme Plaza', 'Phoenix', 'AZ', '85001', 50000.00, '2001-03-12', 1),
    ('GLOBX002', 'Global Exports Ltd.', 'Jane Thornton', '555-0202', 'j.thornton@globex.example',
     '42 Commerce Way', 'Chicago', 'IL', '60601', 100000.00, '2003-07-08', 1),
    ('MINIML03', 'Minimalist Manufacturing', 'Dan Park', '555-0303', 'dan@minimalist.example',
     '7 Lean St', 'Portland', 'OR', '97201', 25000.00, '2008-11-22', 1),
    ('RETRO004', 'Retrofit Solutions Inc.', 'Sandra Vega', '555-0404', 'svega@retrofit.example',
     '99 Old Town Rd', 'Nashville', 'TN', '37201', 75000.00, '2010-04-15', 1),
    ('DORMNT05', 'Dormant Corp (inactive)', NULL, NULL, NULL,
     NULL, NULL, NULL, NULL, 0.00, '2005-01-01', 0);

-- Inventory
INSERT INTO inventory
    (sku, description, unit_of_measure, qty_on_hand, qty_reserved, reorder_point,
     reorder_qty, unit_cost, unit_price, warehouse_loc, is_active)
VALUES
    ('BOLT-M8-SS',   'M8 Stainless Steel Hex Bolt (box/100)',  'BOX',  142.0, 12.0,  20.0, 50.0,   8.50,  14.99, 'A1-B01', 1),
    ('GASKET-NIT-L', 'Nitrile Gasket Set - Large',             'EA',    38.0,  4.0,  10.0, 25.0,  22.00,  39.99, 'A2-C04', 1),
    ('PUMP-CTF-3HP', 'Centrifugal Pump 3HP 230V',              'EA',     6.0,  2.0,   2.0,  5.0, 310.00, 599.00, 'B1-A01', 1),
    ('FILTER-OIL-5', 'Industrial Oil Filter #5',               'CASE',  89.0,  0.0,  15.0, 30.0,  18.00,  34.50, 'A3-B12', 1),
    ('SEAL-VITON-S', 'Viton O-Ring Seal - Small (pkg/50)',     'PKG',   55.0,  6.0,  12.0, 24.0,  11.25,  21.00, 'A1-C03', 1),
    ('HOSE-HYD-1IN', '1-inch Hydraulic Hose (per meter)',      'M',    200.0, 15.0,  50.0,100.0,   4.80,   9.50, 'C2-A05', 1),
    ('MTR-ELEC-1HP', 'Electric Motor 1HP TEFC',                'EA',     9.0,  1.0,   3.0,  6.0, 185.00, 349.00, 'B2-B02', 1),
    ('LUBE-GREASE-L','Multi-Purpose Grease - Large Tub',       'EA',    33.0,  0.0,   8.0, 16.0,  12.50,  24.99, 'A4-D01', 1);

-- Orders (a mix of statuses to simulate real ERP state)
-- Order 1: closed order from 2023
INSERT INTO orders
    (order_number, customer_id, order_date, required_date, shipped_date,
     status, ship_addr1, ship_city, ship_state, ship_zip,
     subtotal, tax_amount, freight_amount, total_amount, entered_by, customer_po)
VALUES
    ('ORD-2023-00001', 1, '2023-06-01', '2023-06-15', '2023-06-13',
     'CLOSED', '1 Acme Plaza', 'Phoenix', 'AZ', '85001',
     629.97, 50.40, 25.00, 705.37, 'admin', 'PO-ACME-8821');

INSERT INTO order_lines (order_id, line_number, item_id, qty_ordered, qty_shipped, unit_price, discount_pct, line_total)
VALUES
    (1, 1, 1, 10.0, 10.0, 14.99, 0.0, 149.90),
    (1, 2, 3,  1.0,  1.0, 599.00, 15.0, 509.15),  -- 15% discount applied
    (1, 3, 5,  2.0,  2.0, 21.00, 0.0, 42.00),      -- note: 149.90 + 509.15 - 21* ... messy rounding in legacy
    (1, 4, 8,  3.0,  3.0, 24.99, 0.0, 74.97);

-- Order 2: open order
INSERT INTO orders
    (order_number, customer_id, order_date, required_date, shipped_date,
     status, ship_addr1, ship_city, ship_state, ship_zip,
     subtotal, tax_amount, freight_amount, total_amount, entered_by, customer_po)
VALUES
    ('ORD-2024-00001', 2, '2024-01-10', '2024-01-24', NULL,
     'OPEN', '42 Commerce Way', 'Chicago', 'IL', '60601',
     1197.50, 95.80, 35.00, 1328.30, 'jsmith', 'GLOBX-2024-Q1-007');

INSERT INTO order_lines (order_id, line_number, item_id, qty_ordered, qty_shipped, unit_price, discount_pct, line_total)
VALUES
    (2, 1, 3,  2.0, 0.0, 599.00, 0.0, 1198.00),
    (2, 2, 4,  5.0, 0.0,  34.50, 0.0,  172.50);

-- Order 3: open order, small
INSERT INTO orders
    (order_number, customer_id, order_date, required_date, shipped_date,
     status, ship_addr1, ship_city, ship_state, ship_zip,
     subtotal, tax_amount, freight_amount, total_amount, entered_by)
VALUES
    ('ORD-2024-00002', 3, '2024-01-15', '2024-01-30', NULL,
     'OPEN', '7 Lean St', 'Portland', 'OR', '97201',
     189.50, 15.16, 15.00, 219.66, 'admin');

INSERT INTO order_lines (order_id, line_number, item_id, qty_ordered, qty_shipped, unit_price, discount_pct, line_total)
VALUES
    (3, 1, 2,  3.0, 0.0, 39.99, 0.0, 119.97),
    (3, 2, 5,  4.0, 0.0, 21.00, 5.0,  79.80);
