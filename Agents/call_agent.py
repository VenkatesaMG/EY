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

    def _step_url(self, provider_id: str, step: str, **params) -> str:
        """Helper to build webhook URL for a step, with optional query params."""
        url = f"/twilio/call/{provider_id}/step/{step}"
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
            if query:
                url += f"?{query}"
        return url

    def generate_twiml_for_step(self, provider_id: str, step: str, provider_data: Dict[str, Any], speech_result: str = None, digits: str = None, attempt: int = 1) -> Tuple[str, dict]:
        """
        Generates Twilio Markup Language (TwiML) for each step of the conversation.
        Returns the XML string and an optional dictionary of extracted updates.
        
        Flow:
        start → confirm_identity → verify_npi → explain_purpose → ask_updates
              → process_update → confirm_update → (loop or closing)
        """
        response = VoiceResponse()
        extracted_updates = {}
        provider_name = provider_data.get('last_name', 'Doctor')

        # ─── STEP 1: GREETING ───
        if step == "start":
            gather = Gather(
                input='dtmf', numDigits=1,
                action=self._step_url(provider_id, "confirm_identity"),
                method="POST", timeout=10
            )
            gather.say(
                f"Hello, this is Dhileepan calling from the Credential Validation Team. "
                f"Am I speaking with Doctor {provider_name}? "
                f"Press 1 for yes, or press 2 for no.",
                voice="Polly.Matthew", language="en-US"
            )
            response.append(gather)
            response.say("We didn't receive a response. Goodbye.", voice="Polly.Matthew")
            response.hangup()

        # ─── STEP 2: CONFIRM IDENTITY ───
        elif step == "confirm_identity":
            if digits == "1":
                # Yes — ask for NPI
                gather = Gather(
                    input='dtmf', numDigits=10,
                    action=self._step_url(provider_id, "verify_npi", attempt=1),
                    method="POST", timeout=15
                )
                gather.say(
                    "Thank you. For security purposes, please verify your identity "
                    "by entering your 10 digit N P I number on your keypad.",
                    voice="Polly.Matthew"
                )
                response.append(gather)
                response.say("We didn't receive your N P I. Goodbye.", voice="Polly.Matthew")
                response.hangup()
            elif digits == "2":
                # Not the provider
                response.say(
                    "We apologize for the inconvenience. We will try calling back at another time. Goodbye.",
                    voice="Polly.Matthew"
                )
                response.hangup()
            else:
                response.say("Invalid input. Goodbye.", voice="Polly.Matthew")
                response.hangup()

        # ─── STEP 3: VERIFY NPI (with retries) ───
        elif step == "verify_npi":
            if digits and digits == provider_id:
                # NPI correct — move to explain purpose
                gather = Gather(
                    input='dtmf', numDigits=1,
                    action=self._step_url(provider_id, "explain_purpose"),
                    method="POST", timeout=10
                )
                gather.say(
                    "Thank you, your identity has been verified. "
                    "We are validating the information on your practice profile. "
                    "I will quickly confirm or update a few details to ensure our records are accurate. "
                    "Would you like to update any of your practice details today? "
                    "Press 1 for yes, or press 2 for no.",
                    voice="Polly.Matthew"
                )
                response.append(gather)
                response.say("We didn't receive a response. Goodbye.", voice="Polly.Matthew")
                response.hangup()
            else:
                # NPI incorrect — retry logic
                if attempt < 3:
                    next_attempt = attempt + 1
                    gather = Gather(
                        input='dtmf', numDigits=10,
                        action=self._step_url(provider_id, "verify_npi", attempt=next_attempt),
                        method="POST", timeout=15
                    )
                    gather.say(
                        f"The N P I number entered is incorrect. "
                        f"You have {3 - attempt} attempts remaining. "
                        f"Please try again.",
                        voice="Polly.Matthew"
                    )
                    response.append(gather)
                    response.say("We didn't receive your N P I. Goodbye.", voice="Polly.Matthew")
                    response.hangup()
                else:
                    response.say(
                        "You have exceeded the maximum number of attempts. "
                        "For security, this call will now end. Goodbye.",
                        voice="Polly.Matthew"
                    )
                    response.hangup()

        # ─── STEP 4: EXPLAIN PURPOSE & ASK IF UPDATES NEEDED ───
        elif step == "explain_purpose":
            if digits == "1":
                # Yes, wants updates — gather speech
                gather = Gather(
                    input='speech', 
                    action=self._step_url(provider_id, "process_update"),
                    method="POST", timeout=15,
                    speechTimeout=3
                )
                gather.say(
                    "Great. You can update any of the following: "
                    "practice name, practice address, phone number, email, website, "
                    "telehealth availability, or whether you are accepting new patients. "
                    "Please tell me what you would like to update.",
                    voice="Polly.Matthew"
                )
                response.append(gather)
                response.say("We couldn't hear you clearly. Goodbye.", voice="Polly.Matthew")
                response.hangup()
            elif digits == "2":
                # No updates needed
                response.redirect(self._step_url(provider_id, "no_updates"), method="POST")
            else:
                response.say("Invalid input. Goodbye.", voice="Polly.Matthew")
                response.hangup()

        # ─── STEP 5: PROCESS UPDATE (LLM extraction + read back) ───
        elif step == "process_update":
            if speech_result:
                try:
                    prompt = f"""You are a data extraction assistant. A healthcare provider said the following on a verification phone call:
"{speech_result}"

Extract the updated information they mentioned. Output a JSON object with ONLY these possible keys:
"practice_name", "address_line1", "city", "state", "postal_code", "phone", "email", "website", "accepting_new_patients", "telehealth"

Rules:
- Only include keys where the provider clearly stated a new value.
- For "accepting_new_patients" and "telehealth", use boolean true/false.
- For addresses, split into address_line1, city, state, postal_code if possible.
- If no clear data is provided, return an empty object {{}}.
- Return ONLY valid JSON, no explanation."""

                    llm_out = generate_text(prompt, json_mode=True)
                    extracted_updates = json.loads(llm_out)
                    
                    if extracted_updates:
                        # Build a human-readable summary of what was extracted
                        summary_parts = []
                        field_labels = {
                            "practice_name": "practice name",
                            "address_line1": "address",
                            "city": "city",
                            "state": "state",
                            "postal_code": "postal code",
                            "phone": "phone number",
                            "email": "email",
                            "website": "website",
                            "accepting_new_patients": "accepting new patients",
                            "telehealth": "telehealth availability"
                        }
                        for key, val in extracted_updates.items():
                            label = field_labels.get(key, key)
                            summary_parts.append(f"Your {label} is {val}")
                        
                        summary_text = ". ".join(summary_parts)
                        
                        # Store updates temporarily in the URL as base64 JSON
                        import base64
                        updates_encoded = base64.urlsafe_b64encode(
                            json.dumps(extracted_updates).encode()
                        ).decode()
                        
                        gather = Gather(
                            input='dtmf', numDigits=1,
                            action=self._step_url(provider_id, "confirm_update", data=updates_encoded),
                            method="POST", timeout=15
                        )
                        gather.say(
                            f"I heard the following update. {summary_text}. "
                            f"If this is correct, press 1. "
                            f"To re-enter the information, press 2.",
                            voice="Polly.Matthew"
                        )
                        response.append(gather)
                        response.say("We didn't receive a response. Goodbye.", voice="Polly.Matthew")
                        response.hangup()
                    else:
                        # LLM couldn't extract anything
                        gather = Gather(
                            input='speech',
                            action=self._step_url(provider_id, "process_update"),
                            method="POST", timeout=15,
                            speechTimeout=3
                        )
                        gather.say(
                            "I'm sorry, I couldn't understand the update. "
                            "Could you please repeat what you would like to change?",
                            voice="Polly.Matthew"
                        )
                        response.append(gather)
                        response.say("We couldn't hear you clearly. Goodbye.", voice="Polly.Matthew")
                        response.hangup()

                except Exception as e:
                    logger.error(f"Error processing LLM update during call: {e}")
                    response.say(
                        "I'm sorry, an error occurred processing your request. "
                        "Your existing information has not been changed. Goodbye.",
                        voice="Polly.Matthew"
                    )
                    response.hangup()
            else:
                # No speech captured
                gather = Gather(
                    input='speech',
                    action=self._step_url(provider_id, "process_update"),
                    method="POST", timeout=15,
                    speechTimeout=3
                )
                gather.say(
                    "I'm sorry, I couldn't hear you clearly. "
                    "Please tell me what you would like to update.",
                    voice="Polly.Matthew"
                )
                response.append(gather)
                response.say("We still couldn't hear you. Goodbye.", voice="Polly.Matthew")
                response.hangup()

        # ─── STEP 6: CONFIRM UPDATE ───
        elif step == "confirm_update":
            if digits == "1":
                # Confirmed — the backend will save the updates
                # Ask if more updates
                gather = Gather(
                    input='dtmf', numDigits=1,
                    action=self._step_url(provider_id, "more_updates"),
                    method="POST", timeout=10
                )
                gather.say(
                    "Thank you. Your update has been recorded. "
                    "Would you like to update anything else today? "
                    "Press 1 for yes, or press 2 for no.",
                    voice="Polly.Matthew"
                )
                response.append(gather)
                # Default to closing if no response
                response.redirect(self._step_url(provider_id, "closing"), method="POST")

            elif digits == "2":
                # Re-enter — go back to speech capture
                gather = Gather(
                    input='speech',
                    action=self._step_url(provider_id, "process_update"),
                    method="POST", timeout=15,
                    speechTimeout=3
                )
                gather.say(
                    "No problem. Please tell me the details you would like to update again.",
                    voice="Polly.Matthew"
                )
                response.append(gather)
                response.say("We couldn't hear you. Goodbye.", voice="Polly.Matthew")
                response.hangup()
            else:
                response.say("Invalid input. Goodbye.", voice="Polly.Matthew")
                response.hangup()

        # ─── STEP 7: MORE UPDATES? ───
        elif step == "more_updates":
            if digits == "1":
                # Yes — loop back to speech capture
                gather = Gather(
                    input='speech',
                    action=self._step_url(provider_id, "process_update"),
                    method="POST", timeout=15,
                    speechTimeout=3
                )
                gather.say(
                    "Please tell me the next detail you would like to update.",
                    voice="Polly.Matthew"
                )
                response.append(gather)
                response.say("We couldn't hear you. Goodbye.", voice="Polly.Matthew")
                response.hangup()
            else:
                # No more updates — go to closing
                response.redirect(self._step_url(provider_id, "closing"), method="POST")

        # ─── NO UPDATES PATH ───
        elif step == "no_updates":
            response.say(
                "Thank you. Your profile information remains unchanged. "
                "We appreciate your time. Have a great day. Goodbye.",
                voice="Polly.Matthew"
            )
            response.hangup()

        # ─── CLOSING ───
        elif step == "closing":
            response.say(
                "Thank you for helping us keep your credentials up to date. "
                "Have a great day. Goodbye.",
                voice="Polly.Matthew"
            )
            response.hangup()

        # ─── FALLBACK ───
        else:
            response.say("Goodbye.", voice="Polly.Matthew")
            response.hangup()
            
        return str(response), extracted_updates
