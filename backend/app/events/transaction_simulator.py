import os
import csv
import time
import argparse
import requests

# SIMULATES Kafka transaction stream for demo purposes — replace with real Kafka consumer in production

DEFAULT_INTERVAL = 5.0
CSV_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "transactions.csv"))
TARGET_URL = "http://localhost:8000/events/transaction"

def run_simulator(interval: float, url: str):
    print(f"[*] Starting transaction simulator...")
    print(f"[*] Target Endpoint: {url}")
    print(f"[*] Replaying rows from: {CSV_FILE_PATH}")
    print(f"[*] Interval: {interval} seconds\n")
    
    if not os.path.exists(CSV_FILE_PATH):
        print(f"[!] Error: transactions.csv not found at {CSV_FILE_PATH}")
        return
        
    with open(CSV_FILE_PATH, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
    print(f"[*] Loaded {len(rows)} transactions to replay.")
    
    for i, row in enumerate(rows):
        try:
            payload = {
                "transaction_id": row["transaction_id"],
                "customer_id": row["customer_id"],
                "account_number": row["account_number"],
                "date": row["date"],
                "amount": float(row["amount"]),
                "type": row["type"],
                "description": row["description"],
                "status": row["status"]
            }
        except Exception as e:
            print(f"[!] Error formatting row {i+1}: {e}")
            continue
            
        print(f"[*] Replaying transaction {row['transaction_id']} (CUST: {row['customer_id']}, AMT: {row['amount']})")
        
        try:
            response = requests.post(url, json=payload, timeout=5.0)
            if response.status_code == 200:
                res_data = response.json()
                if res_data.get("nudge_generated"):
                    print(f"    [NUDGE FIRED] for customer {row['customer_id']}: {res_data['nudge']['text']}")
                else:
                    print(f"    [PROCESSED] No nudge triggered.")
            else:
                print(f"    [ERROR] Status Code {response.status_code}: {response.text}")
        except Exception as e:
            print(f"    [CONNECTION ERROR] Could not post transaction: {e}")
            
        time.sleep(interval)
        
    print("[*] Replay completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Replay transaction events to FinSense API")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="Time interval between events in seconds")
    parser.add_argument("--url", type=str, default=TARGET_URL, help="Target URL endpoint")
    args = parser.parse_args()
    
    run_simulator(args.interval, args.url)
