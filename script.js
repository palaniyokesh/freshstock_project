/**
 * FreshStock AI - Client Controller
 * Connected with Python Flask RESTful Backend with graceful local fallback.
 */

// Global State
let products = [];
let suppliers = [];
let sales = [];
let currentCategory = "all";
let currentPeriod = "30";
let isBackendConnected = false;

// Helpers
function money(n) {
  return "₹" + Math.round(Number(n) || 0).toLocaleString("en-IN");
}

function escapeHTML(str) {
  return String(str ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function dayDiff(date) {
  if (!date) return null;
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const d = new Date(date + "T00:00:00");
  return Math.round((d - now) / 86400000);
}

function showToast(message, isError = false) {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast ${isError ? "error" : ""}`;
  toast.innerHTML = `<span>${isError ? "⚠" : "✓"}</span> <span>${escapeHTML(message)}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(40px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Modal Management
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add("active");
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove("active");
  }
}

// Check Backend Connection
async function checkBackend() {
  try {
    const res = await fetch("/health", { method: "GET" });
    if (res.ok) {
      isBackendConnected = true;
      const badge = document.getElementById("serverStatus");
      if (badge) {
        badge.innerHTML = `<span class="server-dot"></span> Backend: Flask Connected`;
        badge.title = "Connected to Python Flask SQLite database";
      }
      return true;
    }
  } catch (e) {
    isBackendConnected = false;
    const badge = document.getElementById("serverStatus");
    if (badge) {
      badge.innerHTML = `<span class="server-dot offline"></span> Offline Mode (Local)`;
      badge.title = "Running locally. Start Flask backend with 'python app.py'";
    }
  }
  return false;
}

// Tab Navigation
function setupNavigation() {
  const navLinks = document.querySelectorAll(".nav a, .quick-tab");
  navLinks.forEach(link => {
    link.addEventListener("click", e => {
      e.preventDefault();
      const targetId = link.getAttribute("href")?.replace("#", "");
      if (!targetId) return;
      switchTab(targetId);
    });
  });

  window.addEventListener("hashchange", () => {
    const hash = window.location.hash.replace("#", "");
    if (hash) switchTab(hash);
  });
}

function switchTab(tabId) {
  document.querySelectorAll(".view-panel").forEach(panel => {
    panel.classList.remove("active");
  });

  const targetPanel = document.getElementById("view-" + tabId) || document.getElementById(tabId);
  if (targetPanel) {
    targetPanel.classList.add("active");
  }

  document.querySelectorAll(".nav a").forEach(a => {
    if (a.getAttribute("href") === "#" + tabId) {
      a.classList.add("active");
    } else {
      a.classList.remove("active");
    }
  });

  // Update header eyebrow / subtitle
  const headerSub = {
    overview: "Supermarket executive overview, key metrics, and demand forecasting.",
    inventory: "Complete product inventory, stock levels, safety stock, and reorder planning.",
    forecast: "Statistical 14-day demand forecasting and seasonal uplift projections.",
    sales: "Point-of-sale checkout records, revenue performance, and gross profit margins.",
    warehouse: "Batch and lot tracking, expiry timelines, and FIFO inventory management.",
    suppliers: "Vendor directory, lead times, order tracking, and purchase management.",
    reports: "Audit-ready inventory valuation, sales reports, and CSV downloads.",
    calculator: "Smart reorder point, safety stock, and suggested order calculations."
  };

  const titles = {
    overview: "Supermarket Overview",
    inventory: "Inventory Intelligence",
    forecast: "Demand Forecast & AI Outlook",
    sales: "Sales Analytics & POS",
    warehouse: "Warehouse & Batch Manager",
    suppliers: "Suppliers & Vendor Management",
    reports: "Reports & Auditing",
    calculator: "Smart Reorder Settings"
  };

  const titleEl = document.getElementById("viewTitle");
  const subEl = document.getElementById("viewSubtitle");
  if (titleEl && titles[tabId]) titleEl.textContent = titles[tabId];
  if (subEl && headerSub[tabId]) subEl.textContent = headerSub[tabId];

  // Refresh relevant data
  if (tabId === "inventory") renderInventoryTable();
  if (tabId === "sales") loadSalesHistory();
  if (tabId === "warehouse") loadBatchesTable();
  if (tabId === "suppliers") loadSuppliers();
  if (tabId === "forecast") loadForecastChart();
}

// ------------------ Data Fetching ------------------ //

async function loadAllData() {
  await checkBackend();
  await Promise.all([
    loadProducts(),
    loadKPIs(),
    loadAlerts(),
    loadForecastChart(),
    loadSuppliers()
  ]);
}

async function loadProducts() {
  if (isBackendConnected) {
    try {
      const cat = document.getElementById("filterCategory")?.value || currentCategory || "all";
      const search = document.getElementById("searchInput")?.value || "";
      const res = await fetch(`/api/products?category=${encodeURIComponent(cat)}&search=${encodeURIComponent(search)}`);
      const data = await res.json();
      if (data.success) {
        products = data.products;
        renderInventoryTable();
        populateProductDropdowns();
        return;
      }
    } catch (e) {
      console.error("API error loading products", e);
    }
  }

  // Local fallback if backend unavailable
  try {
    const raw = localStorage.getItem("freshstock_owner_inventory_v3_empty");
    if (raw) products = JSON.parse(raw);
  } catch (e) {}
  renderInventoryTable();
}

async function loadKPIs() {
  const period = document.getElementById("periodSelect")?.value || currentPeriod;
  if (isBackendConnected) {
    try {
      const res = await fetch(`/api/kpis?period=${period}`);
      const data = await res.json();
      if (data.success) {
        const k = data.kpis;
        const revEl = document.getElementById("salesValue");
        const marginEl = document.getElementById("marginValue");
        const stockEl = document.getElementById("stockValue");
        const riskEl = document.getElementById("riskCount");
        const wasteEl = document.getElementById("wasteValue");

        if (revEl) revEl.textContent = money(k.revenue);
        if (marginEl) marginEl.textContent = k.revenue > 0 ? `${k.gross_margin}%` : "—";
        if (stockEl) stockEl.textContent = k.inventory_value >= 100000 ? (k.inventory_value / 100000).toFixed(2) + "L" : money(k.inventory_value);
        if (riskEl) riskEl.textContent = `${k.stockout_risk_skus} SKUs`;
        if (wasteEl) wasteEl.textContent = money(k.waste_risk_value);
        return;
      }
    } catch (e) {
      console.error("KPI fetch error", e);
    }
  }

  // Fallback calculation
  let val = products.reduce((s, p) => s + (p.total_stock || 0) * (p.cost_price || 0), 0);
  document.getElementById("stockValue").textContent = val >= 100000 ? (val / 100000).toFixed(2) + "L" : money(val);
}

async function loadAlerts() {
  const listEl = document.getElementById("alertList");
  const countEl = document.getElementById("alertCountBadge");
  if (!listEl) return;

  if (isBackendConnected) {
    try {
      const res = await fetch("/api/alerts");
      const data = await res.json();
      if (data.success && data.alerts) {
        const alerts = data.alerts;
        if (countEl) countEl.textContent = `${alerts.length} alert${alerts.length !== 1 ? "s" : ""}`;
        if (alerts.length === 0) {
          listEl.innerHTML = `
            <div class="alert">
              <div class="alert-symbol good">✓</div>
              <div><b>No product alerts</b><p>Stock levels and batch expiry dates look healthy.</p></div>
            </div>`;
          return;
        }

        listEl.innerHTML = alerts.map(a => {
          const isHigh = a.severity === "high";
          const symClass = isHigh ? "" : "amber";
          const sym = isHigh ? "⚠" : "!";
          return `
            <div class="alert">
              <div class="alert-symbol ${symClass}">${sym}</div>
              <div style="flex:1">
                <b>${escapeHTML(a.title)}</b>
                <p>${escapeHTML(a.description)}</p>
                <div class="alert-action">
                  ${a.type === 'expired' ? `<button class="btn sm danger" onclick="openExpireModal('${escapeHTML(a.batch_id)}')">Mark Expired</button>` :
                    a.type === 'out_of_stock' || a.type === 'low_stock' ? `<button class="btn sm primary" onclick="openReceiveModal('${escapeHTML(a.product_id)}')">＋ Receive Stock</button>` :
                    `<button class="btn sm" onclick="switchTab('warehouse')">Inspect Batch</button>`}
                </div>
              </div>
            </div>`;
        }).join("");
        return;
      }
    } catch (e) {
      console.error("Alerts error", e);
    }
  }

  listEl.innerHTML = `
    <div class="alert">
      <div class="alert-symbol good">✓</div>
      <div><b>Ready for products</b><p>Add products to enable automated stockout and expiry monitoring.</p></div>
    </div>`;
}

// ------------------ Demand Forecast Chart ------------------ //

async function loadForecastChart() {
  const svg = document.getElementById("salesChart");
  if (!svg) return;
  const category = document.getElementById("forecastCategory")?.value || "all";

  let actualValues = [];
  let forecastValues = [];
  let dates = [];

  if (isBackendConnected) {
    try {
      const res = await fetch(`/api/forecast?category=${category}&days=14`);
      const data = await res.json();
      if (data.success && data.forecast_data) {
        actualValues = data.forecast_data.actual.values;
        forecastValues = data.forecast_data.forecast.values;
        dates = data.forecast_data.actual.dates.concat(data.forecast_data.forecast.dates);
      }
    } catch (e) {
      console.error("Forecast fetch error", e);
    }
  }

  if (!actualValues.length) {
    // Graceful fallback dummy simulation
    actualValues = Array.from({ length: 30 }, (_, i) => 100 + Math.sin(i * 0.5) * 20);
    forecastValues = Array.from({ length: 14 }, (_, i) => 110 + Math.cos(i * 0.4) * 15);
  }

  const allVals = actualValues.concat(forecastValues);
  const max = Math.ceil(Math.max(...allVals, 10) * 1.15 / 10) * 10;
  const min = Math.max(0, Math.floor(Math.min(...allVals) * 0.8 / 10) * 10);

  const totalPoints = actualValues.length + forecastValues.length;
  const x = i => 42 + i * (630 / (totalPoints - 1));
  const y = v => 205 - ((v - min) / (max - min || 1)) * 165;

  let grid = "";
  for (let j = 0; j < 5; j++) {
    const yy = 40 + j * 41.25;
    const val = Math.round(max - j * (max - min) / 4);
    grid += `<line x1="40" y1="${yy}" x2="680" y2="${yy}" stroke="#edf1f4"/>
             <text x="32" y="${yy + 4}" text-anchor="end" fill="#96a1ad" font-size="10">${val}</text>`;
  }

  const actualPath = actualValues.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
  const forecastStartIndex = actualValues.length - 1;
  const combinedForecast = [actualValues[actualValues.length - 1], ...forecastValues];
  const forecastPath = combinedForecast.map((v, i) => `${i === 0 ? "M" : "L"}${x(forecastStartIndex + i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");

  // Confidence band
  const band = `M${x(forecastStartIndex)} ${y(combinedForecast[0] + 12)} ` +
    combinedForecast.map((v, i) => `L${x(forecastStartIndex + i)} ${y(v + 12)}`).join(" ") +
    ` ` + combinedForecast.slice().reverse().map((v, j) => `L${x(totalPoints - 1 - j)} ${y(v - 12)}`).join(" ") + " Z";

  const splitX = x(actualValues.length - 1);

  svg.innerHTML = `
    ${grid}
    <path d="${band}" fill="#f2a64a" opacity="0.14"/>
    <path d="${actualPath}" fill="none" stroke="#14866d" stroke-width="2.8" stroke-linejoin="round" stroke-linecap="round"/>
    <path d="${forecastPath}" fill="none" stroke="#f2a64a" stroke-width="2.8" stroke-dasharray="5 5" stroke-linejoin="round" stroke-linecap="round"/>
    <line x1="${splitX}" y1="35" x2="${splitX}" y2="205" stroke="#cbd5e1" stroke-dasharray="3 4"/>
    <text x="42" y="230" fill="#96a1ad" font-size="10">30 days ago</text>
    <text x="${splitX}" y="230" text-anchor="middle" fill="#14866d" font-weight="700" font-size="10">Today</text>
    <text x="675" y="230" text-anchor="end" fill="#f2a64a" font-weight="700" font-size="10">+14 days forecast</text>
  `;
}

// ------------------ Inventory Table ------------------ //

function renderInventoryTable() {
  const tbody = document.getElementById("inventoryRows");
  const tbodyFull = document.getElementById("inventoryRowsFull");
  if (!tbody && !tbodyFull) return;

  const cat = document.getElementById("filterCategory")?.value || "all";
  const search = (document.getElementById("searchInput")?.value || "").toLowerCase().trim();
  const statusFilter = document.getElementById("filterStatus")?.value || "all";

  const filtered = products.filter(p => {
    const matchCat = cat === "all" || p.category === cat;
    const matchSearch = !search || p.name.toLowerCase().includes(search) || (p.id && p.id.toLowerCase().includes(search));
    return matchCat && matchSearch;
  });

  if (filtered.length === 0) {
    const emptyHtml = `
      <tr>
        <td colspan="8" style="text-align:center;padding:40px 15px;color:#64748b">
          <div style="font-size:28px;margin-bottom:6px">📦</div>
          <b style="font-size:13px;color:var(--navy);display:block;margin-bottom:4px">Your Supermarket Inventory is Empty</b>
          <p style="font-size:11px;margin:0 0 14px;color:#8491a0">Add your own products and stock details using the form below to begin tracking inventory and expiry.</p>
          <button class="btn primary sm" onclick="document.getElementById('pName').focus(); document.getElementById('stockManager').scrollIntoView({behavior:'smooth'});">＋ Add Your First Product</button>
        </td>
      </tr>`;
    if (tbody) tbody.innerHTML = emptyHtml;
    if (tbodyFull) tbodyFull.innerHTML = emptyHtml;
    return;
  }

  const rowsHtml = filtered.map(p => {
    const qty = Number(p.total_stock ?? p.stock ?? 0);
    const daily = (Number(p.weekly_sales_est) || 7) / 7.0;
    const daysCover = daily > 0 ? (qty / daily) : Infinity;

    // Seasonal factor
    const season = p.name.toLowerCase().includes("mango") ? 1.32 : 1.08;
    const weeklyProj = Math.round(Number(p.weekly_sales_est || 7) * season);

    // Reorder Point & Suggested Order
    const rop = Math.ceil((daily * Number(p.lead_time_days || 2)) + Number(p.safety_stock || 0));
    const pack = Math.max(1, Number(p.pack_size || 1));
    const deficit = Math.max(0, rop - qty);
    const suggestedOrder = deficit > 0 ? Math.ceil(deficit / pack) * pack : 0;

    // Status Determination
    let statusText = "Healthy";
    let statusClass = "good";

    const hasExpired = (p.batches || []).some(b => b.status === "active" && b.expiry_date && dayDiff(b.expiry_date) < 0 && b.quantity > 0);
    const hasExpiringSoon = (p.batches || []).some(b => b.status === "active" && b.expiry_date && dayDiff(b.expiry_date) <= 7 && b.quantity > 0);

    if (hasExpired) {
      statusText = "Expiry check";
      statusClass = "low";
    } else if (qty === 0) {
      statusText = "Out of Stock";
      statusClass = "low";
    } else if (qty <= rop || daysCover < 3.5) {
      statusText = "Low stock";
      statusClass = "low";
    } else if (daysCover < 7 || hasExpiringSoon) {
      statusText = "Watch";
      statusClass = "watch";
    }

    // Expiry summary label
    let expiryHtml = '<span class="pill good">Dates look OK</span>';
    if (p.batches && p.batches.length > 0) {
      const activeBatches = p.batches.filter(b => b.status === "active" && b.quantity > 0);
      const expiredBatches = activeBatches.filter(b => b.expiry_date && dayDiff(b.expiry_date) < 0);
      const soonBatches = activeBatches.filter(b => b.expiry_date && dayDiff(b.expiry_date) >= 0 && dayDiff(b.expiry_date) <= 7);

      let pieces = [];
      if (expiredBatches.length > 0) {
        const expUnits = expiredBatches.reduce((sum, b) => sum + b.quantity, 0);
        pieces.push(`<span class="pill low">${expUnits} expired</span>`);
      }
      if (soonBatches.length > 0) {
        const soonUnits = soonBatches.reduce((sum, b) => sum + b.quantity, 0);
        pieces.push(`<span class="pill watch">${soonUnits} expiring soon</span>`);
      }
      if (p.nearest_expiry) {
        const diff = dayDiff(p.nearest_expiry);
        const diffText = diff < 0 ? "past date" : diff === 0 ? "today" : `${diff} days`;
        pieces.push(`<div style="font-size:10px;color:#64748b;margin-top:3px">Nearest: ${p.nearest_expiry} (${diffText})</div>`);
      }
      if (pieces.length > 0) expiryHtml = pieces.join(" ");
    }

    const defaultImg = "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=160&q=80";

    return `
      <tr>
        <td>
          <div class="product">
            <img src="${escapeHTML(p.image_url || defaultImg)}" alt="" onerror="this.src='${defaultImg}'">
            <div>
              <b>${escapeHTML(p.name)}</b>
              <div class="card-sub">${escapeHTML(p.category || "grocery")} • ₹${Number(p.cost_price || 0).toFixed(0)} cost</div>
            </div>
          </div>
        </td>
        <td><b>${qty}</b> <small style="color:#8491a0">${escapeHTML(p.unit || 'units')}</small></td>
        <td>${weeklyProj}</td>
        <td>${Number.isFinite(daysCover) ? daysCover.toFixed(1) : "—"}</td>
        <td><b>${suggestedOrder}</b></td>
        <td><div class="expiry-text">${expiryHtml}</div></td>
        <td><span class="pill ${statusClass}">${statusText}</span></td>
        <td>
          <div class="owner-actions">
            <button class="receive" onclick="openReceiveModal('${escapeHTML(p.id)}')">＋ Receive</button>
            <button class="sell" onclick="openSaleModal('${escapeHTML(p.id)}')">↗ Sell</button>
            <button class="expired" onclick="openExpireProductModal('${escapeHTML(p.id)}')">⚠ Expire</button>
            <button onclick="openEditModal('${escapeHTML(p.id)}')">✎ Edit</button>
          </div>
        </td>
      </tr>
    `;
  }).join("");

  if (tbody) tbody.innerHTML = rowsHtml;
  if (tbodyFull) tbodyFull.innerHTML = rowsHtml;
}

// ------------------ Modals & Actions ------------------ //

function populateProductDropdowns() {
  const options = products.map(p => `<option value="${escapeHTML(p.id)}">${escapeHTML(p.name)} (${p.total_stock || 0} in stock)</option>`).join("");
  const receiveSelect = document.getElementById("modalReceiveProduct");
  const saleSelect = document.getElementById("modalSaleProduct");
  const editSelect = document.getElementById("editProductId");

  if (receiveSelect) receiveSelect.innerHTML = options;
  if (saleSelect) saleSelect.innerHTML = options;
  if (editSelect) editSelect.innerHTML = options;
}

function openReceiveModal(productId) {
  const select = document.getElementById("modalReceiveProduct");
  if (select && productId) select.value = productId;
  document.getElementById("modalReceiveDate").value = todayISO();
  document.getElementById("modalReceiveLot").value = "LOT-" + Date.now().toString().slice(-6);
  document.getElementById("modalReceiveQty").value = "10";
  openModal("receiveModal");
}

async function handleReceiveSubmit(e) {
  e.preventDefault();
  const pid = document.getElementById("modalReceiveProduct").value;
  const qty = Number(document.getElementById("modalReceiveQty").value);
  const lot = document.getElementById("modalReceiveLot").value.trim();
  const expiry = document.getElementById("modalReceiveExpiry").value || null;
  const recDate = document.getElementById("modalReceiveDate").value || todayISO();

  if (!pid || qty <= 0) {
    showToast("Please select product and positive quantity.", true);
    return;
  }

  if (isBackendConnected) {
    try {
      const res = await fetch("/api/batches/receive", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: pid, quantity: qty, batch_id: lot, expiry_date: expiry, received_date: recDate })
      });
      const data = await res.json();
      if (data.success) {
        showToast(`Stock received: +${qty} units added!`);
        closeModal("receiveModal");
        await loadAllData();
        return;
      }
    } catch (err) {
      showToast("Error connecting to server", true);
    }
  }

  // Local fallback
  const prod = products.find(p => p.id === pid);
  if (prod) {
    prod.batches = prod.batches || [];
    prod.batches.push({ id: lot, batch_id: lot, quantity: qty, expiry_date: expiry, received_date: recDate, status: "active" });
    prod.total_stock = (prod.total_stock || 0) + qty;
    saveLocalProducts();
    showToast(`Stock received locally (+${qty} units)`);
    closeModal("receiveModal");
    renderInventoryTable();
    loadKPIs();
  }
}

function openSaleModal(productId) {
  const select = document.getElementById("modalSaleProduct");
  if (select && productId) {
    select.value = productId;
    onSaleProductChange();
  }
  openModal("saleModal");
}

function onSaleProductChange() {
  const select = document.getElementById("modalSaleProduct");
  const pid = select?.value;
  const prod = products.find(p => p.id === pid);
  const priceInput = document.getElementById("modalSalePrice");
  if (prod && priceInput) {
    priceInput.value = prod.selling_price || Math.round(Number(prod.cost_price || 0) * 1.3);
  }
}

async function handleSaleSubmit(e) {
  e.preventDefault();
  const pid = document.getElementById("modalSaleProduct").value;
  const qty = Number(document.getElementById("modalSaleQty").value);
  const price = Number(document.getElementById("modalSalePrice").value);
  const notes = document.getElementById("modalSaleNotes").value || "Store Sale";

  if (!pid || qty <= 0) {
    showToast("Please enter valid quantity", true);
    return;
  }

  if (isBackendConnected) {
    try {
      const res = await fetch("/api/sales", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: pid, quantity: qty, unit_price: price, notes })
      });
      const data = await res.json();
      if (data.success) {
        showToast(`Sale recorded! Revenue: ₹${data.sale.total_revenue}`);
        closeModal("saleModal");
        await loadAllData();
        return;
      } else {
        showToast(data.error || "Could not complete sale", true);
      }
    } catch (err) {
      showToast("Connection error while recording sale", true);
    }
  }

  // Local fallback
  const prod = products.find(p => p.id === pid);
  if (prod) {
    prod.total_stock = Math.max(0, (prod.total_stock || 0) - qty);
    saveLocalProducts();
    showToast(`Sale recorded locally (-${qty} units)`);
    closeModal("saleModal");
    renderInventoryTable();
    loadKPIs();
  }
}

function openExpireProductModal(productId) {
  const prod = products.find(p => p.id === productId);
  if (!prod) return;
  const activeBatches = (prod.batches || []).filter(b => b.status === "active" && b.quantity > 0);
  if (!activeBatches.length) {
    showToast("No active batches found for this product.", true);
    return;
  }
  openExpireModal(activeBatches[0].id || activeBatches[0].batch_id);
}

function openExpireModal(batchId) {
  document.getElementById("modalExpireBatchId").value = batchId;
  document.getElementById("modalExpireReason").value = "expired";
  openModal("expireModal");
}

async function handleExpireSubmit(e) {
  e.preventDefault();
  const batchId = document.getElementById("modalExpireBatchId").value;
  const reason = document.getElementById("modalExpireReason").value;
  const qty = document.getElementById("modalExpireQty").value ? Number(document.getElementById("modalExpireQty").value) : null;

  if (isBackendConnected) {
    try {
      const res = await fetch("/api/batches/expire", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ batch_id: batchId, reason, quantity: qty })
      });
      const data = await res.json();
      if (data.success) {
        showToast(`Batch marked as ${reason}. Loss: ₹${data.result.cost_loss}`);
        closeModal("expireModal");
        await loadAllData();
        return;
      }
    } catch (err) {
      showToast("Server error marking batch", true);
    }
  }

  showToast("Batch marked locally");
  closeModal("expireModal");
}

// ------------------ New Product Form ------------------ //

async function handleNewProductSubmit(e) {
  e.preventDefault();
  const name = document.getElementById("pName").value.trim();
  const cat = document.getElementById("pCategory").value;
  const stock = Number(document.getElementById("pStock").value);
  const weekly = Number(document.getElementById("pWeekly").value);
  const cost = Number(document.getElementById("pCost").value);
  const lead = Number(document.getElementById("pLead").value);
  const pack = Number(document.getElementById("pPack").value);
  const safety = Number(document.getElementById("pMin").value);
  const lot = document.getElementById("pBatch").value.trim();
  const expiry = document.getElementById("pExpiry").value || null;
  const received = document.getElementById("pReceived").value || todayISO();

  if (!name || cost < 0 || weekly < 0) {
    showToast("Please check numeric fields.", true);
    return;
  }

  const payload = {
    name,
    category: cat,
    cost_price: cost,
    selling_price: Math.round(cost * 1.35),
    stock,
    weekly_sales_est: weekly,
    lead_time_days: lead,
    pack_size: pack,
    safety_stock: safety,
    batch_id: lot || "LOT-" + Date.now().toString().slice(-6),
    expiry_date: expiry,
    received_date: received
  };

  if (isBackendConnected) {
    try {
      const res = await fetch("/api/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success) {
        showToast(`Product "${name}" added successfully!`);
        document.getElementById("productForm").reset();
        await loadAllData();
        return;
      }
    } catch (e) {
      showToast("Server error saving product", true);
    }
  }

  // Local fallback
  payload.id = "p-" + Date.now();
  payload.total_stock = stock;
  payload.batches = stock > 0 ? [{ id: payload.batch_id, batch_id: payload.batch_id, quantity: stock, expiry_date: expiry, status: "active" }] : [];
  products.push(payload);
  saveLocalProducts();
  showToast(`Product saved locally.`);
  document.getElementById("productForm").reset();
  renderInventoryTable();
  loadKPIs();
}

function saveLocalProducts() {
  try {
    localStorage.setItem("freshstock_owner_inventory_v3_empty", JSON.stringify(products));
  } catch (e) {}
}

// ------------------ Edit Product Modal ------------------ //

function openEditModal(productId) {
  const prod = products.find(p => p.id === productId);
  if (!prod) return;

  document.getElementById("editProdId").value = prod.id;
  document.getElementById("editProdName").value = prod.name;
  document.getElementById("editProdCategory").value = prod.category || "grocery";
  document.getElementById("editProdCost").value = prod.cost_price || 0;
  document.getElementById("editProdPrice").value = prod.selling_price || 0;
  document.getElementById("editProdWeekly").value = prod.weekly_sales_est || 7;
  document.getElementById("editProdLead").value = prod.lead_time_days || 2;
  document.getElementById("editProdPack").value = prod.pack_size || 1;
  document.getElementById("editProdSafety").value = prod.safety_stock || 0;

  openModal("editProductModal");
}

async function handleEditProductSubmit(e) {
  e.preventDefault();
  const pid = document.getElementById("editProdId").value;
  const payload = {
    name: document.getElementById("editProdName").value.trim(),
    category: document.getElementById("editProdCategory").value,
    cost_price: Number(document.getElementById("editProdCost").value),
    selling_price: Number(document.getElementById("editProdPrice").value),
    weekly_sales_est: Number(document.getElementById("editProdWeekly").value),
    lead_time_days: Number(document.getElementById("editProdLead").value),
    pack_size: Number(document.getElementById("editProdPack").value),
    safety_stock: Number(document.getElementById("editProdSafety").value)
  };

  if (isBackendConnected) {
    try {
      const res = await fetch(`/api/products/${pid}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success) {
        showToast("Product updated successfully!");
        closeModal("editProductModal");
        await loadAllData();
        return;
      }
    } catch (e) {
      showToast("Server error updating product", true);
    }
  }

  // Fallback
  const prod = products.find(p => p.id === pid);
  if (prod) {
    Object.assign(prod, payload);
    saveLocalProducts();
    showToast("Product updated locally");
    closeModal("editProductModal");
    renderInventoryTable();
  }
}

// ------------------ Warehouse & Batches View ------------------ //

async function loadBatchesTable() {
  const tbody = document.getElementById("warehouseRows");
  if (!tbody) return;

  if (isBackendConnected) {
    try {
      const status = document.getElementById("warehouseStatusFilter")?.value || "all";
      const res = await fetch(`/api/batches?status=${status}`);
      const data = await res.json();
      if (data.success && data.batches) {
        renderBatchesList(data.batches);
        return;
      }
    } catch (e) {
      console.error("Batches error", e);
    }
  }

  // Fallback
  const allBatches = products.flatMap(p => (p.batches || []).map(b => ({
    ...b,
    product_name: p.name,
    category: p.category,
    unit: p.unit
  })));
  renderBatchesList(allBatches);
}

function renderBatchesList(batches) {
  const tbody = document.getElementById("warehouseRows");
  if (!tbody) return;

  if (batches.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:24px;color:#94a3b8">No batches recorded yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = batches.map(b => {
    const diff = dayDiff(b.expiry_date);
    let diffBadge = '<span class="pill good">Valid</span>';
    if (diff !== null) {
      if (diff < 0) diffBadge = `<span class="pill low">${Math.abs(diff)}d EXPIRED</span>`;
      else if (diff <= 3) diffBadge = `<span class="pill low">${diff}d LEFT</span>`;
      else if (diff <= 7) diffBadge = `<span class="pill watch">${diff}d LEFT</span>`;
      else diffBadge = `<span class="pill good">${diff} days</span>`;
    }

    const val = Number(b.quantity || 0) * Number(b.cost_price || 0);

    return `
      <tr>
        <td><b>${escapeHTML(b.batch_id)}</b></td>
        <td>${escapeHTML(b.product_name)}</td>
        <td><b>${b.quantity}</b> ${escapeHTML(b.unit || '')}</td>
        <td>${escapeHTML(b.expiry_date || 'None')}</td>
        <td>${diffBadge}</td>
        <td>${escapeHTML(b.received_date || '—')}</td>
        <td>${money(val)}</td>
        <td><span class="pill ${b.status === 'active' ? 'good' : 'low'}">${b.status}</span></td>
      </tr>
    `;
  }).join("");
}

// ------------------ Sales Analytics View ------------------ //

async function loadSalesHistory() {
  const tbody = document.getElementById("salesHistoryRows");
  if (!tbody) return;

  if (isBackendConnected) {
    try {
      const res = await fetch("/api/sales?limit=50");
      const data = await res.json();
      if (data.success && data.sales) {
        sales = data.sales;
        renderSalesHistory(sales);
        return;
      }
    } catch (e) {
      console.error("Sales fetch error", e);
    }
  }

  tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px;color:#94a3b8">No sales records logged yet. Use the POS quick sale form above to start recording sales!</td></tr>`;
}

function renderSalesHistory(list) {
  const tbody = document.getElementById("salesHistoryRows");
  if (!tbody) return;

  if (list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px;color:#94a3b8">No sales transactions logged yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(s => {
    const marginPct = s.total_revenue > 0 ? ((s.total_profit / s.total_revenue) * 100).toFixed(1) : "0.0";
    return `
      <tr>
        <td>${escapeHTML(s.sale_date)}</td>
        <td><b>${escapeHTML(s.product_name)}</b></td>
        <td><b>${s.quantity}</b></td>
        <td>${money(s.unit_price)}</td>
        <td><b>${money(s.total_revenue)}</b></td>
        <td><span class="positive">${money(s.total_profit)}</span> (${marginPct}%)</td>
        <td><small style="color:#64748b">${escapeHTML(s.notes || '')}</small></td>
      </tr>
    `;
  }).join("");
}

// ------------------ Suppliers View ------------------ //

async function loadSuppliers() {
  const tbody = document.getElementById("supplierRows");
  if (!tbody) return;

  if (isBackendConnected) {
    try {
      const res = await fetch("/api/suppliers");
      const data = await res.json();
      if (data.success && data.suppliers) {
        suppliers = data.suppliers;
        renderSuppliersList(suppliers);
        return;
      }
    } catch (e) {
      console.error("Suppliers error", e);
    }
  }

  tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:20px;color:#94a3b8">No suppliers configured.</td></tr>`;
}

function renderSuppliersList(list) {
  const tbody = document.getElementById("supplierRows");
  if (!tbody) return;

  if (list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:20px;color:#94a3b8">No suppliers added yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(s => `
    <tr>
      <td><b>${escapeHTML(s.name)}</b></td>
      <td>${escapeHTML(s.category || 'general')}</td>
      <td>${escapeHTML(s.contact_person || '—')}<br><small style="color:#64748b">${escapeHTML(s.phone || '')}</small></td>
      <td><a href="mailto:${escapeHTML(s.email || '')}" style="color:var(--green)">${escapeHTML(s.email || '—')}</a></td>
      <td><b>${s.lead_time_days || 2} days</b></td>
      <td><span class="pill good">${s.products_count || 0} products</span></td>
    </tr>
  `).join("");
}

async function handleNewSupplierSubmit(e) {
  e.preventDefault();
  const name = document.getElementById("supName").value.trim();
  const contact = document.getElementById("supContact").value.trim();
  const email = document.getElementById("supEmail").value.trim();
  const phone = document.getElementById("supPhone").value.trim();
  const lead = Number(document.getElementById("supLead").value || 2);
  const cat = document.getElementById("supCategory").value;

  if (!name) {
    showToast("Supplier name is required", true);
    return;
  }

  if (isBackendConnected) {
    try {
      const res = await fetch("/api/suppliers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, contact_person: contact, email, phone, lead_time_days: lead, category: cat })
      });
      const data = await res.json();
      if (data.success) {
        showToast(`Supplier "${name}" created!`);
        document.getElementById("supplierForm").reset();
        await loadSuppliers();
        return;
      }
    } catch (e) {
      showToast("Error adding supplier", true);
    }
  }

  showToast(`Supplier "${name}" saved locally`);
  document.getElementById("supplierForm").reset();
}

// ------------------ Reorder Calculator ------------------ //

async function calculate() {
  const d = Math.max(0, +document.getElementById("daily").value || 0);
  const stock = Math.max(0, +document.getElementById("onhand").value || 0);
  const lead = Math.max(0, +document.getElementById("lead").value || 0);
  const season = +document.getElementById("season").value || 0;
  const safety = Math.max(0, +document.getElementById("safety").value || 0);
  const pack = Math.max(1, +document.getElementById("pack").value || 1);
  const cost = Math.max(0, +document.getElementById("cost").value || 0);

  if (isBackendConnected) {
    try {
      const res = await fetch("/api/calculator", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ daily: d, onhand: stock, lead, season, safety, pack, cost })
      });
      const data = await res.json();
      if (data.success) {
        document.getElementById("adjusted").textContent = `${data.adjusted_daily} units`;
        document.getElementById("rop").textContent = `${data.reorder_point} units`;
        document.getElementById("order").textContent = `${data.suggested_order} units`;
        document.getElementById("orderCost").textContent = `Estimated cost ${money(data.order_cost)}`;
        return;
      }
    } catch (e) {
      console.error("Calculator API error", e);
    }
  }

  // Client-side formula
  const adj = d * (1 + season / 100);
  const rop = Math.ceil(adj * (lead + safety));
  const need = Math.max(0, rop - stock);
  const order = need ? Math.ceil(need / pack) * pack : 0;
  document.getElementById("adjusted").textContent = adj.toFixed(1) + " units";
  document.getElementById("rop").textContent = rop.toLocaleString("en-IN") + " units";
  document.getElementById("order").textContent = order.toLocaleString("en-IN") + " units";
  document.getElementById("orderCost").textContent = "Estimated cost " + money(order * cost);
}

// ------------------ Data Export & Management ------------------ //

function downloadStockCSV() {
  if (isBackendConnected) {
    window.location.href = "/api/export/csv";
    showToast("Downloading stock & expiry CSV...");
    return;
  }
  // Client-side fallback
  exportLocalStockCSV();
}

function downloadSalesCSV() {
  if (isBackendConnected) {
    window.location.href = "/api/export/sales-csv";
    showToast("Downloading sales history CSV...");
    return;
  }
  showToast("Connect to Flask backend to export sales records", true);
}

function exportLocalStockCSV() {
  const rows = [
    ["Product", "Category", "Batch ID", "Batch units", "Expiry date", "Received date", "Status", "Weekly sales", "Lead time", "Unit cost", "Value"],
    ...products.flatMap(p => (p.batches || []).map(b => [
      p.name, p.category, b.batch_id || b.id, b.quantity, b.expiry_date, b.received_date, b.status,
      p.weekly_sales_est, p.lead_time_days, p.cost_price, Number(b.quantity || 0) * Number(p.cost_price || 0)
    ]))
  ];
  const csv = rows.map(r => r.map(v => `"${String(v ?? "").replaceAll('"', '""')}"`).join(",")).join("\r\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "freshstock-stock-export.csv";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function resetToSampleData() {
  if (!confirm("This will reload sample supermarket inventory, batches, and sales history. Continue?")) return;
  if (isBackendConnected) {
    try {
      const res = await fetch("/api/admin/seed", { method: "POST" });
      const data = await res.json();
      if (data.success) {
        showToast("Sample supermarket database reloaded!");
        await loadAllData();
        return;
      }
    } catch (e) {
      showToast("Error reloading sample data", true);
    }
  }
}

async function clearAllInventory() {
  if (!confirm("Are you sure you want to clear all products, batches, and sales? This cannot be undone.")) return;
  if (isBackendConnected) {
    try {
      const res = await fetch("/api/admin/clear", { method: "POST" });
      const data = await res.json();
      if (data.success) {
        showToast("Database cleared to fresh empty state.");
        await loadAllData();
        return;
      }
    } catch (e) {
      showToast("Error clearing database", true);
    }
  }
  products = [];
  saveLocalProducts();
  showToast("Cleared local inventory.");
  renderInventoryTable();
  loadKPIs();
}

// ------------------ App Initialization ------------------ //

document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();

  // Filters & Period listeners
  document.getElementById("periodSelect")?.addEventListener("change", e => {
    currentPeriod = e.target.value;
    loadKPIs();
  });

  document.getElementById("forecastCategory")?.addEventListener("change", e => {
    currentCategory = e.target.value;
    loadForecastChart();
  });

  document.getElementById("filterCategory")?.addEventListener("change", () => renderInventoryTable());
  document.getElementById("filterStatus")?.addEventListener("change", () => renderInventoryTable());
  document.getElementById("searchInput")?.addEventListener("input", () => renderInventoryTable());
  document.getElementById("modalSaleProduct")?.addEventListener("change", onSaleProductChange);

  // Form Submissions
  document.getElementById("productForm")?.addEventListener("submit", handleNewProductSubmit);
  document.getElementById("receiveForm")?.addEventListener("submit", handleReceiveSubmit);
  document.getElementById("saleForm")?.addEventListener("submit", handleSaleSubmit);
  document.getElementById("expireForm")?.addEventListener("submit", handleExpireSubmit);
  document.getElementById("editProductForm")?.addEventListener("submit", handleEditProductSubmit);
  document.getElementById("supplierForm")?.addEventListener("submit", handleNewSupplierSubmit);

  // Initial Load
  loadAllData();
  calculate();
});
