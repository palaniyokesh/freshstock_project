"""
FreshStock AI - Production Flask Application
Provides RESTful APIs, inventory management, demand forecasting, and POS operations.
Ready for deployment on Render, Railway, Heroku, Docker, or standalone VPS.
"""

import os
import io
import csv
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file, Response, send_from_directory
from flask_cors import CORS
from config import config_by_name
import database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("FreshStock")

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development").lower()

    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates"
    )
    
    app_config = config_by_name.get(config_name, config_by_name["development"])
    app.config.from_object(app_config)

    # Enable CORS for API routes
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize Database
    with app.app_context():
        try:
            database.init_db(seed_if_empty=False)
            logger.info("Database initialized (clean empty state for supermarket owner).")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")

    # ------------------ Web Routes ------------------ #

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/health")
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "FreshStock AI Dashboard",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }), 200

    # ------------------ API Routes ------------------ #

    @app.route("/api/products", methods=["GET"])
    def get_products():
        category = request.args.get("category", "all")
        search = request.args.get("search", "")
        products = database.get_all_products(category=category, search=search)
        return jsonify({"success": True, "products": products, "count": len(products)})

    @app.route("/api/products/<product_id>", methods=["GET"])
    def get_single_product(product_id):
        product = database.get_product(product_id)
        if not product:
            return jsonify({"success": False, "error": "Product not found"}), 404
        return jsonify({"success": True, "product": product})

    @app.route("/api/products", methods=["POST"])
    def create_product():
        data = request.get_json() or {}
        if not data.get("name"):
            return jsonify({"success": False, "error": "Product name is required"}), 400

        try:
            new_prod = database.add_product(data)
            return jsonify({"success": True, "product": new_prod, "message": "Product created successfully"}), 201
        except Exception as e:
            logger.exception("Error adding product")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/products/<product_id>", methods=["PUT"])
    def update_product(product_id):
        data = request.get_json() or {}
        try:
            updated = database.update_product(product_id, data)
            if not updated:
                return jsonify({"success": False, "error": "Product not found"}), 404
            return jsonify({"success": True, "product": updated, "message": "Product updated successfully"})
        except Exception as e:
            logger.exception("Error updating product")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/products/<product_id>", methods=["DELETE"])
    def delete_product(product_id):
        try:
            success = database.delete_product(product_id)
            return jsonify({"success": True, "message": "Product deleted successfully"})
        except Exception as e:
            logger.exception("Error deleting product")
            return jsonify({"success": False, "error": str(e)}), 500

    # ------------------ Batches & Stock Management ------------------ #

    @app.route("/api/batches", methods=["GET"])
    def get_batches():
        status_filter = request.args.get("status", "all")
        batches = database.get_all_batches(status_filter=status_filter)
        return jsonify({"success": True, "batches": batches, "count": len(batches)})

    @app.route("/api/batches/receive", methods=["POST"])
    def receive_stock():
        data = request.get_json() or {}
        product_id = data.get("product_id")
        quantity = data.get("quantity")

        if not product_id or not quantity or int(quantity) <= 0:
            return jsonify({"success": False, "error": "Product ID and valid quantity > 0 are required"}), 400

        try:
            res = database.receive_batch(
                product_id=product_id,
                batch_id=data.get("batch_id"),
                quantity=int(quantity),
                expiry_date=data.get("expiry_date"),
                received_date=data.get("received_date"),
                cost_price=data.get("cost_price")
            )
            return jsonify({"success": True, "batch": res, "message": "Stock received successfully"}), 201
        except Exception as e:
            logger.exception("Error receiving stock")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/batches/expire", methods=["POST"])
    def expire_batch():
        data = request.get_json() or {}
        batch_id = data.get("batch_id")
        reason = data.get("reason", "expired")
        quantity = data.get("quantity")

        if not batch_id:
            return jsonify({"success": False, "error": "Batch ID is required"}), 400

        try:
            res = database.mark_batch_expired_or_waste(batch_id, reason=reason, quantity=quantity)
            return jsonify({"success": True, "result": res, "message": "Batch marked as expired/waste"})
        except Exception as e:
            logger.exception("Error marking batch expired")
            return jsonify({"success": False, "error": str(e)}), 500

    # ------------------ Sales & POS ------------------ #

    @app.route("/api/sales", methods=["GET"])
    def get_sales():
        limit = int(request.args.get("limit", 50))
        category = request.args.get("category", "all")
        sales = database.get_sales_history(limit=limit, category=category)
        return jsonify({"success": True, "sales": sales, "count": len(sales)})

    @app.route("/api/sales", methods=["POST"])
    def record_sale():
        data = request.get_json() or {}
        product_id = data.get("product_id")
        quantity = data.get("quantity")

        if not product_id or not quantity or int(quantity) <= 0:
            return jsonify({"success": False, "error": "Product ID and valid quantity > 0 are required"}), 400

        try:
            res = database.record_sale_transaction(
                product_id=product_id,
                quantity=int(quantity),
                unit_price=data.get("unit_price"),
                notes=data.get("notes", "POS Sale")
            )
            return jsonify({"success": True, "sale": res, "message": "Sale recorded and stock updated"}), 201
        except Exception as e:
            logger.exception("Error recording sale")
            return jsonify({"success": False, "error": str(e)}), 500

    # ------------------ KPIs & Analytics ------------------ #

    @app.route("/api/kpis", methods=["GET"])
    def get_kpis():
        period = request.args.get("period", "30")
        kpis = database.get_kpi_summary(period=period)
        return jsonify({"success": True, "kpis": kpis})

    @app.route("/api/forecast", methods=["GET"])
    def get_forecast():
        category = request.args.get("category", "all")
        horizon = int(request.args.get("days", 14))
        data = database.get_forecast_chart_data(category=category, horizon_days=horizon)
        return jsonify({"success": True, "forecast_data": data})

    @app.route("/api/alerts", methods=["GET"])
    def get_alerts():
        alerts = database.get_priority_alerts()
        return jsonify({"success": True, "alerts": alerts, "count": len(alerts)})

    # ------------------ Suppliers ------------------ #

    @app.route("/api/suppliers", methods=["GET"])
    def get_suppliers():
        suppliers = database.get_all_suppliers()
        return jsonify({"success": True, "suppliers": suppliers, "count": len(suppliers)})

    @app.route("/api/suppliers", methods=["POST"])
    def create_supplier():
        data = request.get_json() or {}
        if not data.get("name"):
            return jsonify({"success": False, "error": "Supplier name is required"}), 400
        try:
            sup = database.add_supplier(data)
            return jsonify({"success": True, "supplier": sup, "message": "Supplier created successfully"}), 201
        except Exception as e:
            logger.exception("Error adding supplier")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/suppliers/<supplier_id>", methods=["DELETE"])
    def delete_supplier(supplier_id):
        try:
            database.delete_supplier(supplier_id)
            return jsonify({"success": True, "message": "Supplier deleted successfully"})
        except Exception as e:
            logger.exception("Error deleting supplier")
            return jsonify({"success": False, "error": str(e)}), 500

    # ------------------ Smart Reorder Calculator ------------------ #

    @app.route("/api/calculator", methods=["POST"])
    def calculate_reorder():
        data = request.get_json() or {}
        try:
            daily = max(0.0, float(data.get("daily", 0.0)))
            stock = max(0.0, float(data.get("onhand", 0.0)))
            lead = max(0.0, float(data.get("lead", 0.0)))
            season_pct = float(data.get("season", 0.0))
            safety = max(0.0, float(data.get("safety", 0.0)))
            pack = max(1, int(data.get("pack", 1)))
            cost = max(0.0, float(data.get("cost", 0.0)))

            season_multiplier = 1.0 + (season_pct / 100.0)
            adjusted_daily = daily * season_multiplier
            # ROP = daily * (lead + safety)
            rop = int(round(adjusted_daily * (lead + safety)))
            needed = max(0, rop - int(stock))
            suggested_order = (int((needed + pack - 1) // pack) * pack) if needed > 0 else 0
            order_cost = suggested_order * cost

            return jsonify({
                "success": True,
                "adjusted_daily": round(adjusted_daily, 1),
                "reorder_point": rop,
                "suggested_order": suggested_order,
                "order_cost": round(order_cost, 2)
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    # ------------------ CSV Exports ------------------ #

    @app.route("/api/export/csv", methods=["GET"])
    def export_csv():
        products = database.get_all_products(category="all")
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Product ID", "Product Name", "Category", "Supplier", "Batch ID",
            "Batch Units", "Expiry Date", "Received Date", "Batch Status",
            "Weekly Sales Est", "Lead Time Days", "Unit Cost (INR)", "Batch Value (INR)"
        ])

        for p in products:
            if not p["batches"]:
                writer.writerow([
                    p["id"], p["name"], p["category"], p.get("supplier_name", ""),
                    "NO-BATCH", 0, "", "", "none",
                    p["weekly_sales_est"], p["lead_time_days"], p["cost_price"], 0.0
                ])
            else:
                for b in p["batches"]:
                    val = b["quantity"] * b["cost_price"]
                    writer.writerow([
                        p["id"], p["name"], p["category"], p.get("supplier_name", ""),
                        b["batch_id"], b["quantity"], b.get("expiry_date", ""),
                        b["received_date"], b["status"],
                        p["weekly_sales_est"], p["lead_time_days"], b["cost_price"], val
                    ])

        csv_bytes = output.getvalue().encode("utf-8")
        return Response(
            csv_bytes,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=freshstock-inventory-export.csv"}
        )

    @app.route("/api/export/sales-csv", methods=["GET"])
    def export_sales_csv():
        sales = database.get_sales_history(limit=1000)
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Sale ID", "Date", "Product ID", "Product Name", "Category",
            "Quantity", "Unit Price (INR)", "Unit Cost (INR)", "Revenue (INR)", "Profit (INR)", "Notes"
        ])

        for s in sales:
            writer.writerow([
                s["id"], s["sale_date"], s["product_id"], s["product_name"], s["category"],
                s["quantity"], s["unit_price"], s["unit_cost"], s["total_revenue"], s["total_profit"], s.get("notes", "")
            ])

        csv_bytes = output.getvalue().encode("utf-8")
        return Response(
            csv_bytes,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=freshstock-sales-report.csv"}
        )

    # ------------------ Admin Data Seeding / Reset ------------------ #

    @app.route("/api/admin/seed", methods=["POST"])
    def seed_data():
        try:
            database.seed_sample_data()
            return jsonify({"success": True, "message": "Sample supermarket dataset reloaded successfully"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/admin/clear", methods=["POST"])
    def clear_data():
        try:
            database.clear_all_data()
            return jsonify({"success": True, "message": "All inventory records cleared to fresh empty state for store owner"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # ------------------ Global Error Handlers ------------------ #

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Endpoint not found"}), 404
        return render_template("index.html"), 200

    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"Internal server error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

    return app

# WSGI Application entry point
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "development").lower() == "development"
    logger.info(f"Starting FreshStock AI on http://127.0.0.1:{port} (debug={debug})")
    app.run(host="0.0.0.0", port=port, debug=debug)
