import os
import shutil
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

# Load environmental configs
load_dotenv()

app = FastAPI(
    title="FinSense AI Backend",
    description="Multi-Agent system routing bank customer requests and banker intelligence tools.",
    version="1.0.0"
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Mock SBI API Router (mounted at root since endpoints have prefix /mock-sbi)
from app.mock_sbi.mock_api import router as mock_sbi_router
app.include_router(mock_sbi_router)

# Include FinSense Agent Router (for banker dashboard /api/graph, /api/customers, etc.)
from app.router import router as api_router
app.include_router(api_router, prefix="/api")

# Models for chat
class ChatRequest(BaseModel):
    message: str
    customer_id: str
    image_path: Optional[str] = None

class TransactionEvent(BaseModel):
    transaction_id: str
    customer_id: str
    account_number: str
    date: str
    amount: float
    type: str
    description: str
    status: str

@app.post("/events/transaction")
async def receive_transaction_event(event: TransactionEvent):
    """
    # SIMULATES Kafka transaction stream for demo purposes — replace with real Kafka consumer in production
    """
    from app.agents.adopt_agent import AdoptAgent
    try:
        agent = AdoptAgent()
        txn_dict = event.dict()
        nudge = agent.handle_transaction_event(event.customer_id, txn_dict)
        if nudge:
            print(f"[CROSS-SELL ALERT] Generated proactive nudge for {event.customer_id}: {nudge['text']}")
            return {
                "status": "PROCESSED",
                "nudge_generated": True,
                "nudge": nudge
            }
        return {
            "status": "PROCESSED",
            "nudge_generated": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {
        "status": "ONLINE",
        "service": "FinSense AI Multi-Agent API Engine",
        "docs_url": "/docs"
    }

@app.get("/health")
async def health():
    return {
        "status": "HEALTHY",
        "service": "FinSense AI Backend"
    }

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """
    Main conversational agent endpoint.
    Routes the message using FinSenseRouter.
    """
    from app.router import FinSenseRouter
    try:
        result = FinSenseRouter.route(req.message, req.customer_id, req.image_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Setup upload folder
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))

@app.post("/upload-document")
async def upload_document(file: UploadFile = File(...)):
    """
    Saves an uploaded file locally and returns the absolute file path.
    """
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"image_path": file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
