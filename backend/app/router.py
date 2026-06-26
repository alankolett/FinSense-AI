from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import json
import csv

# Import agents
from app.agents.acquire_agent import AcquireAgent
from app.agents.adopt_agent import AdoptAgent
from app.agents.engage_agent import EngageAgent
from app.llm import call_llm
from app.memory.customer_store import CustomerStore

# Define router for dashboard
router = APIRouter()
store = CustomerStore()

class FinSenseRouter:
    @staticmethod
    def route(message: str, customer_id: str, image_path: Optional[str] = None) -> dict:
        """
        Classifies incoming user messages and routes them to the appropriate agent.
        Defaults to AcquireAgent if the customer does not have an account yet.
        """
        customer = store.get_customer(customer_id)
        
        # Rule: Default to AcquireAgent if the customer has no account yet
        if not customer or not customer.get("account_number"):
            agent = AcquireAgent()
            return agent.handle(message, customer_id, image_path)
            
        # If account exists, classify query to route to the correct agent
        classification_prompt = f"""You are the intelligent router for a multi-agent banking system.
Given the User Message, classify it into one of three categories:
1. 'acquire': Onboarding, KYC, opening a savings account, updating personal details, scheduling Video KYC.
2. 'adopt': Loans, credit cards, premium savings accounts, interest rates, checking credit eligibility.
3. 'engage': Checking account balance, sending money, UPI transactions, checking transaction history, security alerts, reporting suspicious activities.

User Message: "{message}"

Respond with exactly one word from this list: 'acquire', 'adopt', 'engage'. Do not write anything else.
"""
        try:
            category = call_llm(prompt=classification_prompt).strip().lower()
        except Exception:
            # Fallback based on simple keyword matching
            message_lc = message.lower()
            if any(keyword in message_lc for keyword in ["loan", "card", "elite", "prime", "simplysave", "savings plus", "interest", "recommend", "eligible", "reward"]):
                category = "adopt"
            elif any(keyword in message_lc for keyword in ["balance", "how much money", "pay", "transfer", "send", "flag", "suspect", "crypto"]):
                category = "engage"
            else:
                category = "acquire"

        if "adopt" in category:
            agent = AdoptAgent()
            res = agent.execute(message, {"customer_id": customer_id})
            return {
                "reply": res.get("response", "I can help you explore loan and credit card options."),
                "stage": "ADOPT",
                "customer_id": customer_id
            }
        elif "engage" in category:
            agent = EngageAgent()
            res = agent.execute(message, {"customer_id": customer_id})
            return {
                "reply": res.get("response", "I can help with balance checks and transactions."),
                "stage": "ENGAGE",
                "customer_id": customer_id
            }
        else:
            agent = AcquireAgent()
            return agent.handle(message, customer_id, image_path)

# --- BANKER DASHBOARD ENDPOINTS ---
@router.get("/graph")
async def get_intelligence_graph():
    """Returns the visual nodes and links for the Banker Dashboard memory graph."""
    from app.memory.customer_graph import CustomerGraphStore
    try:
        graph_store = CustomerGraphStore()
        data = graph_store.get_graph_data()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/customers")
async def get_customers():
    """Returns the lists of customer profiles."""
    from app.mock_sbi.mock_api import CUSTOMERS_FILE
    if os.path.exists(CUSTOMERS_FILE):
        with open(CUSTOMERS_FILE, "r") as f:
            return json.load(f)
    return []

@router.get("/transactions")
async def get_transactions(customer_id: Optional[str] = None):
    """Returns transaction list logs."""
    from app.mock_sbi.mock_api import TRANSACTIONS_FILE
    txns = []
    if os.path.exists(TRANSACTIONS_FILE):
        with open(TRANSACTIONS_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not customer_id or row["customer_id"] == customer_id:
                    txns.append(row)
    return txns
