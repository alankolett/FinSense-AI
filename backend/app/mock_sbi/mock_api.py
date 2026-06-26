import os
import json
import csv
import random
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
CUSTOMERS_FILE = os.path.join(DATA_DIR, "customers.json")
TRANSACTIONS_FILE = os.path.join(DATA_DIR, "transactions.csv")

router = APIRouter()

class AccountCreateRequest(BaseModel):
    name: str
    dob: str
    aadhaar_number: str
    pan_number: str

class VKYCScheduleRequest(BaseModel):
    account_number: str
    preferred_slot: str

class StandingInstructionRequest(BaseModel):
    customer_id: str
    payee: str
    amount: float
    frequency: str

class SIPRequest(BaseModel):
    customer_id: str
    goal_description: str
    target_amount: float
    target_years: int
    monthly_sip_amount: float

# MOCKED — simulates Finacle/CKYC/UPI for demo purposes
@router.post("/mock-sbi/standing-instruction/create")
async def create_standing_instruction_endpoint(req: StandingInstructionRequest):
    fake_instruction_id = f"SI{random.randint(100000, 999999)}"
    return {
        "status": "STANDING_INSTRUCTION_CREATED",
        "instruction_id": fake_instruction_id,
        "customer_id": req.customer_id,
        "payee": req.payee,
        "amount": req.amount,
        "frequency": req.frequency
    }

# MOCKED — simulates Finacle/CKYC/UPI for demo purposes
@router.post("/mock-sbi/sip/create")
async def create_sip_endpoint(req: SIPRequest):
    fake_sip_id = f"SIP{random.randint(100000, 999999)}"
    return {
        "status": "SIP_CREATED",
        "sip_id": fake_sip_id,
        "customer_id": req.customer_id,
        "goal_description": req.goal_description,
        "target_amount": req.target_amount,
        "target_years": req.target_years,
        "monthly_sip_amount": req.monthly_sip_amount
    }

# MOCKED — simulates Finacle/CKYC/UPI for demo purposes
@router.post("/mock-sbi/account/create")
async def create_account(req: AccountCreateRequest):
    # generate fake account number: "SBI" + 10 random digits
    fake_acc = "SBI" + "".join(str(random.randint(0, 9)) for _ in range(10))
    return {
        "status": "ACCOUNT_CREATED",
        "account_number": fake_acc,
        "name": req.name
    }

# MOCKED — simulates Finacle/CKYC/UPI for demo purposes
@router.get("/mock-sbi/account/{account_number}")
async def get_account(account_number: str):
    return {
        "account_number": account_number,
        "balance": 15000.0,
        "account_type": "SAVINGS"
    }

# MOCKED — simulates Finacle/CKYC/UPI for demo purposes
@router.post("/mock-sbi/vkyc/schedule")
async def schedule_vkyc(req: VKYCScheduleRequest):
    fake_slot_id = f"SLOT{random.randint(1000, 9999)}"
    return {
        "status": "SCHEDULED",
        "slot_id": fake_slot_id,
        "account_number": req.account_number,
        "time": req.preferred_slot
    }

# MOCKED — simulates Finacle/CKYC/UPI for demo purposes
@router.get("/mock-sbi/ckyc/verify/{aadhaar_number}")
async def verify_ckyc_endpoint(aadhaar_number: str):
    return {
        "verified": True,
        "aadhaar_number": aadhaar_number
    }

class MockSBIEngine:
    def __init__(self):
        self._load_data()

    def _load_data(self):
        # Load customers
        if os.path.exists(CUSTOMERS_FILE):
            with open(CUSTOMERS_FILE, "r") as f:
                self.customers = json.load(f)
        else:
            self.customers = []

    def _save_customers(self):
        with open(CUSTOMERS_FILE, "w") as f:
            json.dump(self.customers, f, indent=2)

    # --- CKYC REGISTRY SIMULATOR ---
    def verify_ckyc(self, pan: str = None, aadhaar: str = None):
        """Simulates checking Central KYC registry database."""
        for cust in self.customers:
            if (pan and cust["pan"] == pan.upper()) or (aadhaar and cust["aadhaar"] == aadhaar):
                return {
                    "status": "SUCCESS",
                    "kyc_status": cust["kyc_status"],
                    "customer_id": cust["customer_id"],
                    "name": cust["name"],
                    "pan": cust["pan"],
                    "aadhaar": cust["aadhaar"]
                }
        # If not found, return empty record
        return {
            "status": "NOT_FOUND",
            "kyc_status": "NONE",
            "customer_id": None,
            "name": "Unknown Customer",
            "pan": pan,
            "aadhaar": aadhaar
        }

    def update_kyc_status(self, customer_id: str, new_status: str):
        """Updates CKYC status for a customer."""
        for cust in self.customers:
            if cust["customer_id"] == customer_id:
                cust["kyc_status"] = new_status
                self._save_customers()
                return {"status": "SUCCESS", "customer_id": customer_id, "kyc_status": new_status}
        return {"status": "ERROR", "message": f"Customer {customer_id} not found."}

    # --- CBS (CORE BANKING SYSTEM) SIMULATOR ---
    def get_account_details(self, account_number: str):
        """Retrieves details of an account."""
        for cust in self.customers:
            for acc in cust["accounts"]:
                if acc["account_number"] == account_number:
                    return {
                        "status": "SUCCESS",
                        "customer_id": cust["customer_id"],
                        "name": cust["name"],
                        "account_number": acc["account_number"],
                        "account_type": acc["account_type"],
                        "balance": acc["balance"],
                        "upi_id": acc["upi_id"]
                    }
        return {"status": "ERROR", "message": "Account not found"}

    def open_savings_account(self, customer_id: str, initial_deposit: float = 10000.0):
        """Opens a savings account for a customer."""
        for cust in self.customers:
            if cust["customer_id"] == customer_id:
                if cust["kyc_status"] != "COMPLETED":
                    return {"status": "ERROR", "message": "KYC must be COMPLETED before opening an account."}
                
                # Check if account already exists
                if len(cust["accounts"]) > 0:
                    return {"status": "ERROR", "message": "Customer already has a savings account.", "accounts": cust["accounts"]}
                
                # Generate account number
                acc_num = f"SBI100020003{len(self.customers) + 100:03d}"
                upi_id = f"{cust['name'].lower().replace(' ', '')}@oksbi"
                
                new_acc = {
                    "account_number": acc_num,
                    "account_type": "SAVINGS",
                    "balance": initial_deposit,
                    "upi_id": upi_id
                }
                
                cust["accounts"].append(new_acc)
                self._save_customers()
                
                # Log initial deposit transaction
                self.record_transaction(customer_id, acc_num, initial_deposit, "CREDIT", "Initial Deposit - Account Opening")
                
                return {
                    "status": "SUCCESS",
                    "message": "Account opened successfully",
                    "account_number": acc_num,
                    "upi_id": upi_id,
                    "balance": initial_deposit
                }
        return {"status": "ERROR", "message": f"Customer {customer_id} not found."}

    def record_transaction(self, customer_id: str, account_number: str, amount: float, txn_type: str, description: str):
        """Appends a transaction to the transactions CSV and updates account balance."""
        # Update balance
        balance_updated = False
        for cust in self.customers:
            if cust["customer_id"] == customer_id:
                for acc in cust["accounts"]:
                    if acc["account_number"] == account_number:
                        if txn_type == "DEBIT":
                            if acc["balance"] < amount:
                                return False, "Insufficient balance"
                            acc["balance"] -= amount
                        else:
                            acc["balance"] += amount
                        balance_updated = True
                        break
        
        if not balance_updated:
            return False, "Account or Customer not matching"

        self._save_customers()

        # Write to CSV
        txn_id = f"TXN{datetime.now().strftime('%M%S%f')[:-3]}"
        today = datetime.now().strftime("%Y-%m-%d")
        
        file_exists = os.path.exists(TRANSACTIONS_FILE)
        with open(TRANSACTIONS_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["transaction_id", "customer_id", "account_number", "date", "amount", "type", "description", "status"])
            writer.writerow([txn_id, customer_id, account_number, today, f"{amount:.2f}", txn_type, description, "SUCCESS"])
            
        return True, txn_id

    # --- UPI GATEWAY SIMULATOR ---
    def process_upi_payment(self, sender_upi_id: str, receiver_upi_id: str, amount: float, description: str):
        """Simulates a UPI transfer between two UPI IDs."""
        sender_acc = None
        sender_cust = None
        receiver_acc = None
        receiver_cust = None

        for cust in self.customers:
            for acc in cust["accounts"]:
                if acc["upi_id"] == sender_upi_id:
                    sender_acc = acc
                    sender_cust = cust
                if acc["upi_id"] == receiver_upi_id:
                    receiver_acc = acc
                    receiver_cust = cust

        if not sender_acc:
            return {"status": "ERROR", "message": f"Sender UPI ID {sender_upi_id} not found"}
        
        if sender_acc["balance"] < amount:
            return {"status": "ERROR", "message": "Insufficient balance"}

        # Perform Debit
        sender_acc["balance"] -= amount
        # Perform Credit if receiver is within mock SBI, else it's external (just processed)
        if receiver_acc:
            receiver_acc["balance"] += amount
        
        self._save_customers()

        # Record transactions
        txn_id_s = f"TXN{datetime.now().strftime('%M%S%f')[:-3]}"
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Log sender debit
        with open(TRANSACTIONS_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([txn_id_s, sender_cust["customer_id"], sender_acc["account_number"], today, f"{amount:.2f}", "DEBIT", f"UPI to {receiver_upi_id} - {description}", "SUCCESS"])
            
            # Log receiver credit if in same system
            if receiver_acc and receiver_cust:
                txn_id_r = f"TXN{int(txn_id_s[3:])+1}"
                writer.writerow([txn_id_r, receiver_cust["customer_id"], receiver_acc["account_number"], today, f"{amount:.2f}", "CREDIT", f"UPI from {sender_upi_id} - {description}", "SUCCESS"])

        return {
            "status": "SUCCESS",
            "message": "UPI payment completed successfully",
            "transaction_id": txn_id_s,
            "sender_balance": sender_acc["balance"]
        }
