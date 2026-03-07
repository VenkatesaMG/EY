import os
import logging
import json
from typing import Dict, Any, Tuple
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from Validation.groq_client import generate_text

logger = logging.getLogger("HealthValidator")

class CallVerificationAgent:
    def __init__(self, webhook_base_url: str = None):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_PHONE_NUMBER")
        
        # This needs to be a public URL (like ngrok) that Twilio can reach
        self.webhook_base_url = webhook_base_url or os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000")
        
        self.is_configured = all([self.account_sid, self.auth_token, self.from_number])
        if self.is_configured:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            logger.warning("⚠️ Twilio credentials missing. Call agent running in SIMULATION mode.")

    def initiate_verification_call(self, provider_id: str, to_number: str, provider_name: str) -> bool:
        """
        Initiates a call to the provider.
        """
        if not to_number:
            logger.error("No phone number provided for the call.")
            return False

        # Format number (Twilio requires E.164, e.g., +1234567890)
        # Assuming to_number might be local, adding +91 for India if missing
        formatted_number = to_number
        formatted_number = ''.join(c for c in formatted_number if c.isdigit() or c == '+')
        if not formatted_number.startswith('+'):
            formatted_number = f"+91{formatted_number}" if len(formatted_number) == 10 else f"+{formatted_number}"

        webhook_url = f"{self.webhook_base_url}/twilio/call/{provider_id}/step/start"
        
        if not self.is_configured:
            logger.info(f"📞 [SIMULATION] Calling {formatted_number} for {provider_name}")
            logger.info(f"   Webhook URL: {webhook_url}")
            return True

        try:
            call = self.client.calls.create(
                to=formatted_number,
                from_=self.from_number,
                url=webhook_url,
                method="POST"
            )
            logger.info(f"✅ Call initiated to {formatted_number} for {provider_name}, SID: {call.sid}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initiate Twilio call: {e}")
            return False

    def generate_twiml_for_step(self, provider_id: str, step: str, provider_data: Dict[str, Any], speech_result: str = None, digits: str = None) -> Tuple[str, dict]:
        """
        Generates Twilio Markup Language (TwiML) for each step of the conversation.
        Returns the XML string and an optional dictionary of extracted updates (if LLM processed it).
        """
        response = VoiceResponse()
        extracted_updates = {}
        
        if step == "start":
            gather = Gather(input='dtmf', numDigits=10, action=f"/twilio/call/{provider_id}/step/verify_npi", method="POST", timeout=10)
            gather.say(f"Hello! This is the Health Data Validation team calling for Dr. {provider_data.get('last_name', '')}. To verify your identity, please enter your 10 digit N.P.I number on your keypad.")
            response.append(gather)
            response.say("We didn't receive your N.P.I. Goodbye.")
            response.hangup()
            
        elif step == "verify_npi":
            if digits and digits == provider_id:
                gather = Gather(input='speech', action=f"/twilio/call/{provider_id}/step/process_update", method="POST", timeout=10)
                gather.say("Thank you. Your identity is verified. What details would you like to update for your practice profile? For example, address, phone number, or practice name.")
                response.append(gather)
            else:
                response.say("The N.P.I number entered is invalid. Goodbye.")
                response.hangup()
                
        elif step == "process_update":
            if speech_result:
                try:
                    # Pass speech result to LLM
                    prompt = f"""
                    You are a data extraction assistant. The healthcare provider just said the following on a phone call:
                    "{speech_result}"
                    
                    Extract the updated information they mentioned. Output a JSON object. Possible keys: "practice_name", "address_line1", "city", "state", "postal_code", "phone", "email", "website", "accepting_new_patients", "telehealth".
                    If no clear data is provided, return an empty object {{}}.
                    """
                    llm_out = generate_text(prompt, json_mode=True)
                    extracted_updates = json.loads(llm_out)
                    
                    response.say("Thank you. We have recorded your updates and will apply them to your profile shortly. Goodbye.")
                    response.hangup()
                except Exception as e:
                    logger.error(f"Error processing LLM update during call: {e}")
                    response.say("An error occurred processing your request. Goodbye.")
                    response.hangup()
            else:
                response.say("We couldn't hear you clearly. Goodbye.")
                response.hangup()
                
        else:
            response.say("Goodbye.")
            response.hangup()
            
        return str(response), extracted_updates
