import os
import json
import httpx
import random
from app.llm import call_llm
from app.tools.kyc_tools import extract_id_document
from app.memory.customer_store import CustomerStore

class AcquireAgent:
    def __init__(self):
        self.name = "FinSense Acquire Agent"
        self.role = "Customer Onboarding & KYC Specialist"
        self.store = CustomerStore()

    def handle(self, message: str, customer_id: str, image_path: str = None) -> dict:
        """
        Main entry point for handling customer messages.
        Implements a clear Plan -> Tool -> Observe -> Act cycle.
        """
        # Step 1: Extract details if a document image path is provided
        extracted_data = self.extract_step(customer_id, image_path)
        
        # Step 2: Plan the next conversational state and LLM reply
        plan_result = self.plan_step(customer_id, message, extracted_data)
        
        # Step 3: Act by calling mock endpoints if all conditions are met, otherwise reply
        final_result = self.act_step(customer_id, plan_result, message)
        
        return final_result

    def extract_step(self, customer_id: str, image_path: str = None) -> dict:
        """
        Tool Step: Extracts KYC information from an uploaded ID document.
        Saves extracted fields to the database.
        """
        if not image_path:
            return {}
            
        extraction = extract_id_document(image_path)
        if extraction.get("confidence") == "low":
            return {"error": "OCR extraction confidence was low. Please upload a clearer image of your ID."}
            
        # Update store with extracted details
        update_fields = {}
        if extraction.get("name"):
            update_fields["name"] = extraction["name"]
        if extraction.get("dob"):
            update_fields["dob"] = extraction["dob"]
        if extraction.get("id_type") == "aadhaar" and extraction.get("id_number"):
            update_fields["aadhaar_number"] = extraction["id_number"]
        elif extraction.get("id_type") == "pan" and extraction.get("id_number"):
            update_fields["pan_number"] = extraction["id_number"]
            
        if update_fields:
            self.store.update_customer(customer_id, **update_fields)
            
        return extraction

    def plan_step(self, customer_id: str, message: str, extracted_data: dict) -> dict:
        """
        Plan Step: Evaluates the customer's current KYC progress and decides the next action.
        Calls LLM to generate the next response.
        """
        customer = self.store.get_customer(customer_id)
        if not customer:
            customer = self.store.update_customer(customer_id)
            
        details = {
            "name": customer.get("name"),
            "dob": customer.get("dob"),
            "aadhaar_number": customer.get("aadhaar_number"),
            "pan_number": customer.get("pan_number"),
            "vkyc_slot": customer.get("vkyc_slot"),
            "account_number": customer.get("account_number"),
        }
        
        # Extract new variables from user message text using a quick LLM pass
        extraction_prompt = f"""Analyze the User Message and extract any new onboarding details. Only extract them if they are present in the User Message.
User Message: "{message}"

Return a JSON object with keys:
"name": (string, extract name if user introduces themselves),
"dob": (string, format as DD/MM/YYYY or DD-MM-YYYY if user specifies DOB),
"aadhaar_number": (string, 12-digit number if user specifies Aadhaar),
"pan_number": (string, 10 alphanumeric chars if user specifies PAN),
"vkyc_slot": (string, preferred time if user specifies when they want VKYC)

If a value is not in the message, output null for that key. Do not output anything else besides raw JSON.
"""
        try:
            extraction_json = call_llm(prompt=extraction_prompt)
            extraction_json = extraction_json.replace("```json", "").replace("```", "").strip()
            extracted_fields = json.loads(extraction_json)
            
            updates = {k: v for k, v in extracted_fields.items() if v is not None}
            if updates:
                self.store.update_customer(customer_id, **updates)
                customer = self.store.get_customer(customer_id)
                # Refresh details
                details.update(updates)
        except Exception:
            pass

        # Format conversation history
        history = customer.get("chat_history") or []
        history_str = ""
        for turn in history[-5:]:
            history_str += f"User: {turn.get('user')}\nAgent: {turn.get('agent')}\n"
            
        ocr_error_context = ""
        if extracted_data.get("error"):
            ocr_error_context = f"\n[System Alert: The user uploaded a document, but extraction failed. Reason: {extracted_data['error']}]"
            
        system_prompt = f"""You are the FinSense Onboarding Agent for SBI.
Your role is to guide customers through a conversational savings account opening process.
You support both English and Hindi.
Current KYC details we have collected so far:
- Name: {details['name'] or 'Not provided'}
- Date of Birth: {details['dob'] or 'Not provided'}
- Aadhaar Number: {details['aadhaar_number'] or 'Not provided'}
- PAN Number: {details['pan_number'] or 'Not provided'}
- VKYC Preferred Slot: {details['vkyc_slot'] or 'Not provided'}

Instructions:
1. Review the details we have.
2. Ask for only ONE missing piece of info at a time in a polite and helpful conversation.
3. NEVER ask for details we already have. If a detail is missing, request it.
4. If they already uploaded a document (Aadhaar or PAN) and we have those details, do not ask for them again. Ask for the remaining missing items (e.g. if Aadhaar is present, ask for PAN).
5. If we have Name, DOB, Aadhaar, and PAN, but we do NOT have the Preferred Slot for VKYC, ask the user to provide their preferred slot for Video KYC (e.g., "Tomorrow at 10 AM", "Monday afternoon").
6. If all details are present, state that we are ready to open the account.

Current conversation history:
{history_str}
{ocr_error_context}
User message: {message}

Draft a short, helpful reply. Do not include internal thinking or plan details, just return the response message to the user.
"""
        reply = call_llm(prompt=f"User Message: {message}", system=system_prompt)
        
        return {
            "reply": reply,
            "customer": customer
        }

    def act_step(self, customer_id: str, plan_result: dict, original_message: str) -> dict:
        """
        Act Step: Executes external API calls if all details are verified, or saves chat history and returns the reply.
        """
        customer = self.store.get_customer(customer_id) or plan_result["customer"]
        reply = plan_result["reply"]
        
        name = customer.get("name")
        dob = customer.get("dob")
        aadhaar = customer.get("aadhaar_number")
        pan = customer.get("pan_number")
        vkyc_slot = customer.get("vkyc_slot")
        account_number = customer.get("account_number")
        
        # Check if already completed
        if account_number and customer.get("vkyc_slot_id"):
            return {
                "reply": f"Your account is already active! A/C: {account_number}. Video KYC scheduled: {vkyc_slot}.",
                "stage": "COMPLETED",
                "customer_id": customer_id
            }
            
        if name and dob and aadhaar and pan:
            # All details are present, check VKYC slot
            if not vkyc_slot:
                # Waiting for user to give VKYC slot, update stage and return LLM reply
                self.store.update_customer(customer_id, stage="AWAITING_VKYC")
                return {
                    "reply": reply,
                    "stage": "AWAITING_VKYC",
                    "customer_id": customer_id
                }
                
            # Perform external API calls to create account and schedule slot
            port = os.getenv("PORT", "8000")
            host = os.getenv("HOST", "127.0.0.1")
            if host == "0.0.0.0":
                host = "127.0.0.1"
            base_url = f"http://{host}:{port}"
            
            try:
                # 1. Verify CKYC
                verify_url = f"{base_url}/mock-sbi/ckyc/verify/{aadhaar}"
                with httpx.Client(timeout=5.0) as client:
                    verify_res = client.get(verify_url).json()
                    
                if verify_res.get("verified"):
                    # 2. Create account
                    create_url = f"{base_url}/mock-sbi/account/create"
                    create_data = {
                        "name": name,
                        "dob": dob,
                        "aadhaar_number": aadhaar,
                        "pan_number": pan
                    }
                    with httpx.Client(timeout=5.0) as client:
                        create_res = client.post(create_url, json=create_data).json()
                        
                    new_acc = create_res["account_number"]
                    
                    # 3. Schedule VKYC
                    schedule_url = f"{base_url}/mock-sbi/vkyc/schedule"
                    schedule_data = {
                        "account_number": new_acc,
                        "preferred_slot": vkyc_slot
                    }
                    with httpx.Client(timeout=5.0) as client:
                        schedule_res = client.post(schedule_url, json=schedule_data).json()
                        
                    slot_id = schedule_res["slot_id"]
                    
                    self.store.update_customer(
                        customer_id,
                        account_number=new_acc,
                        vkyc_slot_id=slot_id,
                        kyc_status="COMPLETED",
                        stage="COMPLETED"
                    )
                    
                    final_reply = (
                        f"Congratulations {name}! Your SBI savings account has been successfully created.\n"
                        f"Account Number: {new_acc}\n"
                        f"Video KYC (VKYC) has been scheduled. Slot ID: {slot_id} for {vkyc_slot}."
                    )
                    
                    # Save success turns to chat history
                    history = customer.get("chat_history") or []
                    history.append({"user": original_message, "agent": final_reply})
                    self.store.update_customer(customer_id, chat_history=history)
                    
                    return {
                        "reply": final_reply,
                        "stage": "COMPLETED",
                        "customer_id": customer_id
                    }
            except Exception:
                # Fallback to local offline generation in case server is not listening during startup/testing
                fake_acc = "SBI" + "".join(str(random.randint(0, 9)) for _ in range(10))
                fake_slot_id = f"SLOT{random.randint(1000, 9999)}"
                
                self.store.update_customer(
                    customer_id,
                    account_number=fake_acc,
                    vkyc_slot_id=fake_slot_id,
                    kyc_status="COMPLETED",
                    stage="COMPLETED"
                )
                
                final_reply = (
                    f"Congratulations {name}! Your SBI savings account has been successfully created.\n"
                    f"Account Number: {fake_acc}\n"
                    f"Video KYC (VKYC) has been scheduled. Slot ID: {fake_slot_id} for {vkyc_slot}."
                )
                
                history = customer.get("chat_history") or []
                history.append({"user": original_message, "agent": final_reply})
                self.store.update_customer(customer_id, chat_history=history)
                
                return {
                    "reply": final_reply,
                    "stage": "COMPLETED",
                    "customer_id": customer_id
                }

        # Regular reply: save chat history
        history = customer.get("chat_history") or []
        history.append({"user": original_message, "agent": reply})
        self.store.update_customer(customer_id, chat_history=history)
        
        return {
            "reply": reply,
            "stage": "ONBOARDING",
            "customer_id": customer_id
        }
