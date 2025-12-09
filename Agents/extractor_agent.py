import os
import sys
from pypdf import PdfReader
from dotenv import load_dotenv
import pytesseract
from PIL import Image

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# Schema
from healthcare_schema import HealthcareProviderProfile

load_dotenv()

def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('utf-8', 'ignore').decode('utf-8'))

class HealthcareExtractionModel:
    def __init__(self, api_key: str = None):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
            google_api_key=api_key or os.getenv("GOOGLE_API_KEY")
        )
        self.parser = PydanticOutputParser(pydantic_object=HealthcareProviderProfile)

    def load_pdf_content(self, pdf_path: str) -> str:
        try:
            reader = PdfReader(pdf_path)
            full_text = []
            for page in reader.pages:
                text = page.extract_text() or ""
                full_text.append(text)
            return "\n".join(full_text)
        except Exception as e:
            return f"Error reading PDF: {e}"
    
    def load_img_content(self, img_path: str) -> str:
        try:
            img = Image.open(img_path)
            return pytesseract.image_to_string(img)
        except Exception as e:
            return f"Error reading Image: {e}"

    def extract_provider_data(self, raw_text: str):
        prompt = PromptTemplate(
            template="""
            You are an expert Healthcare Data Extraction Agent.
            
            Your task is to extract 'HealthcareProviderProfile' from the text below.
            
            Focus on extracting:
            - Identity: NPI, Name, Credential (MD, DO, etc.)
            - Professional: Specialties, Board Certifications, Licenses (with State)
            - Operations: Telehealth availability, Accepting New Patients
            - Locations: Full address details for practice locations 
            - Affiliations: Hospital privileges or Payer Networks
            
            If a specific field (like NPI) is not explicitly found in the text, leave it null.
            
            You can also include additional fields that are relevant in identifying the organization or person.
            
            SOURCE TEXT:
            "{text_content}"
            
            FORMAT INSTRUCTIONS:
            {format_instructions}
            """,
            input_variables=["text_content"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )

        chain = prompt | self.llm | self.parser

        try:
            safe_print("--- Analyzing Document for Provider/Organization Data ---")
            result = chain.invoke({"text_content": raw_text})
            return result
        except Exception as e:
            safe_print(f"Extraction Logic Failed: {e}")
            return None

if __name__ == "__main__":
    pdf_path = r"C:\Users\mgven\Downloads\Final_Resume.pdf"

    extractor = HealthcareExtractionModel()
    
    if pdf_path.lower().endswith('.pdf'):
        raw_text = extractor.load_pdf_content(pdf_path)
    else:
        raw_text = extractor.load_img_content(pdf_path)
    
    structured_data = extractor.extract_provider_data(raw_text)
    
    if structured_data:
        safe_print("\n--- EXTRACTION SUCCESSFUL ---")
        
        if structured_data.provider_type == "Organization":
             safe_print(f"Organization: {structured_data.organization_name}")
        else:
             safe_print(f"Provider: {structured_data.first_name} {structured_data.last_name}")
        
        safe_print(f"NPI: {structured_data.npi}")
        
        safe_print("\n--- JSON Output ---")
        safe_print(structured_data.model_dump_json(indent=2))