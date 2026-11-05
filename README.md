# 🛒 FreshStock AI — Enterprise Supermarket Inventory & Forecasting Suite

**FreshStock AI** is a complete, production-ready retail inventory intelligence, demand forecasting, and Point-of-Sale (POS) management application. Powered by a high-performance **Python Flask** backend and SQLite/PostgreSQL-compatible data layer, it transforms the original single-page prototype into a robust multi-user system ready for immediate cloud or on-premise deployment.

---

## 🌟 Key Problems Solved (Upgrades from Prototype)

| Feature / Area | Original Prototype | FreshStock AI Production Suite |
| :--- | :--- | :--- |
| **Backend & Storage** | Ephemeral `localStorage` locked to one browser tab | **Persistent Python Flask RESTful backend** with SQLite/PostgreSQL schema |
| **Sales & POS** | No sales recorded; hardcoded `₹0` revenue and `—` margin | **Full POS transaction system** with FIFO batch stock deduction, gross profit tracking, and real margins |
| **Store KPIs** | Static dummy values; period filter reset to ₹0 | **Dynamic real-time KPI engine** (Revenue, Gross Margin %, Inventory Valuation, Stockout Risk SKUs, Expiry Waste Risk) |
| **Demand Forecasting** | Synthetic Math.sin() dummy curve | **Statistical 14-day demand forecast** based on past POS trends, weekday cycles, seasonal uplift indices, and confidence intervals |
| **Priority Alerts** | Hardcoded static alert that never updated | **Automated intelligent alert engine** monitoring expired lots, zero-stock items, critical ROP breaches, and lots expiring ≤ 7 days |
| **Navigation & Views** | Broken/missing views (`#sales`, `#suppliers`, `#reports` didn't exist) | **7 fully implemented workspace views** (Overview, Inventory, Demand Forecast, Sales POS, Warehouse & Batches, Suppliers, Reports, Calculator) |
| **User Experience (UX)** | Intrusive browser `prompt()` and `confirm()` dialogs | **Clean, accessible modal dialogs** with datepickers, validation, and toast notifications |
| **Data Export** | Basic client-side CSV | **Dual server-side & client-side CSV exports** (Full Inventory Valuation CSV, Sales & Margins CSV, and Print reports) |
| **Deployment** | Not deployable as a web service | **Docker, Docker Compose, Gunicorn, Procfile, and Render/Railway configs ready** |

---

## 🚀 Quick Start (Running Locally)

### 1. Prerequisites
- Python 3.9+ (Python 3.10, 3.11, 3.12, 3.13, 3.14 tested)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Flask Server
```bash
python app.py
```
*The server will start on [http://127.0.0.1:5000](http://127.0.0.1:5000).*  
Upon first launch, the database automatically initializes `freshstock.db` and pre-seeds sample retail supermarket data (Milk, Alphonso Mangoes, Basmati Rice, Sunflower Oil, Bread, Curd, Dishwash Gel, etc.) alongside 30 days of sales history.

### 4. Run Automated Tests
```bash
python -m unittest tests/test_app.py
```
*(Runs 8 comprehensive end-to-end unit tests covering all endpoints, FIFO stock deductions, KPIs, and calculators).*

---

## 🚢 Deployment Options

### Option A: Deploy to Render / Railway / Heroku
The repository includes a ready-to-use `Procfile`:
```procfile
web: gunicorn app:app --bind 0.0.0.0:$PORT
```
1. Push this repository to GitHub or GitLab.
2. In **Render** or **Railway**, create a new Web Service from your repository.
3. Select **Python** runtime. The platform will automatically detect `requirements.txt` and `Procfile`.
4. (Optional) Set environment variables:
   - `FLASK_ENV=production`
   - `SECRET_KEY=your-secure-random-key`

### Option B: Deploy with Docker
```bash
# Build Docker image
docker build -t freshstock-ai .

# Run container
docker run -d -p 5000:5000 --name freshstock freshstock-ai
```
Visit `http://localhost:5000` to access the dashboard.

### Option C: Deploy with Docker Compose
```bash
docker-compose up -d
```

### Option D: Traditional Linux VPS (Nginx + Gunicorn + Systemd)
1. Clone repo to `/var/www/freshstock`
2. Create Python virtualenv: `python3 -m venv venv && source venv/bin/activate`
3. Install: `pip install -r requirements.txt`
4. Setup systemd service pointing to:
   ```bash
   gunicorn --workers 3 --bind 127.0.0.1:5000 app:app
   ```
5. Proxy pass requests through Nginx:
   ```nginx
   server {
       listen 80;
       server_name your-store-domain.com;

       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       }
   }
   ```

---

## 📚 REST API Reference

All API routes return JSON and include standard HTTP status codes (`200 OK`, `201 Created`, `400 Bad Request`, `404 Not Found`, `500 Server Error`).

### Products
- `GET /api/products` — List all products with current stock, nearest expiry, and active batches.
  - Query parameters: `category` (e.g. `fresh`, `grocery`, `all`), `search` (query string).
- `GET /api/products/<id>` — Get single product details and batch breakdown.
- `POST /api/products` — Add new product and optional opening batch.
- `PUT /api/products/<id>` — Update product reorder parameters, safety stock, cost price, and prices.
- `DELETE /api/products/<id>` — Delete product.

### Stock & Batches
- `GET /api/batches` — List batches (status filter: `all`, `active`, `expired`).
- `POST /api/batches/receive` — Receive new stock batch:
  ```json
  {
    "product_id": "p-milk-500",
    "quantity": 24,
    "batch_id": "LOT-MK-991",
    "expiry_date": "2026-10-20",
    "received_date": "2026-10-13",
    "cost_price": 28.0
  }
  ```
- `POST /api/batches/expire` — Mark batch as expired/waste with reason (`expired`, `damaged`, `spoiled`).

### Sales & Point-of-Sale (POS)
- `GET /api/sales` — List recent checkout transactions (limit, category).
- `POST /api/sales` — Record checkout sale. Automatically deducts inventory from the oldest active batch (**FIFO**):
  ```json
  {
    "product_id": "p-milk-500",
    "quantity": 3,
    "unit_price": 34.0,
    "notes": "Counter 1 / UPI"
  }
  ```

### Analytics & AI Forecast
- `GET /api/kpis?period=today|7|30|all` — Live KPIs (revenue, gross margin %, inventory valuation, stockout risk SKUs, expiry waste risk value).
- `GET /api/forecast?category=fresh&days=14` — 30-day actual sales vs 14-day statistical projection with seasonal weighting.
- `GET /api/alerts` — Active priority alerts (expired batches, out-of-stock items, low stock ROP alerts, batches expiring ≤ 7 days).

### Suppliers
- `GET /api/suppliers` — Supplier directory with product counts and lead times.
- `POST /api/suppliers` — Register new supplier.
- `DELETE /api/suppliers/<id>` — Delete supplier.

### Reorder Calculator
- `POST /api/calculator` — Supply chain calculations:
  ```json
  {
    "daily": 18,
    "onhand": 42,
    "lead": 3,
    "season": 20,
    "safety": 3,
    "pack": 12,
    "cost": 45
  }
  ```
  Returns `adjusted_daily`, `reorder_point`, `suggested_order`, and `order_cost`.

### Exports & Backups
- `GET /api/export/csv` — Download complete inventory valuation CSV.
- `GET /api/export/sales-csv` — Download sales ledger and gross profit margins CSV.
- `POST /api/admin/seed` — Reload sample supermarket store data.
- `POST /api/admin/clear` — Reset store to fresh empty state.

---

## 🏗 Project Structure

```
freshstock_inventory/
├── app.py                  # Production Flask application & REST API routes
├── config.py               # Development, Production & Testing configs
├── database.py             # SQLite database layer, seed data & queries
├── requirements.txt        # Production dependencies (Flask, Gunicorn, CORS)
├── Procfile                # Heroku/Render/Railway deployment configuration
├── Dockerfile              # Multi-stage production container
├── docker-compose.yml      # Container orchestration
├── .env.example            # Environment variables template
├── .gitignore              # Ignored files
├── tests/
│   └── test_app.py         # Automated test suite
├── templates/
│   └── index.html          # Jinja2 / HTML5 Web Application template
└── static/
    ├── styles.css          # Modern CSS styling (responsive, modals, cards)
    └── script.js           # Client-side JavaScript controller & API sync
```

---

## 🔒 Security & Best Practices
- SQL Injection protection via parameterized queries throughout `database.py`.
- CORS configured for cross-origin API access if needed.
- FIFO inventory deduction guarantees consistent unit batch tracking.
- Standard health check endpoint `/health` for load balancers and orchestrators.
- Graceful client fallback: if Flask backend is restarting or opened via `file://`, the frontend displays offline status and preserves data locally.

---

## 📄 License
MIT License. Built for modern retail supermarket operations.
