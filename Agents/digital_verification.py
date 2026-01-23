import uuid
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# In reality, these would be your Postgres tables
provider_db = {
    "101": {
        "name": "Dr. Satyasree Upadhyayula",
        "email": "dr.satyasree@example.com",
        "phone": "555-0199",           # Unverified
        "accepting_new": None          # Missing
    }
}

# Stores the secure tokens (token -> provider_id)
verification_tokens = {}

app = FastAPI()

# --- 2. SENDING THE REQUEST (Triggered by your System) ---

class VerificationRequest(BaseModel):
    provider_id: str

@app.post("/verify/trigger_email")
def trigger_verification(payload: VerificationRequest):
    pid = payload.provider_id
    if pid not in provider_db:
        raise HTTPException(404, "Provider not found")
    
    # Generate a unique, secure token valid for 3 days
    token = str(uuid.uuid4())
    verification_tokens[token] = {
        "provider_id": pid,
        "expires_at": datetime.utcnow() + timedelta(days=3),
        "status": "pending"
    }
    
    # Create the "Magic Link"
    # In production, use your actual domain (e.g., https://app.insurance.com/...)
    magic_link = f"http://localhost:8000/verify/{token}"
    
    # SIMULATE SENDING EMAIL
    print(f"\n[EMAIL SENT] To: {provider_db[pid]['email']}")
    print(f"Subject: Action Required - Verify Directory Information")
    print(f"Body: Dear {provider_db[pid]['name']}, please confirm your practice details by clicking here: {magic_link}\n")
    
    return {"status": "sent", "link": magic_link}

# --- 3. THE PROVIDER'S VIEW (The Web Form) ---

@app.get("/verify/{token}", response_class=HTMLResponse)
def show_verification_form(token: str):
    # Security Checks
    record = verification_tokens.get(token)
    if not record:
        return "<h1>Error: Invalid or Expired Link</h1>"
    
    if record['status'] == 'completed':
        return "<h1>You have already verified this profile. Thank you!</h1>"
    
    # Fetch current data to pre-fill the form
    provider = provider_db[record['provider_id']]
    
    # A simple, clean HTML form
    return f"""
    <html>
        <body style="font-family: sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; border: 1px solid #ccc;">
            <h2>Verify Practice Details</h2>
            <p><strong>Provider:</strong> {provider['name']}</p>
            <p>Please update or confirm the information below.</p>
            
            <form action="/verify/{token}/submit" method="post">
                <label><strong>Office Phone Number:</strong></label><br>
                <input type="text" name="phone" value="{provider['phone']}" style="width: 100%; padding: 8px; margin-bottom: 15px;"><br>
                
                <label><strong>Accepting New Patients?</strong></label><br>
                <select name="accepting_new" style="width: 100%; padding: 8px; margin-bottom: 15px;">
                    <option value="Yes" selected>Yes</option>
                    <option value="No">No</option>
                </select><br>
                
                <button type="submit" style="background-color: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer;">
                    Confirm & Submit
                </button>
            </form>
        </body>
    </html>
    """

# --- 4. HANDLING THE SUBMISSION (The Update) ---

@app.post("/verify/{token}/submit", response_class=HTMLResponse)
def process_submission(token: str, phone: str = Form(...), accepting_new: str = Form(...)):
    record = verification_tokens.get(token)
    if not record:
        return "Error: Invalid Token"
    
    pid = record['provider_id']
    
    # UPDATE THE DATABASE
    # In a real app, you would run a SQL UPDATE here
    provider_db[pid]['phone'] = phone
    provider_db[pid]['accepting_new'] = (accepting_new == "Yes")
    
    # Invalidate token so it can't be used again
    record['status'] = 'completed'
    
    print(f"\n[DATABASE UPDATED] Provider {pid}: Phone={phone}, Accepting={accepting_new}")
    
    return """
    <div style="text-align: center; margin-top: 50px; font-family: sans-serif;">
        <h1 style="color: green;">✔ Verification Complete</h1>
        <p>Your profile has been updated in our directory.</p>
    </div>
    """

if __name__ == "__main__":
    import uvicorn
    print("--- DIGITAL VERIFICATION AGENT RUNNING ---")
    print("Use the API to trigger an email, then click the link to test.")
    uvicorn.run(app, host="127.0.0.1", port=8000)