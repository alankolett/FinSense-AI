import httpx
import os
import random
from app.mock_sbi.mock_api import MockSBIEngine

sbi_engine = MockSBIEngine()

def get_balance(account_number: str):
    """
    Checks the balance of a specified SBI account.
    """
    result = sbi_engine.get_account_details(account_number)
    if result["status"] == "SUCCESS":
        return f"Account balance for A/C {account_number} is Rs. {result['balance']:.2f}."
    return f"Error: {result['message']}"

def create_savings_account(customer_id: str, deposit: float = 10000.0):
    """
    Initiates savings account creation for a customer.
    Prerequisite: Customer must have KYC completed.
    """
    result = sbi_engine.open_savings_account(customer_id, deposit)
    return result

def send_money_upi(sender_upi: str, receiver_upi: str, amount: float, remarks: str = "Payment"):
    """
    Triggers a UPI money transfer between two virtual payment addresses (UPI IDs).
    """
    result = sbi_engine.process_upi_payment(sender_upi, receiver_upi, amount, remarks)
    return result

# Rule-based stand-in for the XGBoost propensity model described in the pitch deck
def detect_recurring_transfer(customer_id: str, transactions: list) -> dict | None:
    """
    Looks for 2+ transactions of the same amount to the same payee in different months.
    Returns the pattern if found.
    """
    patterns = {}
    for tx in transactions:
        if tx.get("customer_id") != customer_id:
            continue
        if tx.get("type") != "DEBIT":
            continue
            
        desc = tx.get("description", "")
        amount_str = tx.get("amount", 0)
        try:
            amount = float(amount_str)
        except ValueError:
            continue
            
        date_str = tx.get("date", "") # YYYY-MM-DD
        
        # Clean payee name from description
        payee = desc
        if "UPI to " in desc:
            payee = desc.split("UPI to ")[1]
        elif "to " in desc:
            payee = desc.split("to ")[1]
            
        payee = payee.strip().upper()
        
        # Extract month/year
        if len(date_str) >= 7:
            month = date_str[:7] # YYYY-MM
        else:
            continue
            
        key = (payee, amount)
        if key not in patterns:
            patterns[key] = set()
        patterns[key].add(month)
        
    for (payee, amount), months in patterns.items():
        if len(months) >= 2:
            return {
                "payee": payee,
                "amount": amount,
                "frequency": "MONTHLY",
                "occurrences": len(months),
                "months": sorted(list(months))
            }
            
    return None

def detect_insurance_gap(customer_id: str, transactions: list) -> dict | None:
    """
    Flags if medical-category spend exists with no insurance-category debit.
    """
    has_medical = False
    has_insurance = False
    medical_spends = []
    
    # Check transactions
    for tx in transactions:
        if tx.get("customer_id") != customer_id:
            continue
        desc = tx.get("description", "").upper()
        amount_str = tx.get("amount", 0)
        try:
            amount = float(amount_str)
        except ValueError:
            amount = 0
        
        # Medical indicators
        if any(term in desc for term in ["PHARMACY", "HOSPITAL", "CLINIC", "MEDICAL", "HEALTHCARE", "MEDPLUS", "APOLLO", "FORTIS", "MAX"]):
            has_medical = True
            medical_spends.append({
                "description": tx.get("description"),
                "amount": amount,
                "date": tx.get("date")
            })
            
        # Insurance indicators
        if any(term in desc for term in ["INSURANCE", "LIC", "SBI LIFE", "HDFC ERGO", "PREMIUM", "POLICY"]):
            has_insurance = True
            
    if has_medical and not has_insurance:
        total_medical_spend = sum(m["amount"] for m in medical_spends)
        return {
            "has_gap": True,
            "medical_spends_count": len(medical_spends),
            "total_medical_spend": total_medical_spend,
            "recent_medical_spend": medical_spends[-1] if medical_spends else None
        }
        
    return None

def create_standing_instruction(customer_id: str, payee: str, amount: float, frequency: str) -> dict:
    """
    Calls the mock Core Banking System to create a standing instruction.
    """
    port = os.getenv("PORT", "8000")
    host = os.getenv("HOST", "127.0.0.1")
    if host == "0.0.0.0":
        host = "127.0.0.1"
    base_url = f"http://{host}:{port}"
    
    try:
        url = f"{base_url}/mock-sbi/standing-instruction/create"
        data = {
            "customer_id": customer_id,
            "payee": payee,
            "amount": amount,
            "frequency": frequency
        }
        res = httpx.post(url, json=data, timeout=5.0).json()
        return res
    except Exception as e:
        # Fallback offline simulation
        return {
            "status": "STANDING_INSTRUCTION_CREATED",
            "instruction_id": f"SI{random.randint(100000, 999999)}",
            "customer_id": customer_id,
            "payee": payee,
            "amount": amount,
            "frequency": frequency,
            "note": f"Offline Fallback: {str(e)}"
        }

def create_sip(customer_id: str, goal_description: str, target_amount: float, target_years: int, monthly_sip_amount: float) -> dict:
    """
    Calls the mock Core Banking System to create a Systematic Investment Plan (SIP).
    """
    port = os.getenv("PORT", "8000")
    host = os.getenv("HOST", "127.0.0.1")
    if host == "0.0.0.0":
        host = "127.0.0.1"
    base_url = f"http://{host}:{port}"
    
    try:
        url = f"{base_url}/mock-sbi/sip/create"
        data = {
            "customer_id": customer_id,
            "goal_description": goal_description,
            "target_amount": target_amount,
            "target_years": target_years,
            "monthly_sip_amount": monthly_sip_amount
        }
        res = httpx.post(url, json=data, timeout=5.0).json()
        return res
    except Exception as e:
        return {
            "status": "SIP_CREATED",
            "sip_id": f"SIP{random.randint(100000, 999999)}",
            "customer_id": customer_id,
            "goal_description": goal_description,
            "target_amount": target_amount,
            "target_years": target_years,
            "monthly_sip_amount": monthly_sip_amount,
            "note": f"Offline Fallback: {str(e)}"
        }

