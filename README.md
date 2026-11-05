# Supply Chain AI Decision-Intelligence Platform — Phase-1 POC

An enterprise decision-intelligence platform unifying multi-source ERP/WMS data, statistical time-series demand forecasting, deterministic safety stock & reorder point optimization, Model Context Protocol (MCP) tools, Claude / ReAct Agent reasoning, and an interactive React Control Tower UI.

```
DATA SOURCES (CSV / Mock ERP / Mock WMS)
       │
CONNECTORS / INGESTION (Validation & Transformation)
       │
  POSTGRESQL / SQLITE DATABASE (Supply Chain Schema)
       │
FASTAPI BACKEND (Application Services, Repositories, API Routes)
       │
  ┌────┴──────────────────────────┐
  │ AI/ML ENGINE                  │
  │  - Demand Forecasting         │
  │  - Safety Stock / Reorder Point│
  │  - Inventory Risk Engine      │
  └────┬──────────────────────────┘
       │
   MCP SERVER (Read-Only Controlled Tools)
       │
  REACT AGENT (Tool Selection & Reasoning Engine)
       │
 GENAI PROVIDER (Claude Provider / Robust Mock Fallback)
       │
 RECOMMENDATIONS & RISK INSIGHTS
       │
 CONTROL TOWER FRONTEND (React Dashboard + AI Assistant)
```

---

## Key Features

1. **Supply Chain Control Tower Dashboard**:
   - Real-time Executive KPI cards: Total Inventory Value, Critical Risk Counts, Open POs, 30-Day Revenue.
   - Interactive Inventory Risk Matrix with filters for warehouse hubs and risk classifications (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
   - Time-series Demand Forecast Visualizer with 95% confidence intervals and MAE/RMSE accuracy metrics.
   - Automated Replenishment & Procurement Recommendations.

2. **AI Assistant & ReAct Agent**:
   - Integrated AI Chat drawer connected to backend ReAct Agent (`/api/ai/chat`).
   - Uses pure Python MCP tools to inspect real-time database state and calculate safety stock thresholds.
   - Powered by Anthropic Claude 3.5 Sonnet with a deterministic offline mock fallback when API keys are omitted.

3. **Multi-Source Connectors**:
   - CSV File Ingestion pipeline with validation error logs.
   - Mock ERP REST Connector for SAP/Oracle simulation.
   - Mock WMS REST Connector for warehouse stock movements.

4. **BI Analytics Integration**:
   - Export adapters for PowerBI and Tableau formatted JSON and CSV datasets (`/api/bi/export`).

5. **Intelligence Tab (9 supply-chain intelligences, `backend/ml/intelligences/`)**:
   Demand Forecasting, Inventory Planning, Inventory Policy Simulation, Pricing & Demand, Customer Value (LTV),
   Market Basket, Supplier Segmentation, Assortment Planning and Trade Area (Huff model). Each is calculated from
   the data in the database and served by `GET /api/intelligences/{id}`.

---

## Step-by-Step Quickstart Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
```

### 3. Seed Database with Realistic Sample Data
Generates 50+ products, 3 warehouses, suppliers, 180 days of daily sales, stockout risk scenarios, and open POs:
```bash
python database/seeds/seed_db.py
```

**Or load the retail dataset** (`Data.xlsx` + `Trade_Area_Synthetic_Inputs.xlsx` from
[ahmedkhancgt/supply-chain](https://github.com/ahmedkhancgt/supply-chain/tree/claude/python-file-review-ikw2q4/data)).
It cleans the 140,000 rows to 139,953 the same way the original analysis scripts do and loads products, suppliers,
countries (as warehouses), customers, invoices (orders + order lines), sales and the trade-area inputs.
`--wipe` first deletes all business data and saved ML results but keeps users, roles and settings:
```bash
python backend/database/seeds/load_retail_dataset.py --data-dir data --download --wipe
```
The 9 intelligences on the Intelligence tab (`GET /api/intelligences/{id}`) are recalculated from whatever is in the database.

### 4. Start FastAPI Backend & MCP Services
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

### 5. Start Control Tower Frontend
In a new terminal:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### 6. Run the Backend via Docker Compose
Runs only the backend API on port 8000 (run the frontend with `npm run dev` as above):
```bash
cd backend
docker compose up --build -d
```

---

## Main Demo Flow & Prompt Verification

Open the **Supply Chain Control Tower UI** at `http://localhost:3000`.

1. Click **"Ask AI Assistant"** in the top navigation bar.
2. Enter prompt:
   > *"Which products are at risk of stockout in the next 7 days?"*
3. The ReAct Agent dynamically selects `get_inventory_risk`, queries PostgreSQL via MCP tools, evaluates lead times and demand forecasts, and responds with exact SKU metrics and supplier order quantities.
