import os
import json
import pandas as pd
import networkx as nx

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
CUSTOMERS_FILE = os.path.join(DATA_DIR, "customers.json")
TRANSACTIONS_FILE = os.path.join(DATA_DIR, "transactions.csv")

class CustomerGraphStore:
    def __init__(self):
        self.G = nx.MultiDiGraph()
        self.rebuild_graph()

    def rebuild_graph(self):
        self.G.clear()
        
        # Load customers
        if os.path.exists(CUSTOMERS_FILE):
            with open(CUSTOMERS_FILE, "r") as f:
                customers = json.load(f)
        else:
            customers = []

        # Load transactions
        transactions = []
        if os.path.exists(TRANSACTIONS_FILE):
            try:
                df = pd.read_csv(TRANSACTIONS_FILE)
                transactions = df.to_dict(orient="records")
            except Exception:
                pass

        # Build Graph
        for cust in customers:
            cust_node = cust["customer_id"]
            self.G.add_node(
                cust_node,
                type="Customer",
                label=cust["name"],
                kyc_status=cust["kyc_status"],
                risk_score=cust["risk_score"],
                email=cust["email"],
                phone=cust["phone"]
            )
            
            # Risk level nodes
            risk_level = "Low Risk"
            if cust["risk_score"] > 70:
                risk_level = "High Risk"
            elif cust["risk_score"] > 30:
                risk_level = "Medium Risk"
                
            self.G.add_node(risk_level, type="RiskCategory", label=risk_level)
            self.G.add_edge(cust_node, risk_level, relation="HAS_RISK_PROFILE")

            # Account nodes
            for acc in cust["accounts"]:
                acc_node = acc["account_number"]
                self.G.add_node(
                    acc_node,
                    type="Account",
                    label=f"A/C: {acc_node[-4:]}",
                    balance=acc["balance"],
                    upi_id=acc["upi_id"]
                )
                self.G.add_edge(cust_node, acc_node, relation="OWNS_ACCOUNT")
                
                # Product interests node (e.g. Savings)
                self.G.add_node("SAVINGS", type="Product", label="Savings Account")
                self.G.add_edge(acc_node, "SAVINGS", relation="PRODUCT_TYPE")

        # Transaction links & entities
        for txn in transactions:
            cust_node = txn["customer_id"]
            acc_node = txn["account_number"]
            
            # Check if customer has transaction risk
            if "crypto" in str(txn["description"]).lower():
                risk_node = "Crypto Activity"
                self.G.add_node(risk_node, type="RiskIndicator", label="Crypto Flag")
                self.G.add_edge(cust_node, risk_node, relation="TRIGGERED_RISK", txn_id=txn["transaction_id"])
            
            # Transfer transactions
            if "UPI to" in str(txn["description"]):
                receiver_upi = str(txn["description"]).split("UPI to ")[1].split(" - ")[0]
                # Find if receiver is another customer
                receiver_node = None
                for cust in customers:
                    for acc in cust["accounts"]:
                        if acc["upi_id"] == receiver_upi:
                            receiver_node = cust["customer_id"]
                            break
                
                if receiver_node:
                    self.G.add_edge(cust_node, receiver_node, relation="TRANSFERRED_FUNDS", amount=txn["amount"], txn_id=txn["transaction_id"])

    def get_graph_data(self):
        """Returns JSON-compatible nodes and links for frontend visualizations."""
        self.rebuild_graph()
        
        nodes = []
        for n, data in self.G.nodes(data=True):
            node_data = {"id": n}
            node_data.update(data)
            nodes.append(node_data)
            
        links = []
        for u, v, data in self.G.edges(data=True):
            link_data = {"source": u, "target": v}
            link_data.update(data)
            links.append(link_data)
            
        return {"nodes": nodes, "links": links}

    def add_product_interest(self, customer_id: str, product_name: str):
        """Adds a product interest node and edge for a customer."""
        self.G.add_node(product_name, type="Product", label=product_name)
        self.G.add_edge(customer_id, product_name, relation="INTERESTED_IN")
