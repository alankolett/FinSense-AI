from app.tools.banking_tools import get_balance, send_money_upi, sbi_engine
from app.tools.messaging_tools import send_push_notification, send_sms_notification

class EngageAgent:
    def __init__(self):
        self.name = "FinSense Engage Agent"
        self.role = "Proactive Engagement & Transaction Assistant"

    def execute(self, query: str, context: dict = None):
        """
        Executes active account management operations.
        Context can contain: customer_id, account_number, receiver_upi, amount, remarks.
        """
        query_lc = query.lower()
        ctx = context or {}
        cust_id = ctx.get("customer_id")
        acc_num = ctx.get("account_number")

        # 1. Balance Checks
        if "balance" in query_lc or "how much money" in query_lc:
            if not acc_num:
                # Attempt to retrieve account number from customer ID
                if cust_id:
                    for cust in sbi_engine.customers:
                        if cust["customer_id"] == cust_id:
                            if len(cust["accounts"]) > 0:
                                acc_num = cust["accounts"][0]["account_number"]
                                break
                
                if not acc_num:
                    return {
                        "agent": self.name,
                        "response": "To check your account balance, please provide your account number.",
                        "status": "AWAITING_INPUT",
                        "fields_needed": ["account_number"]
                    }
            
            bal_str = get_balance(acc_num)
            return {
                "agent": self.name,
                "response": bal_str,
                "status": "COMPLETED",
                "account_number": acc_num
            }

        # 2. UPI Payments / Send Money
        elif "pay" in query_lc or "transfer" in query_lc or "send" in query_lc:
            sender_upi = ctx.get("sender_upi")
            receiver_upi = ctx.get("receiver_upi")
            amount = ctx.get("amount")
            remarks = ctx.get("remarks", "Transfer")

            if not sender_upi and cust_id:
                # Find sender's UPI
                for cust in sbi_engine.customers:
                    if cust["customer_id"] == cust_id:
                        if len(cust["accounts"]) > 0:
                            sender_upi = cust["accounts"][0]["upi_id"]
                            break

            if not sender_upi or not receiver_upi or not amount:
                return {
                    "agent": self.name,
                    "response": "To perform a UPI transfer, please specify: Sender UPI ID, Receiver UPI ID, and the Amount.",
                    "status": "AWAITING_INPUT",
                    "fields_needed": ["sender_upi", "receiver_upi", "amount"]
                }
            
            try:
                amt_val = float(amount)
            except ValueError:
                return {
                    "agent": self.name,
                    "response": "Please enter a valid numeric value for the transaction amount.",
                    "status": "ERROR"
                }

            pay_res = send_money_upi(sender_upi, receiver_upi, amt_val, remarks)
            if pay_res["status"] == "SUCCESS":
                msg = f"UPI Payment of Rs. {amt_val:.2f} to {receiver_upi} was processed successfully.\nTXN ID: {pay_res['transaction_id']}"
                return {
                    "agent": self.name,
                    "response": msg,
                    "status": "COMPLETED",
                    "transaction_id": pay_res["transaction_id"],
                    "sender_balance": pay_res["sender_balance"]
                }
            else:
                return {
                    "agent": self.name,
                    "response": f"UPI transfer failed: {pay_res['message']}",
                    "status": "ERROR"
                }

        # 3. Proactive Suspicious Flags / Fraud Alerts
        elif "flag" in query_lc or "suspect" in query_lc or "crypto" in query_lc:
            if not cust_id:
                return {
                    "agent": self.name,
                    "response": "Please provide a customer ID to run suspicious activity checks.",
                    "status": "AWAITING_INPUT",
                    "fields_needed": ["customer_id"]
                }
                
            # Simulate scanning recent transactions for warnings
            import csv
            import os
            TRANSACTIONS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "transactions.csv"))
            
            has_crypto = False
            if os.path.exists(TRANSACTIONS_FILE):
                with open(TRANSACTIONS_FILE, "r") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row["customer_id"] == cust_id and "crypto" in row["description"].lower():
                            has_crypto = True
                            break
                            
            if has_crypto:
                send_push_notification(cust_id, "Security Alert", "High-risk crypto transactions flagged on your profile. Please contact your banker.")
                send_sms_notification("+919876543212", "ALERT: A high-risk crypto purchase was detected on your account. Review details in SBI NetBanking.")
                return {
                    "agent": self.name,
                    "response": "CRITICAL FLAG: Suspicious crypto activity detected for this profile. Sent urgent security notifications (SMS & PUSH) requesting banker verification.",
                    "status": "FLAGGED",
                    "risk_indicator": "Crypto Purchase"
                }
            else:
                return {
                    "agent": self.name,
                    "response": "Risk scan complete. No high-risk transaction flags found for this customer profile.",
                    "status": "COMPLETED"
                }

        # Default Response
        return {
            "agent": self.name,
            "response": "Hello! I am the FinSense Engagement Agent. I assist with checking account balances, processing UPI payments, and monitoring profile security for suspicious flags.",
            "status": "AWAITING_INSTRUCTION"
        }
