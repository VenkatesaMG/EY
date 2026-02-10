import sys
import os
import shutil
from typing import List, Optional
from uuid import uuid4
import csv
import io
import codecs
import logging
import json

# Add parent directory to path to allow importing from Agents
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, desc

from database import get_db, init_db
from models import ProviderPersonal, ProviderProfessional, ProviderMeta, RawProviderSubmission, MarketExpansionOpportunity
from Agents.extractor_agent import HealthcareExtractionModel
from services import ValidationService

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
    provider_data = None
    if submission.npi:
        # Load provider with meta and professional relation
        stmt = select(ProviderPersonal).options(
            selectinload(ProviderPersonal.meta),
            selectinload(ProviderPersonal.professional)
        ).filter(ProviderPersonal.npi == submission.npi)
        
        p_res = await db.execute(stmt)
        provider = p_res.scalars().first()
        
        if provider:
            # Flatten for UI consumption
            provider_data = {
                "id": provider.npi, # Use NPI as ID
                "status": provider.meta.status if provider.meta else "needs_review",
                "overall_confidence": provider.meta.overall_confidence if provider.meta else 0,
                "npi_status": provider.meta.npi_status if provider.meta else "PENDING",
                "name_status": provider.meta.name_status if provider.meta else "PENDING",
                "address_status": provider.meta.address_status if provider.meta else "PENDING"
            }

    # Compute step statuses based on processing_status
    status = submission.processing_status
    
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
    """
    try:
        csv_file = io.TextIOWrapper(file.file, encoding="utf-8")
        reader = csv.DictReader(csv_file)
        
        submissions_created = []
        
        for row in reader:
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
    stmt = select(ProviderPersonal).join(ProviderMeta).options(
        selectinload(ProviderPersonal.meta),
        selectinload(ProviderPersonal.professional)
    ).order_by(desc(ProviderMeta.created_at)).limit(limit).offset(skip)
    
    result = await db.execute(stmt)
    providers = result.scalars().all()
    
    output = []
    for p in providers:
        # Join data safely
        prof = p.professional or ProviderProfessional()
        meta = p.meta or ProviderMeta()
        
        output.append({
            "provider_id": p.npi, # Using NPI as primary ID
            "npi": p.npi,
            "display_name": p.display_name,
            "first_name": p.first_name,
            "last_name": p.last_name,
            "practice_name": prof.practice_name,
            "email": p.email,
            "phone": p.phone,
            "address_line1": p.address_line1 or prof.address_line1,
            "city": p.city or prof.city,
            "state": p.state or prof.state,
            "postal_code": p.postal_code or prof.postal_code,
            "specialties": prof.specialties or ([prof.taxonomy_code] if prof.taxonomy_code else []),
            "overall_confidence": meta.overall_confidence,
            "status": meta.status,
            "npi_status": meta.npi_status,
            "created_at": meta.created_at.isoformat() if meta.created_at else None
        })
    return output

@app.get("/providers/{provider_id}")
async def get_provider(provider_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get provider by NPI (or ID).
    """
    stmt = select(ProviderPersonal).options(
        selectinload(ProviderPersonal.meta),
        selectinload(ProviderPersonal.professional)
    ).filter(ProviderPersonal.npi == provider_id)
    
    result = await db.execute(stmt)
    p = result.scalars().first()
    
    if not p:
        raise HTTPException(status_code=404, detail="Provider not found")
        
    prof = p.professional or ProviderProfessional()
    meta = p.meta or ProviderMeta()
    
    # Return flattened
    return {
        "provider_id": p.npi,
        "npi": p.npi,
        "display_name": p.display_name,
        "first_name": p.first_name,
        "last_name": p.last_name,
        "practice_name": prof.practice_name,
        "email": p.email,
        "phone": p.phone,
        "website": prof.website,
        "address_line1": p.address_line1 or prof.address_line1,
        "city": p.city or prof.city,
        "state": p.state or prof.state,
        "postal_code": p.postal_code or prof.postal_code,
        "country": p.country,
        "taxonomies": prof.taxonomies,
        "taxonomy_code": prof.taxonomy_code,
        "specialties": prof.specialties,
        "accepting_new_patients": prof.accepting_new_patients,
        "telehealth": prof.telehealth,
        # Meta
        "status": meta.status,
        "overall_confidence": meta.overall_confidence,
        "npi_status": meta.npi_status,
        "npi_confidence": meta.npi_confidence,
        "name_status": meta.name_status,
        "name_confidence": meta.name_confidence,
        "practice_status": meta.practice_status,
        "practice_confidence": meta.practice_confidence,
        "address_status": meta.address_status,
        "address_confidence": meta.address_confidence,
        "taxonomy_status": meta.taxonomy_status,
        "taxonomy_confidence": meta.taxonomy_confidence,
        "last_verified": meta.last_verified,
        "raw_json": meta.raw_data_json
    }

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
        for p_data in mock_providers:
            npi = p_data.get("npi")
            existing = await db.execute(select(ProviderPersonal).filter(ProviderPersonal.npi == npi))
            if existing.scalars().first():
                continue
            
            # Create Personal
            personal = ProviderPersonal(
                npi=npi,
                first_name=p_data.get("first_name"),
                last_name=p_data.get("last_name"),
                display_name=p_data.get("display_name"),
                phone=None, # Mock data didn't have phone
                email=p_data.get("email"),
                address_line1=p_data.get("address_line1"),
                city=p_data.get("city"),
                state=p_data.get("state"),
                postal_code=p_data.get("postal_code"),
                country=p_data.get("country")
            )
            
            # Create Professional
            prof = ProviderProfessional(
                npi=npi,
                practice_name=p_data.get("practice_name"),
                address_line1=p_data.get("address_line1"), # Duplicate for integrity
                city=p_data.get("city"),
                specialties=p_data.get("specialties")
            )
            
            # Create Meta
            meta = ProviderMeta(
                npi=npi,
                status=p_data.get("status"),
                overall_confidence=p_data.get("overall_confidence"),
                npi_status=p_data.get("npi_status")
            )
            
            db.add(personal)
            db.add(prof)
            db.add(meta)
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

from datetime import datetime, timedelta
from Agents.email_agent import EmailVerificationAgent

@app.post("/providers/{provider_id}/verify-email")
async def verify_provider_email(provider_id: str, db: AsyncSession = Depends(get_db)):
    """
    Trigger email verification for a provider.
    Generates a token, saves it, and sends a link.
    """
    try:
        # Assuming provider_id is NPI for consistency
        result = await db.execute(select(ProviderPersonal).options(selectinload(ProviderPersonal.meta)).filter(ProviderPersonal.npi == provider_id))
        provider = result.scalars().first()
        
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        # Initialize Agent
        # In prod, base_url would come from env (e.g. frontend URL)
        email_agent = EmailVerificationAgent(base_url="http://localhost:3000") 
        
        # Generate Token
        token = email_agent.generate_verification_token()
        
        # Update DB
        if not provider.meta:
            provider.meta = ProviderMeta(npi=provider.npi)
            
        provider.meta.verification_token = token
        provider.meta.token_expires_at = datetime.utcnow() + timedelta(hours=48)
        
        await db.commit()
        
        # Send Email
        link = email_agent.create_verification_link(token)
        sent = email_agent.send_verification_email(
            recipient_email=provider.email or "test@example.com",
            recipient_name=provider.display_name or "Doctor",
            verification_link=link
        )
        
        if sent:
            logger.info(f"📧 Email request sent for {provider.npi}. Token: {token}")
            return {
                "success": True,
                "message": f"Verification email sent to {provider.email}",
                "debug_link": link # Returning link for demo purposes since we can't check email
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send email")

    except Exception as e:
        logger.error(f"Error triggering email verification: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

@app.get("/verification/{token}")
async def get_verification_data(token: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve provider data based on verification token.
    Used by the external verification page.
    """
    try:
        # Find connection by token
        stmt = select(ProviderMeta).options(
            selectinload(ProviderMeta.personal).selectinload(ProviderPersonal.professional)
        ).filter(ProviderMeta.verification_token == token)
        
        result = await db.execute(stmt)
        meta = result.scalars().first()
        
        if not meta:
            raise HTTPException(status_code=404, detail="Invalid verification token")
            
        if meta.token_expires_at and meta.token_expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Verification link has expired")
            
        p = meta.personal
        prof = p.professional
        
        # Return editable fields
        return {
            "npi": p.npi,
            "display_name": p.display_name,
            "first_name": p.first_name,
            "last_name": p.last_name,
            "email": p.email,
            "phone": p.phone,
            "practice_name": prof.practice_name,
            "specialties": prof.specialties,
            "address_line1": p.address_line1 or prof.address_line1,
            "city": p.city or prof.city,
            "state": p.state or prof.state,
            "postal_code": p.postal_code or prof.postal_code,
            "website": prof.website,
            "accepting_new_patients": prof.accepting_new_patients,
            "telehealth": prof.telehealth,
            "token_valid": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving verification data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/verification/{token}/submit")
async def submit_verification_data(token: str, data: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """
    Provider submits verified/corrected data.
    Overrides existing data and marks as Verified.
    """
    try:
        logger.info(f"📝 Processing verification submission for token: {token}")
        logger.info(f"📦 Received Payload: {data}")

        stmt = select(ProviderMeta).options(
            selectinload(ProviderMeta.personal).selectinload(ProviderPersonal.professional)
        ).filter(ProviderMeta.verification_token == token)
        
        result = await db.execute(stmt)
        meta = result.scalars().first()
        
        if not meta:
            logger.warning(f"❌ Invalid token: {token}")
            raise HTTPException(status_code=404, detail="Invalid token")
            
        if meta.token_expires_at and meta.token_expires_at < datetime.utcnow():
            logger.warning(f"⏰ Token expired: {token}")
            raise HTTPException(status_code=400, detail="Token expired")
            
        p = meta.personal
        prof = p.professional
        
        if not prof:
            logger.info(f"⚠️ ProviderProfessional missing for NPI {p.npi}. Creating new record.")
            prof = ProviderProfessional(npi=p.npi)
            db.add(prof)
            # Ensure relationship is established
            p.professional = prof
        
        # Update fields if provided
        # We explicitly trust the provider input here
        
        if "first_name" in data: p.first_name = data["first_name"]
        if "last_name" in data: p.last_name = data["last_name"]
        if "display_name" in data: p.display_name = data["display_name"]
        if "email" in data: p.email = data["email"]
        if "phone" in data: p.phone = data["phone"]
        
        # Professional
        if "practice_name" in data: prof.practice_name = data["practice_name"]
        if "website" in data: prof.website = data["website"]
        if "accepting_new_patients" in data: prof.accepting_new_patients = data["accepting_new_patients"]
        if "telehealth" in data: prof.telehealth = data["telehealth"]
        
        # Address (Sync both for simplicity in this flow)
        if "address_line1" in data: 
            p.address_line1 = data["address_line1"]
            prof.address_line1 = data["address_line1"]
        if "city" in data:
            p.city = data["city"]
            prof.city = data["city"]
        if "state" in data:
            p.state = data["state"]
            prof.state = data["state"]
        if "postal_code" in data:
            p.postal_code = data["postal_code"]
            prof.postal_code = data["postal_code"]
            
        # Update Meta Status
        meta.status = "verified_by_provider"
        meta.overall_confidence = 100.0
        meta.last_verified = datetime.utcnow()
        meta.verification_token = None # Consume token
        
        # Add a flag to indicate self-verification
        if meta.data_quality_flags:
            meta.data_quality_flags = [f for f in meta.data_quality_flags if "mismatch" not in f]
        meta.data_quality_flags = (meta.data_quality_flags or []) + ["self_verified"]

        logger.info(f"💾 Committing updates for NPI {p.npi}...")
        await db.commit()
        logger.info("✅ Verification data committed successfully.")
        
        return {"success": True, "message": "Information verified successfully"}

    except Exception as e:
        await db.rollback()
        logger.error(f"Error submitting verification: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/geo-distribution")
async def get_geo_distribution(db: AsyncSession = Depends(get_db)):
    """
    Get provider counts by state.
    """
    try:
        # Group by state from ProviderProfessional (which has practice address)
        # Use simple group by count
        stmt = select(
            ProviderProfessional.state, 
            func.count(ProviderProfessional.id)
        ).group_by(ProviderProfessional.state)
        
        result = await db.execute(stmt)
        rows = result.all()
        
        # Convert to dictionary { "CA": 120, "TX": 50, ... }
        # Filter out None states
        state_counts = {
            row[0]: row[1] 
            for row in rows 
            if row[0]
        }
        
        return state_counts
    except Exception as e:
        logger.error(f"Error fetching geo analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/map-data")
async def analyze_map_data(data: dict = Body(...)):

    """
    Analyze geographic distribution data using Gemini AI.
    """
    # ... existing implementation kept same ...
    try:
        import json
        import os
        from google import genai
        
        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
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
        
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={
                "temperature": 0.7,
            }
        )
        
        try:
            analysis_text = response.text
        except AttributeError:
            try:
                if hasattr(response, 'parsed'):
                    analysis_text = str(response.parsed)
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
