import sys
import os
import shutil
from typing import List, Optional
from uuid import uuid4

# Add parent directory to path to allow importing from Agents
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import csv
import io
import codecs

from database import get_db, init_db
from models import Provider, RawProviderSubmission
from Agents.extractor_agent import HealthcareExtractionModel
from services import ValidationService
import logging

# Configure clean, readable logging
logging.basicConfig(
    level=logging.INFO,
    format='\033[36m%(asctime)s\033[0m | \033[33m%(levelname)-8s\033[0m | %(message)s',
    datefmt='%H:%M:%S'
)
# Reduce noise from other libraries
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

logger = logging.getLogger("HealthValidator")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    await init_db()

# --- Endpoints ---

@app.post("/onboard/extract")
async def extract_data(file: UploadFile = File(...)):
    """
    Uploads a file (PDF/Image), runs OCR + LLM extraction, and returns the simplified JSON.
    """
    try:
        temp_filename = f"temp_{uuid4()}_{file.filename}"
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        extractor = HealthcareExtractionModel()
        
        raw_text = ""
        if temp_filename.lower().endswith(".pdf"):
            raw_text = extractor.load_pdf_content(temp_filename)
        else:
            raw_text = extractor.load_img_content(temp_filename)
            
        extracted_data = extractor.extract_provider_data(raw_text)
        
        os.remove(temp_filename)
        
        if not extracted_data:
             raise HTTPException(status_code=422, detail="Failed to extract data")

        return extracted_data.dict()
        
    except Exception as e:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/onboard/submit")
async def submit_provider(
    background_tasks: BackgroundTasks,
    data: dict = Body(...), 
    db: AsyncSession = Depends(get_db)
):
    try:
        logger.info(f"📨 New Submission: NPI={data.get('npi')} | Name={data.get('first_name', '')} {data.get('last_name', '')}")
        
        # Create Raw Submission
        submission = RawProviderSubmission(
            source="form",
            npi=data.get("npi"),
            input_payload=data,
            processing_status="queued" # Initial state
        )
        
        db.add(submission)
        await db.commit()
        await db.refresh(submission)
        
        # Trigger validation in BACKGROUND
        # This allows immediate response to UI so it can start polling/visualizing
        background_tasks.add_task(ValidationService.process_submission, submission, db)
        
        return {
            "message": "Submission queued", 
            "submission_id": submission.submission_id,
            "status": "queued"
        }
        
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/submissions/{submission_id}")
async def get_submission_status(submission_id: int, db: AsyncSession = Depends(get_db)):
    """
    Poll this endpoint to get the status of the pipeline steps.
    """
    # Fetch Submission
    result = await db.execute(select(RawProviderSubmission).filter(RawProviderSubmission.submission_id == submission_id))
    submission = result.scalars().first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
        
    # Fetch associated Provider (if created/linked)
    # We can link by NPI since that's unique enough for this flow, or add provider_id to submission table later.
    provider_data = None
    if submission.npi:
        p_res = await db.execute(select(Provider).filter(Provider.npi == submission.npi))
        provider = p_res.scalars().first()
        if provider:
            provider_data = {
                "id": provider.provider_id,
                "status": provider.status,
                "overall_confidence": provider.overall_confidence,
                "npi_status": provider.npi_status,
                "name_status": provider.name_status,
                "address_status": provider.address_status
            }

    # Compute step statuses based on processing_status
    status = submission.processing_status
    
    # Step status logic:
    # - queued: just submitted, nothing started
    # - npi_lookup: NPI lookup in progress
    # - validating: AI validation in progress  
    # - enriching: enrichment in progress
    # - processed: completed without enrichment
    # - enriched: completed with enrichment
    # - failed*: various failure states
    
    def get_step_status(step_name):
        if step_name == "submitted":
            return "completed"
        
        elif step_name == "npi_lookup":
            if status == "queued":
                return "pending"
            elif status == "npi_lookup":
                return "in_progress"
            elif status in ["failed", "rejected_invalid_npi"]:
                return "failed" if not submission.npi_api_response else "completed"
            else:
                return "completed" if submission.npi_api_response else "pending"
        
        elif step_name == "ai_validation":
            if status in ["queued", "npi_lookup"]:
                return "pending"
            elif status == "validating":
                return "in_progress"
            elif status == "failed_validation":
                return "failed"
            elif status in ["processed", "enriching", "enriched"]:
                return "completed"
            else:
                return "completed" if provider_data else "pending"
        
        elif step_name == "enrichment":
            if status in ["queued", "npi_lookup", "validating"]:
                return "pending"
            elif status == "enriching":
                return "in_progress"
            elif status == "enriched":
                return "completed"
            elif status == "processed":
                # Processed without enrichment - mark as completed (skipped)
                return "completed"
            else:
                return "pending"
        
        return "pending"

    return {
        "submission_id": submission.submission_id,
        "processing_status": submission.processing_status,
        "error_message": submission.error_message,
        "npi": submission.npi,
        "provider": provider_data,
        "steps": {
            "submitted": get_step_status("submitted"),
            "npi_lookup": get_step_status("npi_lookup"),
            "ai_validation": get_step_status("ai_validation"),
            "enrichment": get_step_status("enrichment")
        }
    }

@app.post("/onboard/csv")
async def onboard_csv_upload(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """
    Batch processing for CSV.
    Expected CSV columns: npi, first_name, last_name, address, city, state, zip_code, etc.
    """
    try:
        csv_file = io.TextIOWrapper(file.file, encoding="utf-8")
        reader = csv.DictReader(csv_file)
        
        submissions_created = []
        
        for row in reader:
            # Clean inputs
            npi_val = row.get("npi") or row.get("National Provider Identifier")
            if npi_val:
                npi_val = npi_val.strip()

            submission = RawProviderSubmission(
                source="csv",
                npi=npi_val,
                input_payload=row,
                processing_status="pending"
            )
            db.add(submission)
            submissions_created.append(submission)
        
        await db.commit()
        
        # Process batch (sequentially for now to avoid overloading free tier usage if any)
        # In prod this would be background tasks
        processed_count = 0
        for sub in submissions_created:
            await db.refresh(sub)
            await ValidationService.process_submission(sub, db)
            processed_count += 1
            
        return {
            "message": f"Successfully processed {processed_count} submissions from CSV."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV processing failed: {str(e)}")

@app.get("/providers")
async def list_providers(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Provider).offset(skip).limit(limit).order_by(Provider.created_at.desc()))
    providers = result.scalars().all()
    # Convert to dict for proper JSON serialization
    return [{
        "provider_id": p.provider_id,
        "npi": p.npi,
        "display_name": p.display_name,
        "first_name": p.first_name,
        "last_name": p.last_name,
        "practice_name": p.practice_name,
        "email": p.email,
        "phone": p.phone,
        "address_line1": p.address_line1,
        "city": p.city,
        "state": p.state,
        "postal_code": p.postal_code,
        "specialties": p.specialties,
        "overall_confidence": p.overall_confidence,
        "status": p.status,
        "npi_status": p.npi_status,
        "created_at": p.created_at.isoformat() if p.created_at else None
    } for p in providers]

@app.get("/providers/{provider_id}")
async def get_provider(provider_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Provider).filter(Provider.provider_id == provider_id))
    provider = result.scalars().first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider

@app.post("/providers/seed-mock-data")
async def seed_mock_data(db: AsyncSession = Depends(get_db)):
    """
    Seed database with mock provider data from CSV rows 1-20.
    """
    try:
        mock_providers = [
            {"npi": "1891106191", "first_name": "SATYASREE", "last_name": "UPADHYAYULA", "display_name": "SATYASREE UPADHYAYULA", "address_line1": "1402 S GRAND BLVD, FDT 14TH FLOOR", "city": "SAINT LOUIS", "state": "MO", "postal_code": "63104", "country": "US", "specialties": ["Internal Medicine"], "overall_confidence": 85.0, "status": "verified", "npi_status": "VALID", "email": "satyasree.upadhyayula@example.com"},
            {"npi": "1346202256", "first_name": "WENDY", "last_name": "JONES", "display_name": "WENDY P JONES", "address_line1": "2950 VILLAGE DR", "city": "FAYETTEVILLE", "state": "NC", "postal_code": "28304", "country": "US", "specialties": ["Obstetrics & Gynecology"], "overall_confidence": 88.0, "status": "verified", "npi_status": "VALID", "email": "wendy.jones@example.com"},
            {"npi": "1306820956", "first_name": "RICHARD", "last_name": "DUROCHER", "display_name": "RICHARD W DUROCHER", "address_line1": "20 WASHINGTON AVE, STE 212", "city": "NORTH HAVEN", "state": "CT", "postal_code": "06473", "country": "US", "specialties": ["Podiatry"], "overall_confidence": 82.0, "status": "verified", "npi_status": "VALID", "email": "richard.durocher@example.com"},
            {"npi": "1770523540", "first_name": "JASPER", "last_name": "FULLARD", "display_name": "JASPER FULLARD", "address_line1": "5746 N BROADWAY ST", "city": "KANSAS CITY", "state": "MO", "postal_code": "64118", "country": "US", "specialties": ["Internal Medicine"], "overall_confidence": 87.0, "status": "verified", "npi_status": "VALID", "email": "jasper.fullard@example.com"},
            {"npi": "1073627758", "first_name": "ANTHONY", "last_name": "PERROTTI", "display_name": "ANTHONY E PERROTTI", "address_line1": "875 MILITARY TRL, SUITE 200", "city": "JUPITER", "state": "FL", "postal_code": "33458", "country": "US", "specialties": ["Internal Medicine"], "overall_confidence": 90.0, "status": "verified", "npi_status": "VALID", "email": "anthony.perrotti@example.com"},
            {"npi": "1346571551", "first_name": "JOHN", "last_name": "PUGH", "display_name": "JOHN R PUGH", "address_line1": "504 ALBEMARLE SQ", "city": "CHARLOTTESVILLE", "state": "VA", "postal_code": "22901", "country": "US", "specialties": ["Physical Therapist in Private Practice"], "overall_confidence": 83.0, "status": "verified", "npi_status": "VALID", "email": "john.pugh@example.com"},
            {"npi": "1215943535", "first_name": "TOM", "last_name": "BRUMITT", "display_name": "TOM B BRUMITT", "address_line1": "70 DOCTORS PARK", "city": "CAPE GIRARDEAU", "state": "MO", "postal_code": "63703", "country": "US", "specialties": ["Diagnostic Radiology"], "overall_confidence": 86.0, "status": "verified", "npi_status": "VALID", "email": "tom.brumitt@example.com"},
            {"npi": "1629160551", "first_name": "RONALD", "last_name": "GALBREATH", "display_name": "RONALD G GALBREATH", "address_line1": "12522 E. LAMBERT ROAD, SUITE D", "city": "WHITTIER", "state": "CA", "postal_code": "90606", "country": "US", "specialties": ["Family Practice"], "overall_confidence": 89.0, "status": "verified", "npi_status": "VALID", "email": "ronald.galbreath@example.com"},
            {"npi": "1518929124", "first_name": "RALPH", "last_name": "BOONE", "display_name": "RALPH M BOONE", "address_line1": "1215 DUNN AVE", "city": "JACKSONVILLE", "state": "FL", "postal_code": "32218", "country": "US", "specialties": ["Family Practice"], "overall_confidence": 84.0, "status": "verified", "npi_status": "VALID", "email": "ralph.boone@example.com"},
            {"npi": "1396781134", "practice_name": "METWEST INC", "display_name": "METWEST INC", "address_line1": "695 S BROADWAY", "city": "DENVER", "state": "CO", "postal_code": "80209", "country": "US", "specialties": ["Clinical Laboratory"], "overall_confidence": 75.0, "status": "needs_review", "npi_status": "VALID", "email": "contact@metwestinc.com"},
            {"npi": "1205869104", "first_name": "LAUREN", "last_name": "ROSEN", "display_name": "LAUREN S ROSEN", "address_line1": "306 E LANCASTER AVE STE 300", "city": "WYNNEWOOD", "state": "PA", "postal_code": "19096", "country": "US", "specialties": ["Internal Medicine"], "overall_confidence": 88.0, "status": "verified", "npi_status": "VALID", "email": "lauren.rosen@example.com"},
            {"npi": "1720086507", "first_name": "ERIC", "last_name": "RODRIGUEZ", "display_name": "ERIC J RODRIGUEZ", "address_line1": "2323 W ROSE GARDEN LN", "city": "PHOENIX", "state": "AZ", "postal_code": "85027", "country": "US", "specialties": ["Diagnostic Radiology"], "overall_confidence": 87.0, "status": "verified", "npi_status": "VALID", "email": "eric.rodriguez@example.com"},
            {"npi": "1871511741", "first_name": "MUKESH", "last_name": "MADUPUR", "display_name": "MUKESH K MADUPUR", "address_line1": "2201 LEXINGTON AVE", "city": "ASHLAND", "state": "KY", "postal_code": "41101", "country": "US", "specialties": ["Diagnostic Radiology"], "overall_confidence": 85.0, "status": "verified", "npi_status": "VALID", "email": "mukesh.madupur@example.com"},
            {"npi": "1942246814", "first_name": "BABAK", "last_name": "SARANI", "display_name": "BABAK SARANI", "address_line1": "2150 PENNSYLVANIA AVE NW, STE 6B", "city": "WASHINGTON", "state": "DC", "postal_code": "20037", "country": "US", "specialties": ["General Surgery"], "overall_confidence": 91.0, "status": "verified", "npi_status": "VALID", "email": "babak.sarani@example.com"},
            {"npi": "1184886806", "first_name": "GAURAV", "last_name": "BHATIA", "display_name": "GAURAV BHATIA", "address_line1": "1860 TOWN CENTER DR, SUITE 300", "city": "RESTON", "state": "VA", "postal_code": "20190", "country": "US", "specialties": ["Pain Management"], "overall_confidence": 86.0, "status": "verified", "npi_status": "VALID", "email": "gaurav.bhatia@example.com"},
            {"npi": "1679737241", "first_name": "AMY", "last_name": "HENKEL", "display_name": "AMY E HENKEL", "address_line1": "801 S STEVENS ST", "city": "SPOKANE", "state": "WA", "postal_code": "99204", "country": "US", "specialties": ["Diagnostic Radiology"], "overall_confidence": 88.0, "status": "verified", "npi_status": "VALID", "email": "amy.henkel@example.com"},
            {"npi": "1366846719", "first_name": "MARIA", "last_name": "ORREGO", "display_name": "MARIA X ORREGO", "address_line1": "1801 INWOOD RD FL 7, SUITE 120", "city": "DALLAS", "state": "TX", "postal_code": "75390", "country": "US", "specialties": ["Physician Assistant"], "overall_confidence": 82.0, "status": "verified", "npi_status": "VALID", "email": "maria.orrego@example.com"},
            {"npi": "1710088190", "first_name": "AARON", "last_name": "CAMPBELL", "display_name": "AARON W CAMPBELL", "address_line1": "605 MEDICAL COURTS, SUITE 203", "city": "BRENHAM", "state": "TX", "postal_code": "77833", "country": "US", "specialties": ["Obstetrics & Gynecology"], "overall_confidence": 87.0, "status": "verified", "npi_status": "VALID", "email": "aaron.campbell@example.com"},
            {"npi": "1801136759", "first_name": "GREGORY", "last_name": "BERNARDO", "display_name": "GREGORY BERNARDO", "address_line1": "1925 PACIFIC AVE", "city": "ATLANTIC CITY", "state": "NJ", "postal_code": "08401", "country": "US", "specialties": ["Internal Medicine"], "overall_confidence": 85.0, "status": "verified", "npi_status": "VALID", "email": "gregory.bernardo@example.com"},
        ]
        
        created_count = 0
        for provider_data in mock_providers:
            # Check if provider already exists
            existing = await db.execute(select(Provider).filter(Provider.npi == provider_data["npi"]))
            if existing.scalars().first():
                continue
            
            provider = Provider(**provider_data)
            db.add(provider)
            created_count += 1
        
        await db.commit()
        
        return {
            "message": f"Successfully seeded {created_count} mock providers",
            "count": created_count
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Error seeding mock data: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Seeding failed: {str(e)}")

@app.post("/providers/{provider_id}/verify-email")
async def verify_provider_email(provider_id: int, db: AsyncSession = Depends(get_db)):
    """
    Trigger email verification for a provider.
    """
    try:
        result = await db.execute(select(Provider).filter(Provider.provider_id == provider_id))
        provider = result.scalars().first()
        
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        # Simulate email verification process
        # In production, this would send an actual verification email
        logger.info(f"📧 Email verification triggered for Provider #{provider_id} | NPI: {provider.npi}")
        
        # Update provider status (simulated)
        # In production, you'd send email and wait for verification
        
        return {
            "success": True,
            "message": f"Verification email sent to provider {provider.display_name}",
            "provider_id": provider_id,
            "email": provider.email or "No email on file"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering email verification: {e}")
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

@app.post("/analyze/map-data")
async def analyze_map_data(data: dict = Body(...)):
    """
    Analyze geographic distribution data using Gemini AI.
    """
    try:
        import json
        import os
        from google import genai
        
        # Initialize Gemini client
        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        # Prepare prompt for analysis
        prompt = f"""
You are a healthcare data analyst. Analyze the following geographic distribution data of healthcare provider submissions across US states.

DATA SUMMARY:
- Total States: {data.get('summary', {}).get('totalStates', 0)}
- Total Submissions: {data.get('summary', {}).get('totalSubmissions', 0):,}
- Total Providers: {data.get('summary', {}).get('totalProviders', 0):,}

TOP 5 STATES BY SUBMISSIONS:
{json.dumps(data.get('summary', {}).get('topStates', []), indent=2)}

FULL STATE DATA:
{json.dumps(data.get('states', []), indent=2)}

Please provide a comprehensive analysis that includes:
1. Key insights about the geographic distribution
2. Notable patterns or trends
3. States with high vs low submission rates
4. Potential implications for healthcare provider network coverage
5. Recommendations for improving distribution if needed

Format your response in clear, readable paragraphs suitable for display in a UI.
"""
        
        # Call Gemini API
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "temperature": 0.7,
            }
        )
        
        # Extract text from response - handle different response formats
        try:
            # Try direct text access
            analysis_text = response.text
        except AttributeError:
            try:
                # Try parsed response
                if hasattr(response, 'parsed'):
                    analysis_text = str(response.parsed)
                # Try candidates structure
                elif hasattr(response, 'candidates') and response.candidates:
                    analysis_text = response.candidates[0].content.parts[0].text
                else:
                    analysis_text = str(response)
            except Exception as e:
                logger.error(f"Error extracting text from Gemini response: {e}")
                analysis_text = "Analysis completed, but response format was unexpected."
        
        return {
            "success": True,
            "analysis": analysis_text
        }
        
    except Exception as e:
        logger.error(f"Gemini analysis error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

