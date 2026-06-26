def send_sms_notification(phone_number: str, message: str):
    """
    Simulates sending an SMS notification to the customer.
    """
    # In production, this would invoke a gateway like Twilio or Karix.
    print(f"[SMS ALERT] Sent to {phone_number}: {message}")
    return {"status": "SUCCESS", "medium": "SMS", "recipient": phone_number, "message": message}

def send_email_notification(email_address: str, subject: str, body: str):
    """
    Simulates sending an email notification to the customer.
    """
    print(f"[EMAIL ALERT] Sent to {email_address} | Subject: {subject} | Body: {body}")
    return {"status": "SUCCESS", "medium": "EMAIL", "recipient": email_address, "subject": subject}

def send_push_notification(customer_id: str, title: str, body: str):
    """
    Simulates sending a push notification to the customer's mobile app.
    """
    print(f"[PUSH ALERT] Sent to CUST:{customer_id} | Title: {title} | Body: {body}")
    return {"status": "SUCCESS", "medium": "PUSH", "recipient": customer_id, "title": title, "body": body}
