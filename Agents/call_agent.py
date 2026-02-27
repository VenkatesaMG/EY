import os
import logging
from typing import Dict, Any
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather

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

    def generate_twiml_for_step(self, provider_id: str, step: str, provider_data: Dict[str, Any], speech_result: str = None) -> str:
        """
        Generates Twilio Markup Language (TwiML) for each step of the conversation.
        """
        response = VoiceResponse()
        
        # Determine the next step based on the current step and speech result
        if step == "start":
            gather = Gather(input='speech', action=f"/twilio/call/{provider_id}/step/verify_name", method="POST", timeout=5)
            gather.say(f"Hello! This is the Health Data Validation team calling for Dr. {provider_data.get('last_name', '')}. Are you available to quickly verify your practice details? Please say yes or no.")
            response.append(gather)
            response.say("We didn't receive any input. Goodbye.")
            response.hangup()
            
        elif step == "verify_name":
            # Check if they said yes
            if speech_result and 'yes' in speech_result.lower():
                gather = Gather(input='speech', action=f"/twilio/call/{provider_id}/step/verify_practice", method="POST", timeout=5)
                practice_name = provider_data.get('practice_name', 'your practice')
                gather.say(f"Great. Can you confirm your practice name is {practice_name}? Say yes, or state the correct practice name.")
                response.append(gather)
            else:
                response.say("Okay, we will try again later. Goodbye.")
                response.hangup()
                
        elif step == "verify_practice":
            gather = Gather(input='speech', action=f"/twilio/call/{provider_id}/step/verify_address", method="POST", timeout=5)
            address = provider_data.get('address_line1', 'your current address')
            city = provider_data.get('city', '')
            gather.say(f"Got it. Is your primary practice address still {address} in {city}? Say yes, or state your new address.")
            response.append(gather)
            
        elif step == "verify_address":
            response.say("Thank you. We have recorded your responses and your profile is now verified. Have a great day! Goodbye.")
            response.hangup()
            
        else:
            response.say("An error occurred. Goodbye.")
            response.hangup()
            
        return str(response)
