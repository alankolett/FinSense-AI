import sqlite3
import os
import json

DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
DB_PATH = os.path.join(DB_DIR, "customer_store.db")

class CustomerStore:
    def __init__(self):
        os.makedirs(DB_DIR, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id TEXT PRIMARY KEY,
                    name TEXT,
                    dob TEXT,
                    aadhaar_number TEXT,
                    pan_number TEXT,
                    kyc_status TEXT DEFAULT 'PENDING',
                    account_number TEXT,
                    vkyc_slot_id TEXT,
                    vkyc_slot TEXT,
                    stage TEXT DEFAULT 'ONBOARDING',
                    chat_history TEXT
                )
            """)
            conn.commit()
            
            # Migration to add pending_nudge column if it doesn't exist yet
            try:
                cursor.execute("ALTER TABLE customers ADD COLUMN pending_nudge TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass # Column already exists

    def get_customer(self, customer_id: str) -> dict:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))
            row = cursor.fetchone()
            if row:
                d = dict(row)
                if d.get("chat_history"):
                    try:
                        d["chat_history"] = json.loads(d["chat_history"])
                    except Exception:
                        d["chat_history"] = []
                else:
                    d["chat_history"] = []
                return d
            return None

    def update_customer(self, customer_id: str, **fields) -> dict:
        existing = self.get_customer(customer_id)
        
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            if not existing:
                cursor.execute(
                    "INSERT INTO customers (customer_id, kyc_status, stage) VALUES (?, 'PENDING', 'ONBOARDING')",
                    (customer_id,)
                )
                conn.commit()

            # Prepare update statements
            updated_fields = {}
            for k, v in fields.items():
                if k == "chat_history" and isinstance(v, list):
                    updated_fields[k] = json.dumps(v)
                else:
                    updated_fields[k] = v

            if updated_fields:
                placeholders = ", ".join([f"{k} = ?" for k in updated_fields.keys()])
                values = list(updated_fields.values()) + [customer_id]
                cursor.execute(f"UPDATE customers SET {placeholders} WHERE customer_id = ?", values)
                conn.commit()

        return self.get_customer(customer_id)
