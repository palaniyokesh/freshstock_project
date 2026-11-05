"""
FreshStock AI - Database Layer & Store Management
Provides SQLite database initialization, models, queries, and sample store seeding.
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta

DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "freshstock.db"))

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(seed_if_empty=False):
    """Initializes SQLite tables without auto-seeding demo data."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS suppliers (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        contact_person TEXT,
        email TEXT,
        phone TEXT,
        lead_time_days INTEGER DEFAULT 2,
        category TEXT DEFAULT 'general',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        unit TEXT DEFAULT 'unit',
        cost_price REAL NOT NULL DEFAULT 0.0,
        selling_price REAL NOT NULL DEFAULT 0.0,
        weekly_sales_est INTEGER NOT NULL DEFAULT 7,
        lead_time_days INTEGER NOT NULL DEFAULT 2,
        pack_size INTEGER NOT NULL DEFAULT 1,
        safety_stock INTEGER NOT NULL DEFAULT 0,
        image_url TEXT,
        supplier_id TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT NOT NULL,
        batch_id TEXT NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 0,
        initial_quantity INTEGER NOT NULL DEFAULT 0,
        expiry_date TEXT,
        received_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active', -- 'active', 'expired', 'depleted'
        cost_price REAL NOT NULL DEFAULT 0.0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        unit_cost REAL NOT NULL,
        total_revenue REAL NOT NULL,
        total_profit REAL NOT NULL,
        batch_id TEXT,
        sale_date TEXT NOT NULL,
        notes TEXT,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS waste_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT NOT NULL,
        batch_id TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        cost_loss REAL NOT NULL,
        reason TEXT NOT NULL, -- 'expired', 'damaged', 'spoiled'
        logged_date TEXT NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    );
    """)
    conn.commit()

    if seed_if_empty:
        cursor.execute("SELECT COUNT(*) as count FROM products")
        if cursor.fetchone()["count"] == 0:
            seed_sample_data(conn)

    conn.close()

def clear_all_data(conn=None):
    """Completely wipes all products, batches, sales, suppliers, and waste logs."""
    should_close = False
    if conn is None:
        conn = get_db()
        should_close = True

    cursor = conn.cursor()
    cursor.execute("DELETE FROM waste_logs")
    cursor.execute("DELETE FROM sales")
    cursor.execute("DELETE FROM batches")
    cursor.execute("DELETE FROM products")
    cursor.execute("DELETE FROM suppliers")
    conn.commit()

    if should_close:
        conn.close()

def seed_sample_data(conn=None):
    """Populates realistic retail supermarket data with batches and 30 days of sales history."""
    should_close = False
    if conn is None:
        conn = get_db()
        should_close = True

    cursor = conn.cursor()

    # Clear existing
    cursor.execute("DELETE FROM waste_logs")
    cursor.execute("DELETE FROM sales")
    cursor.execute("DELETE FROM batches")
    cursor.execute("DELETE FROM products")
    cursor.execute("DELETE FROM suppliers")

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    # 1. Suppliers
    suppliers = [
        ("sup-dairy", "Heritage & Amul Dairy Co-op", "Ramesh Kumar", "orders@heritagedairy.in", "+91 98450 12345", 1, "fresh"),
        ("sup-farms", "Green Valley Fresh Produce", "Sunita Rao", "produce@greenvalleyfarms.com", "+91 98450 67890", 2, "fresh"),
        ("sup-staples", "Bharat Agri Staples & Grains", "Vikram Patel", "sales@bharatstaples.in", "+91 98200 45678", 4, "grocery"),
        ("sup-fmcg", "Apex Consumer Goods Dist.", "Anil Gupta", "supply@apexconsumer.com", "+91 98110 33445", 3, "household"),
        ("sup-bakery", "Daily Crust Artisanal Bakers", "Maria Joseph", "dispatch@dailycrust.in", "+91 98330 99887", 1, "bakery")
    ]

    for s in suppliers:
        cursor.execute("""
            INSERT INTO suppliers (id, name, contact_person, email, phone, lead_time_days, category, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (s[0], s[1], s[2], s[3], s[4], s[5], s[6], today_str))

    # 2. Products
    products = [
        {
            "id": "p-milk-500",
            "name": "Fresh Cow Milk (500 ml)",
            "category": "fresh",
            "unit": "packet",
            "cost_price": 28.0,
            "selling_price": 34.0,
            "weekly_sales_est": 140,
            "lead_time_days": 1,
            "pack_size": 12,
            "safety_stock": 20,
            "image_url": "https://images.unsplash.com/photo-1550583724-b2692b85b150?auto=format&fit=crop&w=160&q=80",
            "supplier_id": "sup-dairy",
            "batches": [
                {"lot": "LOT-MK-882", "qty": 35, "expiry_offset": 2, "received_offset": -1},
                {"lot": "LOT-MK-890", "qty": 40, "expiry_offset": 4, "received_offset": 0}
            ]
        },
        {
            "id": "p-mango-alphonso",
            "name": "Alphonso Mangoes (1 kg)",
            "category": "fresh",
            "unit": "kg",
            "cost_price": 320.0,
            "selling_price": 450.0,
            "weekly_sales_est": 42,
            "lead_time_days": 2,
            "pack_size": 5,
            "safety_stock": 10,
            "image_url": "https://images.unsplash.com/photo-1601493700631-2b16ec4b4716?auto=format&fit=crop&w=160&q=80",
            "supplier_id": "sup-farms",
            "batches": [
                {"lot": "LOT-MG-401", "qty": 18, "expiry_offset": 3, "received_offset": -2},
                {"lot": "LOT-MG-415", "qty": 25, "expiry_offset": 6, "received_offset": -1}
            ]
        },
        {
            "id": "p-basmati-5kg",
            "name": "Royal Basmati Rice (5 kg)",
            "category": "grocery",
            "unit": "bag",
            "cost_price": 490.0,
            "selling_price": 640.0,
            "weekly_sales_est": 28,
            "lead_time_days": 4,
            "pack_size": 4,
            "safety_stock": 12,
            "image_url": "https://images.unsplash.com/photo-1532629345422-7515f3d16bb6?auto=format&fit=crop&w=160&q=80",
            "supplier_id": "sup-staples",
            "batches": [
                {"lot": "LOT-RC-101", "qty": 22, "expiry_offset": 240, "received_offset": -14},
                {"lot": "LOT-RC-109", "qty": 30, "expiry_offset": 300, "received_offset": -3}
            ]
        },
        {
            "id": "p-sunflower-oil-1l",
            "name": "Pure Sunflower Oil (1 L)",
            "category": "grocery",
            "unit": "bottle",
            "cost_price": 125.0,
            "selling_price": 165.0,
            "weekly_sales_est": 56,
            "lead_time_days": 3,
            "pack_size": 10,
            "safety_stock": 15,
            "image_url": "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?auto=format&fit=crop&w=160&q=80",
            "supplier_id": "sup-staples",
            "batches": [
                {"lot": "LOT-OIL-55", "qty": 8, "expiry_offset": 120, "received_offset": -20}  # Low stock intentionally
            ]
        },
        {
            "id": "p-curd-400g",
            "name": "Farm Set Curd (400 g)",
            "category": "fresh",
            "unit": "tub",
            "cost_price": 32.0,
            "selling_price": 42.0,
            "weekly_sales_est": 70,
            "lead_time_days": 1,
            "pack_size": 10,
            "safety_stock": 12,
            "image_url": "https://images.unsplash.com/photo-1546173159-315724a31696?auto=format&fit=crop&w=160&q=80",
            "supplier_id": "sup-dairy",
            "batches": [
                {"lot": "LOT-CD-210", "qty": 14, "expiry_offset": 1, "received_offset": -4},
                {"lot": "LOT-CD-222", "qty": 28, "expiry_offset": 5, "received_offset": -1}
            ]
        },
        {
            "id": "p-whole-wheat-bread",
            "name": "Whole Wheat Bread Loaf (400 g)",
            "category": "bakery",
            "unit": "loaf",
            "cost_price": 35.0,
            "selling_price": 50.0,
            "weekly_sales_est": 63,
            "lead_time_days": 1,
            "pack_size": 6,
            "safety_stock": 8,
            "image_url": "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=160&q=80",
            "supplier_id": "sup-bakery",
            "batches": [
                {"lot": "LOT-BR-991", "qty": 5, "expiry_offset": -1, "received_offset": -5}, # Expired lot intentionally
                {"lot": "LOT-BR-995", "qty": 18, "expiry_offset": 2, "received_offset": 0}
            ]
        },
        {
            "id": "p-dishwash-gel-750ml",
            "name": "Sparkle Dishwash Liquid Gel (750 ml)",
            "category": "household",
            "unit": "bottle",
            "cost_price": 95.0,
            "selling_price": 139.0,
            "weekly_sales_est": 21,
            "lead_time_days": 4,
            "pack_size": 8,
            "safety_stock": 6,
            "image_url": "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?auto=format&fit=crop&w=160&q=80",
            "supplier_id": "sup-fmcg",
            "batches": [
                {"lot": "LOT-DW-33", "qty": 24, "expiry_offset": 450, "received_offset": -30}
            ]
        },
        {
            "id": "p-green-tea-100g",
            "name": "Organic Green Tea Leaves (100 g)",
            "category": "beverages",
            "unit": "box",
            "cost_price": 140.0,
            "selling_price": 210.0,
            "weekly_sales_est": 18,
            "lead_time_days": 3,
            "pack_size": 6,
            "safety_stock": 5,
            "image_url": "https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=160&q=80",
            "supplier_id": "sup-staples",
            "batches": [
                {"lot": "LOT-TEA-07", "qty": 15, "expiry_offset": 180, "received_offset": -15}
            ]
        }
    ]

    for p in products:
        cursor.execute("""
            INSERT INTO products (id, name, category, unit, cost_price, selling_price, weekly_sales_est,
                                 lead_time_days, pack_size, safety_stock, image_url, supplier_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (p["id"], p["name"], p["category"], p["unit"], p["cost_price"], p["selling_price"],
              p["weekly_sales_est"], p["lead_time_days"], p["pack_size"], p["safety_stock"],
              p["image_url"], p["supplier_id"], today_str))

        for b in p["batches"]:
            exp_date = (now + timedelta(days=b["expiry_offset"])).strftime("%Y-%m-%d")
            rec_date = (now + timedelta(days=b["received_offset"])).strftime("%Y-%m-%d")
            status = "expired" if b["expiry_offset"] < 0 else "active"
            cursor.execute("""
                INSERT INTO batches (product_id, batch_id, quantity, initial_quantity, expiry_date, received_date, status, cost_price, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (p["id"], b["lot"], b["qty"], b["qty"], exp_date, rec_date, status, p["cost_price"], today_str))

    # 3. Realistic Sales History (Last 30 days) to power revenue, margins, and forecasts
    for day_idx in range(30, -1, -1):
        sale_dt = now - timedelta(days=day_idx, hours=(day_idx * 3) % 12 + 8)
        sale_date_str = sale_dt.strftime("%Y-%m-%d %H:%M:%S")

        # Simulate sales across products with weekend uplift
        is_weekend = sale_dt.weekday() >= 5
        weekend_mult = 1.35 if is_weekend else 1.0

        for p in products:
            daily_base = p["weekly_sales_est"] / 7.0
            # Seasonal factor for fresh mangoes or curd
            season_mult = 1.3 if "mango" in p["id"] or "curd" in p["id"] else 1.0
            units_sold = max(0, round(daily_base * weekend_mult * season_mult * (0.85 + (day_idx % 4) * 0.1)))

            if units_sold > 0:
                rev = units_sold * p["selling_price"]
                cogs = units_sold * p["cost_price"]
                profit = rev - cogs
                cursor.execute("""
                    INSERT INTO sales (product_id, quantity, unit_price, unit_cost, total_revenue, total_profit, batch_id, sale_date, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (p["id"], units_sold, p["selling_price"], p["cost_price"], rev, profit, "POS-STORE", sale_date_str, "Store POS Checkout"))

    # 4. Sample Waste Log
    cursor.execute("""
        INSERT INTO waste_logs (product_id, batch_id, quantity, cost_loss, reason, logged_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("p-whole-wheat-bread", "LOT-BR-991", 5, 5 * 35.0, "expired", today_str))

    conn.commit()
    if should_close:
        conn.close()

# ----------------- Query Functions ----------------- #

def get_all_products(category="all", search=""):
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT p.*, s.name as supplier_name,
               COALESCE((SELECT SUM(b.quantity) FROM batches b WHERE b.product_id = p.id AND b.status = 'active'), 0) as total_stock,
               COALESCE((SELECT MIN(b.expiry_date) FROM batches b WHERE b.product_id = p.id AND b.status = 'active' AND b.expiry_date IS NOT NULL), NULL) as nearest_expiry
        FROM products p
        LEFT JOIN suppliers s ON p.supplier_id = s.id
        WHERE 1=1
    """
    params = []
    if category and category != "all":
        query += " AND p.category = ?"
        params.append(category)
    if search:
        query += " AND (p.name LIKE ? OR p.id LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY p.name ASC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]

    # Fetch active batches for each product
    for row in rows:
        cursor.execute("SELECT * FROM batches WHERE product_id = ? ORDER BY expiry_date ASC", (row["id"],))
        row["batches"] = [dict(b) for b in cursor.fetchall()]

    conn.close()
    return rows

def get_product(product_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, s.name as supplier_name,
               COALESCE((SELECT SUM(b.quantity) FROM batches b WHERE b.product_id = p.id AND b.status = 'active'), 0) as total_stock
        FROM products p
        LEFT JOIN suppliers s ON p.supplier_id = s.id
        WHERE p.id = ?
    """, (product_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    product = dict(row)
    cursor.execute("SELECT * FROM batches WHERE product_id = ? ORDER BY expiry_date ASC", (product_id,))
    product["batches"] = [dict(b) for b in cursor.fetchall()]
    conn.close()
    return product

def add_product(data):
    conn = get_db()
    cursor = conn.cursor()

    pid = data.get("id") or f"p-{int(datetime.now().timestamp())}"
    now_str = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        INSERT INTO products (id, name, category, unit, cost_price, selling_price, weekly_sales_est,
                             lead_time_days, pack_size, safety_stock, image_url, supplier_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        pid,
        data.get("name", "").strip(),
        data.get("category", "grocery"),
        data.get("unit", "unit"),
        float(data.get("cost_price", 0.0)),
        float(data.get("selling_price", 0.0) or float(data.get("cost_price", 0.0)) * 1.3),
        int(data.get("weekly_sales_est", 7)),
        int(data.get("lead_time_days", 2)),
        max(1, int(data.get("pack_size", 1))),
        max(0, int(data.get("safety_stock", 0))),
        data.get("image_url", ""),
        data.get("supplier_id"),
        now_str
    ))

    # Initial batch if opening stock > 0
    stock = int(data.get("stock", 0))
    if stock > 0:
        batch_id = data.get("batch_id") or f"LOT-{datetime.now().strftime('%m%d%H%M')}"
        expiry = data.get("expiry_date") or None
        received = data.get("received_date") or now_str
        cursor.execute("""
            INSERT INTO batches (product_id, batch_id, quantity, initial_quantity, expiry_date, received_date, status, cost_price, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)
        """, (pid, batch_id, stock, stock, expiry, received, float(data.get("cost_price", 0.0)), now_str))

    conn.commit()
    conn.close()
    return get_product(pid)

def update_product(product_id, data):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE products SET
            name = COALESCE(?, name),
            category = COALESCE(?, category),
            unit = COALESCE(?, unit),
            cost_price = COALESCE(?, cost_price),
            selling_price = COALESCE(?, selling_price),
            weekly_sales_est = COALESCE(?, weekly_sales_est),
            lead_time_days = COALESCE(?, lead_time_days),
            pack_size = COALESCE(?, pack_size),
            safety_stock = COALESCE(?, safety_stock),
            supplier_id = COALESCE(?, supplier_id)
        WHERE id = ?
    """, (
        data.get("name"),
        data.get("category"),
        data.get("unit"),
        data.get("cost_price"),
        data.get("selling_price"),
        data.get("weekly_sales_est"),
        data.get("lead_time_days"),
        data.get("pack_size"),
        data.get("safety_stock"),
        data.get("supplier_id"),
        product_id
    ))
    conn.commit()
    conn.close()
    return get_product(product_id)

def delete_product(product_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return True

# ----------------- Batches & Inventory Operations ----------------- #

def receive_batch(product_id, batch_id, quantity, expiry_date=None, received_date=None, cost_price=None):
    conn = get_db()
    cursor = conn.cursor()

    now_str = datetime.now().strftime("%Y-%m-%d")
    received_date = received_date or now_str
    batch_id = batch_id or f"LOT-{datetime.now().strftime('%m%d%H%M')}"

    # Get product cost price if not specified
    if cost_price is None:
        cursor.execute("SELECT cost_price FROM products WHERE id = ?", (product_id,))
        p = cursor.fetchone()
        cost_price = p["cost_price"] if p else 0.0

    cursor.execute("""
        INSERT INTO batches (product_id, batch_id, quantity, initial_quantity, expiry_date, received_date, status, cost_price, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)
    """, (product_id, batch_id, quantity, quantity, expiry_date, received_date, cost_price, now_str))

    batch_row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": batch_row_id, "batch_id": batch_id, "quantity": quantity, "product_id": product_id}

def record_sale_transaction(product_id, quantity, unit_price=None, notes=""):
    """
    Records a sale and applies FIFO stock deduction from oldest active unexpired batches.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    p = cursor.fetchone()
    if not p:
        conn.close()
        raise ValueError("Product not found")

    unit_price = float(unit_price if unit_price is not None else p["selling_price"])
    unit_cost = float(p["cost_price"])

    # Fetch active batches ordered by expiry date (FIFO)
    cursor.execute("""
        SELECT * FROM batches
        WHERE product_id = ? AND status = 'active' AND quantity > 0
        ORDER BY CASE WHEN expiry_date IS NULL THEN '9999-12-31' ELSE expiry_date END ASC
    """, (product_id,))
    active_batches = [dict(b) for b in cursor.fetchall()]

    total_avail = sum(b["quantity"] for b in active_batches)
    units_to_deduct = min(quantity, total_avail)

    remaining_deduct = units_to_deduct
    used_batch_ids = []

    for b in active_batches:
        take = min(b["quantity"], remaining_deduct)
        new_qty = b["quantity"] - take
        new_status = 'active' if new_qty > 0 else 'depleted'
        cursor.execute("UPDATE batches SET quantity = ?, status = ? WHERE id = ?", (new_qty, new_status, b["id"]))
        remaining_deduct -= take
        used_batch_ids.append(b["batch_id"])
        if remaining_deduct <= 0:
            break

    total_rev = units_to_deduct * unit_price
    total_profit = total_rev - (units_to_deduct * unit_cost)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO sales (product_id, quantity, unit_price, unit_cost, total_revenue, total_profit, batch_id, sale_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (product_id, units_to_deduct, unit_price, unit_cost, total_rev, total_profit,
          ", ".join(used_batch_ids) or "MANUAL", now_str, notes))

    conn.commit()
    conn.close()

    return {
        "product_id": product_id,
        "quantity_sold": units_to_deduct,
        "total_revenue": total_rev,
        "total_profit": total_profit,
        "sale_date": now_str
    }

def mark_batch_expired_or_waste(batch_id, reason="expired", quantity=None):
    """Marks a batch or portion of batch as expired / damaged, logging loss."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM batches WHERE id = ? OR batch_id = ?", (batch_id, batch_id))
    b = cursor.fetchone()
    if not b:
        conn.close()
        raise ValueError("Batch not found")

    qty_to_remove = int(quantity) if quantity is not None else b["quantity"]
    qty_to_remove = min(qty_to_remove, b["quantity"])

    new_qty = b["quantity"] - qty_to_remove
    new_status = "expired" if new_qty == 0 else "active"

    cursor.execute("UPDATE batches SET quantity = ?, status = ? WHERE id = ?", (new_qty, new_status, b["id"]))

    cost_loss = qty_to_remove * float(b["cost_price"])
    now_str = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        INSERT INTO waste_logs (product_id, batch_id, quantity, cost_loss, reason, logged_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (b["product_id"], b["batch_id"], qty_to_remove, cost_loss, reason, now_str))

    conn.commit()
    conn.close()
    return {"batch_id": b["batch_id"], "removed": qty_to_remove, "cost_loss": cost_loss}

def get_all_batches(status_filter="all"):
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT b.*, p.name as product_name, p.category, p.unit
        FROM batches b
        JOIN products p ON b.product_id = p.id
    """
    params = []
    if status_filter != "all":
        query += " WHERE b.status = ?"
        params.append(status_filter)

    query += " ORDER BY b.expiry_date ASC, b.id DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

# ----------------- Analytics, KPIs & Forecasting ----------------- #

def get_kpi_summary(period="30"):
    """
    Computes real store KPIs based on sales history and inventory status.
    period: 'today', '7', '30', 'all'
    """
    conn = get_db()
    cursor = conn.cursor()

    now = datetime.now()
    if period == "today":
        start_date = now.strftime("%Y-%m-%d 00:00:00")
    elif period == "7":
        start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d 00:00:00")
    elif period == "30":
        start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d 00:00:00")
    else:
        start_date = "2000-01-01 00:00:00"

    # Sales & Gross Margin
    cursor.execute("""
        SELECT COALESCE(SUM(total_revenue), 0) as revenue,
               COALESCE(SUM(total_profit), 0) as profit,
               COALESCE(SUM(quantity), 0) as units_sold
        FROM sales
        WHERE sale_date >= ?
    """, (start_date,))
    sales_data = cursor.fetchone()
    revenue = float(sales_data["revenue"])
    profit = float(sales_data["profit"])
    units_sold = int(sales_data["units_sold"])
    gross_margin = (profit / revenue * 100.0) if revenue > 0 else 0.0

    # Total Active Stock Value at cost price
    cursor.execute("""
        SELECT COALESCE(SUM(b.quantity * b.cost_price), 0) as inventory_value,
               COALESCE(SUM(b.quantity), 0) as total_units
        FROM batches b
        WHERE b.status = 'active'
    """)
    inv_data = cursor.fetchone()
    inventory_value = float(inv_data["inventory_value"])
    total_units = int(inv_data["total_units"])

    # Stockout risk (SKUs with stock <= ROP or days cover < 7)
    cursor.execute("""
        SELECT p.id, p.name, p.weekly_sales_est, p.lead_time_days, p.safety_stock,
               COALESCE((SELECT SUM(b.quantity) FROM batches b WHERE b.product_id = p.id AND b.status = 'active'), 0) as current_stock
        FROM products p
    """)
    products = cursor.fetchall()

    stockout_count = 0
    for p in products:
        daily = p["weekly_sales_est"] / 7.0
        days_cover = (p["current_stock"] / daily) if daily > 0 else 999
        reorder_point = int((daily * p["lead_time_days"]) + p["safety_stock"])
        if p["current_stock"] <= reorder_point or days_cover < 7:
            stockout_count += 1

    # Waste / Expiry Risk: active stock expiring in <= 7 days + already expired active stock
    seven_days_ahead = (now + timedelta(days=7)).strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT COALESCE(SUM(b.quantity * b.cost_price), 0) as at_risk_value,
               COALESCE(SUM(b.quantity), 0) as at_risk_units
        FROM batches b
        WHERE b.status = 'active' AND b.expiry_date IS NOT NULL AND b.expiry_date <= ? AND b.quantity > 0
    """, (seven_days_ahead,))
    risk_data = cursor.fetchone()
    waste_risk_value = float(risk_data["at_risk_value"])

    conn.close()

    return {
        "period": period,
        "revenue": revenue,
        "gross_margin": round(gross_margin, 1),
        "inventory_value": inventory_value,
        "stockout_risk_skus": stockout_count,
        "waste_risk_value": waste_risk_value,
        "units_sold": units_sold,
        "total_units": total_units
    }

def get_forecast_chart_data(category="all", horizon_days=14):
    """
    Returns actual daily sales for past 30 days and statistical 14-day demand forecast.
    Uses linear trend + 7-day cyclical seasonality indices.
    """
    conn = get_db()
    cursor = conn.cursor()

    now = datetime.now()
    thirty_days_ago = (now - timedelta(days=29)).strftime("%Y-%m-%d 00:00:00")

    query = """
        SELECT strftime('%Y-%m-%d', s.sale_date) as day,
               SUM(s.quantity) as total_qty,
               SUM(s.total_revenue) as total_rev
        FROM sales s
        JOIN products p ON s.product_id = p.id
        WHERE s.sale_date >= ?
    """
    params = [thirty_days_ago]
    if category != "all":
        query += " AND p.category = ?"
        params.append(category)

    query += " GROUP BY strftime('%Y-%m-%d', s.sale_date) ORDER BY day ASC"
    cursor.execute(query, params)
    sales_by_day = {r["day"]: float(r["total_qty"]) for r in cursor.fetchall()}

    # Fill full 30 days
    actual_labels = []
    actual_values = []
    for i in range(29, -1, -1):
        d_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        actual_labels.append(d_str)
        actual_values.append(sales_by_day.get(d_str, 0.0))

    # Calculate 7-day moving average and trend for forecasting
    if len(actual_values) > 0 and sum(actual_values) > 0:
        recent_avg = sum(actual_values[-7:]) / max(1, len(actual_values[-7:]))
    else:
        # Default baseline if fresh database without sales yet
        cursor.execute("SELECT SUM(weekly_sales_est) / 7.0 as daily_est FROM products" +
                       (" WHERE category = ?" if category != "all" else ""),
                       [category] if category != "all" else [])
        row = cursor.fetchone()
        recent_avg = float(row["daily_est"] or 20.0)

    # 14-day statistical projection with weekday seasonality
    forecast_labels = []
    forecast_values = []
    for j in range(1, horizon_days + 1):
        next_dt = now + timedelta(days=j)
        d_str = next_dt.strftime("%Y-%m-%d")
        # Weekend boost factor
        weekday_factor = 1.25 if next_dt.weekday() in [5, 6] else 0.95
        # Slight trend factor (+0.5% per week)
        trend = 1.0 + (j * 0.005)
        # Category seasonal lift (e.g., fresh / beverages in summer)
        cat_lift = 1.15 if category in ["fresh", "beverages"] else 1.0

        projected = round(recent_avg * weekday_factor * trend * cat_lift, 1)
        forecast_labels.append(d_str)
        forecast_values.append(projected)

    conn.close()

    return {
        "category": category,
        "actual": {
            "dates": actual_labels,
            "values": actual_values
        },
        "forecast": {
            "dates": forecast_labels,
            "values": forecast_values
        }
    }

def get_priority_alerts():
    """
    Computes priority alerts for low stock, impending expiry, and expired batches.
    """
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    soon_str = (now + timedelta(days=7)).strftime("%Y-%m-%d")

    alerts = []

    # 1. Expired Batches (High Severity)
    cursor.execute("""
        SELECT b.*, p.name as product_name
        FROM batches b
        JOIN products p ON b.product_id = p.id
        WHERE b.status = 'active' AND b.quantity > 0 AND b.expiry_date IS NOT NULL AND b.expiry_date < ?
    """, (today_str,))
    for row in cursor.fetchall():
        alerts.append({
            "type": "expired",
            "severity": "high",
            "title": f"Expired Batch: {row['product_name']}",
            "description": f"Batch {row['batch_id']} has {row['quantity']} units expired on {row['expiry_date']}. Immediate removal needed.",
            "product_id": row["product_id"],
            "batch_id": row["id"],
            "action": "Mark Expired"
        })

    # 2. Critical Stockouts / Zero Stock
    cursor.execute("""
        SELECT p.id, p.name,
               COALESCE((SELECT SUM(b.quantity) FROM batches b WHERE b.product_id = p.id AND b.status = 'active'), 0) as stock
        FROM products p
        WHERE (SELECT COALESCE(SUM(b.quantity), 0) FROM batches b WHERE b.product_id = p.id AND b.status = 'active') = 0
    """)
    for row in cursor.fetchall():
        alerts.append({
            "type": "out_of_stock",
            "severity": "high",
            "title": f"Out of Stock: {row['name']}",
            "description": "Inventory is completely depleted. Reorder from supplier immediately to prevent lost sales.",
            "product_id": row["id"],
            "action": "Receive Stock"
        })

    # 3. Low Stock / Approaching Reorder Point
    cursor.execute("""
        SELECT p.id, p.name, p.weekly_sales_est, p.lead_time_days, p.safety_stock, p.pack_size,
               COALESCE((SELECT SUM(b.quantity) FROM batches b WHERE b.product_id = p.id AND b.status = 'active'), 0) as stock
        FROM products p
    """)
    for row in cursor.fetchall():
        daily = row["weekly_sales_est"] / 7.0
        stock = row["stock"]
        if stock > 0 and daily > 0:
            days_cover = stock / daily
            rop = (daily * row["lead_time_days"]) + row["safety_stock"]
            if stock <= rop or days_cover <= 4:
                deficit = max(1, rop - stock + daily * 3)
                suggested_qty = max(row["pack_size"], int((deficit + row["pack_size"] - 1) // row["pack_size"]) * row["pack_size"])
                alerts.append({
                    "type": "low_stock",
                    "severity": "medium",
                    "title": f"Low Stock: {row['name']}",
                    "description": f"Only {stock} units left (~{days_cover:.1f} days cover, reorder point is {int(rop)} units). Suggested order: {suggested_qty} units.",
                    "product_id": row["id"],
                    "action": "Reorder"
                })

    # 4. Batches Expiring in <= 7 Days
    cursor.execute("""
        SELECT b.*, p.name as product_name
        FROM batches b
        JOIN products p ON b.product_id = p.id
        WHERE b.status = 'active' AND b.quantity > 0 AND b.expiry_date IS NOT NULL
          AND b.expiry_date >= ? AND b.expiry_date <= ?
        ORDER BY b.expiry_date ASC
    """, (today_str, soon_str))
    for row in cursor.fetchall():
        exp_dt = datetime.strptime(row["expiry_date"], "%Y-%m-%d")
        days_left = (exp_dt.date() - now.date()).days
        alerts.append({
            "type": "expiring_soon",
            "severity": "medium",
            "title": f"Expiring Soon: {row['product_name']}",
            "description": f"Batch {row['batch_id']} ({row['quantity']} units) expires in {days_left} day{'s' if days_left != 1 else ''} ({row['expiry_date']}). Consider promotional discount.",
            "product_id": row["product_id"],
            "batch_id": row["id"],
            "action": "View Batch"
        })

    conn.close()
    return alerts

# ----------------- Suppliers ----------------- #

def get_all_suppliers():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*,
               COUNT(p.id) as products_count
        FROM suppliers s
        LEFT JOIN products p ON s.id = p.supplier_id
        GROUP BY s.id
        ORDER BY s.name ASC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def add_supplier(data):
    conn = get_db()
    cursor = conn.cursor()
    sid = data.get("id") or f"sup-{int(datetime.now().timestamp())}"
    now_str = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        INSERT INTO suppliers (id, name, contact_person, email, phone, lead_time_days, category, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sid,
        data.get("name", "").strip(),
        data.get("contact_person", "").strip(),
        data.get("email", "").strip(),
        data.get("phone", "").strip(),
        int(data.get("lead_time_days", 2)),
        data.get("category", "general"),
        now_str
    ))
    conn.commit()
    conn.close()
    return {"id": sid, "name": data.get("name")}

def delete_supplier(supplier_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))
    conn.commit()
    conn.close()
    return True

# ----------------- Sales History ----------------- #

def get_sales_history(limit=50, category="all"):
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT s.*, p.name as product_name, p.category, p.unit
        FROM sales s
        JOIN products p ON s.product_id = p.id
    """
    params = []
    if category != "all":
        query += " WHERE p.category = ?"
        params.append(category)

    query += " ORDER BY s.sale_date DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
