import os
import time
import json
import threading
import queue
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import ollama
import whisper
import pyttsx3
from typing import Dict, Any

# --- CONFIGURATION ---
MODEL_LLM = "llama3.1"      # Your Ollama model
MODEL_WHISPER = "base"      # Options: tiny, base, small, medium, large
SAMPLE_RATE = 16000         # Whisper expects 16kHz
SILENCE_THRESHOLD = 0.02    # Volume threshold to detect silence
SILENCE_DURATION = 2.0      # Seconds of silence to consider "speaking finished"

class VoiceVerificationAgent:
    def __init__(self):
        print("--- INITIALIZING AI CORES ---")
        
        # 1. The "Ear" (Whisper)
        print(f"Loading Whisper ({MODEL_WHISPER})...")
        self.ear = whisper.load_model(MODEL_WHISPER)
        
        # 2. The "Mouth" (Text-to-Speech)
        print("Initializing TTS Engine...")
        self.mouth = pyttsx3.init()
        self.mouth.setProperty('rate', 175) # Speed of speech
        
        # 3. The "Brain" (Llama 3.1) is accessed via Ollama API calls later
        
        print("--- AGENT READY ---\n")

    # --- SIMULATED DATABASE FETCH ---
    def fetch_provider_profile(self, provider_id: str) -> Dict[str, Any]:
        """
        Simulates fetching 'Live' data from your Postgres DB at the moment of the call.
        """
        print(f"[System] Fetching live record for Provider {provider_id}...")
        
        # Mock Data: Dr. Smith has a confirmed name, but Phone and Accepting status are unverified.
        return {
            "id": provider_id,
            "name": "Dr. Satyasree Upadhyayula",
            "clinic_name": "St. Louis Heart Center",
            "fields_to_verify": {
                "phone_number": {"current_value": "555-0199", "status": "needs_confirmation"},
                "accepting_new_patients": {"current_value": None, "status": "missing"},
                "office_hours": {"current_value": None, "status": "missing"}
            }
        }

    # --- THE "MOUTH" (Text-to-Speech) ---
    def speak(self, text: str):
        """Convert text to audible speech."""
        print(f"\n🤖 Agent: {text}")
        self.mouth.say(text)
        self.mouth.runAndWait()

    # --- THE "EAR" (Microphone -> Whisper) ---
    def listen(self) -> str:
        """
        Records audio from microphone until silence is detected, then transcribes.
        """
        print("\n🎤 [Listening...] (Speak into your mic)")
        
        q = queue.Queue()
        
        def callback(indata, frames, time, status):
            q.put(indata.copy())

        # Start recording
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback):
            audio_data = []
            silent_chunks = 0
            
            while True:
                chunk = q.get()
                audio_data.append(chunk)
                
                # Simple silence detection
                volume = np.linalg.norm(chunk) * 10
                if volume < SILENCE_THRESHOLD:
                    silent_chunks += 1
                else:
                    silent_chunks = 0
                
                # If silence persists for ~2 seconds, stop recording
                if silent_chunks > (SILENCE_DURATION * (SAMPLE_RATE / len(chunk))):
                    break

        # Process Audio
        audio_np = np.concatenate(audio_data, axis=0).flatten()
        
        # Convert to float32 range [-1, 1] for Whisper
        audio_np = audio_np.astype(np.float32)

        # Transcribe
        result = self.ear.transcribe(audio_np, fp16=False) # fp16=False for CPU compatibility
        transcript = result["text"].strip()
        print(f"🗣️ User: {transcript}")
        return transcript

    # --- THE "BRAIN" (Llama 3.1 Decision Logic) ---
    def generate_question(self, field_name: str, context: dict) -> str:
        """Uses Llama 3.1 to formulate a polite, natural question."""
        prompt = f"""
        You are a healthcare verification assistant calling a doctor's office.
        Your goal is to verify the field: '{field_name}'.
        
        Context:
        - Doctor Name: {context['name']}
        - Current Value in DB: {context['fields_to_verify'][field_name]['current_value']}
        
        Task: Generate a single, polite, professional sentence to ask the receptionist for this information.
        Do not include any instructions, just the sentence to speak.
        """
        
        response = ollama.chat(model=MODEL_LLM, messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content'].replace('"', '')

    def verify_answer(self, field_name: str, user_response: str) -> dict:
        """Uses Llama 3.1 to interpret the human's spoken response into structured data."""
        prompt = f"""
        You are a Data Extractor. 
        
        Field being verified: {field_name}
        User's Spoken Response: "{user_response}"
        
        Task: Extract the verified value for the database.
        
        Output JSON format strictly:
        {{
            "verified": true/false,
            "extracted_value": "value or null",
            "confidence": 0.0 to 1.0
        }}
        """
        
        response = ollama.chat(model=MODEL_LLM, messages=[{'role': 'user', 'content': prompt}])
        
        try:
            # Simple cleanup to find JSON if Llama chats a bit
            content = response['message']['content']
            start = content.find('{')
            end = content.rfind('}') + 1
            return json.loads(content[start:end])
        except:
            return {"verified": False, "extracted_value": None, "confidence": 0}

    # --- MAIN EXECUTION FLOW ---
    def start_call(self, provider_id: str):
        # 1. Fetch Real-time Data
        profile = self.fetch_provider_profile(provider_id)
        
        self.speak(f"Hello, I am calling to verify records for {profile['name']}. Do you have a moment?")
        
        # Simple confirmation wait (in real life logic would be more complex)
        response = self.listen()
        if "no" in response.lower() or "busy" in response.lower():
            self.speak("I understand. I will call back later. Goodbye.")
            return

        verified_data = {}

        # 2. Iterate through missing/unverified fields
        fields = profile['fields_to_verify']
        
        for field_name, details in fields.items():
            # A. Brain generates question
            question = self.generate_question(field_name, profile)
            
            # B. Mouth speaks
            self.speak(question)
            
            # C. Ear listens
            user_response = self.listen()
            
            # D. Brain verifies
            if len(user_response) > 2: # Ensure we heard something
                result = self.verify_answer(field_name, user_response)
                
                if result['verified']:
                    verified_data[field_name] = result['extracted_value']
                    print(f"✅ VERIFIED: {field_name} -> {result['extracted_value']}")
                else:
                    print(f"❌ FAILED: Could not understand response for {field_name}")
            
            time.sleep(0.5) # Natural pause

        # 3. Closing
        self.speak("Thank you for your help. Have a great day.")
        
        # 4. Final Data Package
        print("\n--- CALL SUMMARY (Ready for Database Update) ---")
        print(json.dumps(verified_data, indent=2))

if __name__ == "__main__":
    agent = VoiceVerificationAgent()
    # Trigger the call for Provider #101
    agent.start_call(provider_id="101")