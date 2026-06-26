import os
import json
import csv
from app.llm import call_llm
from app.memory.customer_store import CustomerStore
from app.tools.banking_tools import (
    detect_recurring_transfer,
    detect_insurance_gap,
    create_standing_instruction,
    create_sip
)

TRANSACTIONS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "transactions.csv"))

def get_customer_transactions(customer_id: str) -> list:
    txns = []
    if os.path.exists(TRANSACTIONS_FILE):
        with open(TRANSACTIONS_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("customer_id") == customer_id:
                    txns.append(row)
    return txns

class AdoptAgent:
    def __init__(self):
        self.name = "FinSense Adopt Agent"
        self.role = "Product Adoption & Credit Advisor"
        self.store = CustomerStore()

    def handle_transaction_event(self, customer_id: str, transaction: dict) -> dict | None:
        """
        On each incoming transaction event, evaluates recent transaction history for cross-sell triggers.
        If a pattern is found, generates a proactive nudge and saves it as pending in the customer store.
        """
        # Fetch recent transaction history
        transactions = get_customer_transactions(customer_id)
        # Add the new incoming transaction to the list to assess it
        transactions.append(transaction)
        
        # 1. Check for recurring transfers pattern
        recurring_pattern = detect_recurring_transfer(customer_id, transactions)
        if recurring_pattern:
            # Check if this recurring transfer has already been handled (nudge exists or SI is active)
            customer = self.store.get_customer(customer_id)
            if customer and customer.get("pending_nudge"):
                # Nudge already active
                return None
                
            payee = recurring_pattern["payee"]
            amount = recurring_pattern["amount"]
            
            # Generate personalized conversational nudge
            prompt = f"""
            Generate a short, friendly, and helpful notification (1-2 sentences) to a customer.
            Context: We noticed they manually transfer ₹{amount} to {payee} every month.
            Goal: Recommend setting up a standing instruction (automated transfer) and ask for their consent.
            """
            nudge_text = call_llm(prompt=prompt, system="You are the FinSense Adopt Agent for SBI.").strip()
            
            nudge_data = {
                "type": "recurring_transfer",
                "payee": payee,
                "amount": amount,
                "frequency": "MONTHLY",
                "text": nudge_text
            }
            
            # Save to store
            self.store.update_customer(customer_id, pending_nudge=json.dumps(nudge_data))
            return nudge_data
            
        # 2. Check for insurance gap pattern
        insurance_gap = detect_insurance_gap(customer_id, transactions)
        if insurance_gap:
            customer = self.store.get_customer(customer_id)
            if customer and customer.get("pending_nudge"):
                return None
                
            total_spend = insurance_gap["total_medical_spend"]
            recent_merchant = insurance_gap["recent_medical_spend"]["description"] if insurance_gap["recent_medical_spend"] else "medical merchants"
            
            prompt = f"""
            Generate a short, helpful, and empathetic notification (1-2 sentences) to a customer.
            Context: We noticed they have spent ₹{total_spend} at medical services (recent spend at {recent_merchant}) but have no health insurance policy registered with us.
            Goal: Suggest checking out SBI's tax-saving customized health insurance plans to shield their savings, and ask if they would like to request details.
            """
            nudge_text = call_llm(prompt=prompt, system="You are the FinSense Adopt Agent for SBI.").strip()
            
            nudge_data = {
                "type": "insurance_gap",
                "payee": "SBI Health Insurance",
                "amount": total_spend,
                "text": nudge_text
            }
            
            self.store.update_customer(customer_id, pending_nudge=json.dumps(nudge_data))
            return nudge_data
            
        return None

    def handle(self, message: str, customer_id: str) -> dict:
        """
        Processes replies to nudges, goal setting, and product queries.
        """
        customer = self.store.get_customer(customer_id)
        if not customer:
            customer = self.store.update_customer(customer_id)
            
        pending_nudge_str = customer.get("pending_nudge")
        
        # Scenario A: Handle active pending nudge reply
        if pending_nudge_str:
            try:
                nudge_data = json.loads(pending_nudge_str)
            except Exception:
                nudge_data = None
                
            if nudge_data:
                # Use LLM to check if message contains affirmation
                affirmation_prompt = f"""
                Determine if the user's message is a 'yes' or affirmation to setting up the suggested option in the chat.
                User message: "{message}"
                
                Respond with 'YES' if they agree/accept, or 'NO' if they do not agree/reject/want something else. Do not output anything else besides 'YES' or 'NO'.
                """
                is_affirmative = call_llm(prompt=affirmation_prompt).strip().upper()
                
                if "YES" in is_affirmative:
                    # Clear pending nudge
                    self.store.update_customer(customer_id, pending_nudge=None)
                    
                    if nudge_data["type"] == "recurring_transfer":
                        res = create_standing_instruction(
                            customer_id,
                            nudge_data["payee"],
                            nudge_data["amount"],
                            nudge_data["frequency"]
                        )
                        reply = (
                            f"Wonderful! I have set up an automated Standing Instruction for you.\n"
                            f"Payee: {nudge_data['payee']}\n"
                            f"Amount: ₹{nudge_data['amount']:.2f}\n"
                            f"Frequency: {nudge_data['frequency']}\n"
                            f"Instruction ID: {res.get('instruction_id', 'SI999999')}"
                        )
                        return {"reply": reply, "stage": "ADOPT_COMPLETED", "customer_id": customer_id}
                        
                    elif nudge_data["type"] == "insurance_gap":
                        reply = (
                            "Great decision! I have registered your interest in SBI Health Insurance. "
                            "One of our health advisors will call you at your registered mobile number shortly to customize a tax-saving plan for you."
                        )
                        return {"reply": reply, "stage": "ADOPT_COMPLETED", "customer_id": customer_id}
                else:
                    # Clear pending nudge if they rejected it
                    self.store.update_customer(customer_id, pending_nudge=None)
                    reply = "No problem! Let me know if there is anything else I can help you with today."
                    return {"reply": reply, "stage": "ADOPT", "customer_id": customer_id}

        # Scenario B: Check if they are expressing a savings goal
        goal_prompt = f"""
        Analyze the user message to check if they are expressing a specific savings goal (e.g., wanting to save a certain amount of money over a certain number of years for education, buying a house, retirement, car, etc.).
        User message: "{message}"
        
        If yes, output a JSON object with keys:
        - "goal_description": "short description of the goal",
        - "target_amount": numeric value of target amount (e.g., 500000 for 5 lakhs),
        - "target_years": numeric number of years (e.g., 5)
        
        If they are NOT expressing a savings goal, output null. Output ONLY raw JSON, nothing else.
        """
        try:
            goal_json = call_llm(prompt=goal_prompt).replace("```json", "").replace("```", "").strip()
            if goal_json != "null" and goal_json != "":
                goal_data = json.loads(goal_json)
                desc = goal_data.get("goal_description")
                amount = float(goal_data.get("target_amount", 0))
                years = int(goal_data.get("target_years", 1))
                
                if amount > 0 and years > 0:
                    # Simple calculation: monthly_sip_amount = target_amount / (target_years * 12)
                    # Note: a real version would use expected return rate (e.g. 12% p.a. compound)
                    monthly_sip = amount / (years * 12)
                    
                    sip_res = create_sip(customer_id, desc, amount, years, monthly_sip)
                    sip_id = sip_res.get("sip_id", "SIP999999")
                    
                    reply = (
                        f"That is a great goal! To save ₹{amount:,.2f} for '{desc}' in {years} years, "
                        f"you will need a monthly Systematic Investment Plan (SIP) of ₹{monthly_sip:,.2f}.\n"
                        f"I have successfully created this SIP plan for you! Plan ID: {sip_id}."
                    )
                    return {"reply": reply, "stage": "SIP_CREATED", "customer_id": customer_id}
        except Exception:
            pass

        # Scenario C: General fallback advisor reply
        fallback_prompt = f"""
        You are the FinSense Adopt Agent, a credit and savings advisor for SBI.
        Respond to the user query in a helpful, conversational manner.
        Mention that you can help them setup Automated Standing Instructions, create Systematic Investment Plans (SIPs) for their financial goals, or evaluate credit card limits.
        
        User Query: "{message}"
        """
        reply = call_llm(prompt=fallback_prompt, system="You are the FinSense Adopt Agent for SBI.").strip()
        
        return {"reply": reply, "stage": "ADOPT", "customer_id": customer_id}

    def execute(self, query: str, context: dict = None):
        """
        Maintains backward compatibility with original router calls.
        """
        ctx = context or {}
        customer_id = ctx.get("customer_id", "CUST001")
        res = self.handle(query, customer_id)
        return {"response": res["reply"], "status": "COMPLETED"}
