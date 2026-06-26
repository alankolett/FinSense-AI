# FinSense AI: Multi-Agent Banking Assistant

FinSense AI is a next-generation agentic banking platform designed to orchestrate onboarding, product adoption, and proactive customer engagement. It uses a FastAPI backend powered by structured intelligence agents and a premium Zinc-themed React dashboard for bankers.

## Architecture & Folder Structure

```
FinSense AI/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── router.py            # FinSense Agent Router
│   │   ├── agents/
│   │   │   ├── acquire_agent.py # Onboarding & KYC
│   │   │   ├── adopt_agent.py   # Upselling & Education
│   │   │   └── engage_agent.py  # Alerts & Transaction support
│   │   ├── tools/               # Agent tool implementations
│   │   │   ├── kyc_tools.py
│   │   │   ├── banking_tools.py
│   │   │   └── messaging_tools.py
│   │   ├── mock_sbi/            # Simulated CBS/CKYC/UPI APIs
│   │   │   └── mock_api.py
│   │   ├── data/
│   │   │   ├── customers.json
│   │   │   ├── transactions.csv
│   │   │   └── product_docs/    # RAG source docs
│   │   └── memory/
│   │       └── customer_graph.py # Relational intelligence graph
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWidget.jsx   # Client-side agent chat interface
│   │   │   └── BankerDashboard.jsx # Banker analytics console
│   │   └── App.jsx
│   └── package.json
└── README.md
```

## Setup & Running

### Backend Setup

1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the server:
   ```bash
   uvicorn app.main:app --reload
   ```
   The API will be available at `http://localhost:8000`.

### Frontend Setup

1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the Vite dev server:
   ```bash
   npm run dev
   ```
   The dashboard will be available at `http://localhost:5173`.
