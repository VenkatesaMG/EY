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
from sqlalchemy import func, desc, delete

from database import get_db, init_db
from models import ProviderPersonal, ProviderProfessional, ProviderMeta, RawProviderSubmission, MarketExpansionOpportunity, ProviderAuditLog
from services import ValidationService, SubmissionPipeline, EnrichmentService, log_field_change, is_significant_change
from Agents.extractor_agent import HealthcareExtractionModel

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
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    await init_db()
    
    # Start the scheduler loop
    global _scheduler_task
    import sys
    if "pytest" not in sys.modules:
        _scheduler_task = asyncio.create_task(bg_scheduler_loop())

# --- Scheduler Setup ---
import asyncio
from datetime import datetime, timedelta
from pydantic import BaseModel
from database import AsyncSessionLocal

SCHEDULER_INTERVAL_MINUTES = 0  # 0 means disabled
_scheduler_task = None
_last_run = None

async def bg_scheduler_loop():
    global _last_run, SCHEDULER_INTERVAL_MINUTES
    
    while True:
        if SCHEDULER_INTERVAL_MINUTES > 0:
            now = datetime.utcnow()
            # If never run, or interval has passed
            if _last_run is None or (now - _last_run).total_seconds() >= (SCHEDULER_INTERVAL_MINUTES * 60):
                logger.info("⏰ Running scheduled batch enrichment...")
                try:
                    async with AsyncSessionLocal() as db:
                        stmt = select(ProviderMeta).filter(ProviderMeta.status == 'needs_review')
                        res = await db.execute(stmt)
                        metas = res.scalars().all()
                        npi_list = [m.npi for m in metas]
                    
                    if npi_list:
                        logger.info(f"Scheduled enrichment: Found {len(npi_list)} providers needing review.")
                        from services import EnrichmentService
                        for npi in npi_list:
                            try:
                                logger.info(f"Scheduled Enrichment for {npi}")
                                await EnrichmentService.enrich_provider(npi=npi)
                            except Exception as inner_e:
                                logger.error(f"Error scheduled enriching {npi}: {inner_e}")
                                
                except Exception as e:
                    logger.error(f"Scheduled task error: {e}")
                finally:
                    _last_run = datetime.utcnow() # Update last run time regardless of success
        
        await asyncio.sleep(30) # check every 30 seconds

class ScheduleConfig(BaseModel):
    interval_minutes: float

@app.get("/scheduler/config")
async def get_scheduler_config():
    global SCHEDULER_INTERVAL_MINUTES, _last_run
    return {
        "interval_minutes": SCHEDULER_INTERVAL_MINUTES,
        "last_run": _last_run.isoformat() if _last_run else None,
        "next_run": (_last_run + timedelta(minutes=SCHEDULER_INTERVAL_MINUTES)).isoformat() if _last_run and SCHEDULER_INTERVAL_MINUTES > 0 else None
    }

@app.post("/scheduler/config")
async def update_scheduler_config(config: ScheduleConfig):
    global SCHEDULER_INTERVAL_MINUTES
    SCHEDULER_INTERVAL_MINUTES = config.interval_minutes
    return {"message": f"Interval updated to {SCHEDULER_INTERVAL_MINUTES} minutes", "interval_minutes": SCHEDULER_INTERVAL_MINUTES}

# --- Endpoints ---

class StatusUpdate(BaseModel):
    submission_id: int
    detail: str

@app.post("/internal/update_status")
async def update_status_detail(update: StatusUpdate, db: AsyncSession = Depends(get_db)):
    sub = await db.get(RawProviderSubmission, update.submission_id)
    if sub:
        sub.error_message = update.detail
        await db.commit()
    return {"status": "ok"}

@app.delete("/admin/reset")
async def reset_database(db: AsyncSession = Depends(get_db)):
    """
    DANGER: Deletes all data from the database.
    """
    try:
        # Delete audit logs first
        await db.execute(delete(ProviderAuditLog))
        
        # Delete submissions
        await db.execute(delete(RawProviderSubmission))
        
        # Explicitly delete children first
        await db.execute(delete(ProviderMeta))
        await db.execute(delete(ProviderProfessional))
        
        # Then delete parent
        await db.execute(delete(ProviderPersonal))
        
        # Delete market opportunities
        await db.execute(delete(MarketExpansionOpportunity))
        
        await db.commit()
        
        return {"message": "Database reset successful. All tables cleared."}
    except Exception as e:
        await db.rollback()
        logger.error(f"Database reset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        
        print("Starting Background Task...")
        # Trigger validation in BACKGROUND
        # This allows immediate response to UI so it can start polling/visualizing
        background_tasks.add_task(SubmissionPipeline.run, submission.submission_id)
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
                return "failed"
            else:
                return "completed"
        

        elif step_name == "enrichment":
            if status in ["queued", "npi_lookup"]:
                return "pending"
            elif status in ["validation_complete", "enriching", "validating"]:
                return "in_progress"
            elif status in ["enriched", "processed", "email_verifying", "call_verifying", "pipeline_complete"]:
                return "completed"
            else:
                return "pending"
                
        elif step_name == "email":
            if status in ["queued", "npi_lookup", "validation_complete", "validating", "processed", "enriching", "enriched"]:
                return "pending"
            elif status == "email_verifying":
                return "in_progress"
            elif status in ["call_verifying", "pipeline_complete"]:
                return "completed"
            else:
                return "pending"
                
        elif step_name == "call":
            if status in ["queued", "npi_lookup", "validation_complete", "validating", "processed", "enriching", "enriched", "email_verifying"]:
                return "pending"
            elif status == "call_verifying":
                return "in_progress"
            elif status in ["pipeline_complete"]:
                return "completed"
            else:
                return "pending"
                
        elif step_name == "final_review":
            if status == "pipeline_complete":
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
            "enrichment": get_step_status("enrichment"),
            "email": get_step_status("email"),
            "call": get_step_status("call"),
            "final_review": get_step_status("final_review")
        }
    }

@app.post("/onboard/csv")
async def onboard_csv_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db)
):
    """
    Batch processing for CSV.
    """
    import codecs
    try:
        # robust encoding handling
        # standard utf-8-sig handles BOM if present (common in Excel CSVs)
        # fallback to latin-1 if utf-8 fails
        content = await file.read()
        
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
            
        csv_file = io.StringIO(text)
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
        
        processed_count = len(submissions_created)
        for sub in submissions_created:
            await db.refresh(sub)
            # Process in background so UI gets control back immediately
            background_tasks.add_task(ValidationService.process_submission, sub.submission_id)
            
        return {
            "message": f"Queued {processed_count} submissions for processing."
        }
        
    except Exception as e:
        logger.error(f"CSV Upload Failed: {e}")
        import traceback
        traceback.print_exc()
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
        "field_metadata": {**(p.field_metadata or {}), **(prof.field_metadata or {})},
        "raw_json": meta.raw_data_json
    }

@app.post("/providers/seed-mock-data")
async def seed_mock_data(db: AsyncSession = Depends(get_db)):
    """
    Seed database with mock provider data from CSV rows 1-20.
    """
    try:
        mock_providers = [
            # Custom record for testing Twilio
            {"npi": "9999999999", "first_name": "DHILEEPAN", "last_name": "S B", "display_name": "Dr. DHILEEPAN", "address_line1": "123 Tech Avenue", "city": "CHENNAI", "state": "TN", "postal_code": "600001", "country": "IN", "specialties": ["Software Engineering"], "overall_confidence": 99.0, "status": "needs_review", "npi_status": "VALID", "email": "dhileepan@example.com", "phone": "6369764886"},
            
        #     {"npi": "1891106191", "first_name": "SATYASREE", "last_name": "UPADHYAYULA", "display_name": "SATYASREE UPADHYAYULA", "address_line1": "1402 S GRAND BLVD, FDT 14TH FLOOR", "city": "SAINT LOUIS", "state": "MO", "postal_code": "63104", "country": "US", "specialties": ["Internal Medicine"], "overall_confidence": 85.0, "status": "verified", "npi_status": "VALID", "email": "satyasree.upadhyayula@example.com", "phone": "6369764886"},
        #     {"npi": "1346202256", "first_name": "WENDY", "last_name": "JONES", "display_name": "WENDY P JONES", "address_line1": "2950 VILLAGE DR", "city": "FAYETTEVILLE", "state": "NC", "postal_code": "28304", "country": "US", "specialties": ["Obstetrics & Gynecology"], "overall_confidence": 88.0, "status": "verified", "npi_status": "VALID", "email": "wendy.jones@example.com", "phone": "6369764886"},
        #     {"npi": "1306820956", "first_name": "RICHARD", "last_name": "DUROCHER", "display_name": "RICHARD W DUROCHER", "address_line1": "20 WASHINGTON AVE, STE 212", "city": "NORTH HAVEN", "state": "CT", "postal_code": "06473", "country": "US", "specialties": ["Podiatry"], "overall_confidence": 82.0, "status": "verified", "npi_status": "VALID", "email": "richard.durocher@example.com", "phone": "6369764886"},
        #     {"npi": "1770523540", "first_name": "JASPER", "last_name": "FULLARD", "display_name": "JASPER FULLARD", "address_line1": "5746 N BROADWAY ST", "city": "KANSAS CITY", "state": "MO", "postal_code": "64118", "country": "US", "specialties": ["Internal Medicine"], "overall_confidence": 87.0, "status": "verified", "npi_status": "VALID", "email": "jasper.fullard@example.com", "phone": "6369764886"},
        #     {"npi": "1073627758", "first_name": "ANTHONY", "last_name": "PERROTTI", "display_name": "ANTHONY E PERROTTI", "address_line1": "875 MILITARY TRL, SUITE 200", "city": "JUPITER", "state": "FL", "postal_code": "33458", "country": "US", "specialties": ["Internal Medicine"], "overall_confidence": 90.0, "status": "verified", "npi_status": "VALID", "email": "anthony.perrotti@example.com", "phone": "6369764886"},
        #     {"npi": "1346571551", "first_name": "JOHN", "last_name": "PUGH", "display_name": "JOHN R PUGH", "address_line1": "504 ALBEMARLE SQ", "city": "CHARLOTTESVILLE", "state": "VA", "postal_code": "22901", "country": "US", "specialties": ["Physical Therapist in Private Practice"], "overall_confidence": 83.0, "status": "verified", "npi_status": "VALID", "email": "john.pugh@example.com", "phone": "6369764886"},
        #     {"npi": "1215943535", "first_name": "TOM", "last_name": "BRUMITT", "display_name": "TOM B BRUMITT", "address_line1": "70 DOCTORS PARK", "city": "CAPE GIRARDEAU", "state": "MO", "postal_code": "63703", "country": "US", "specialties": ["Diagnostic Radiology"], "overall_confidence": 86.0, "status": "verified", "npi_status": "VALID", "email": "tom.brumitt@example.com", "phone": "6369764886"},
        #     {"npi": "1629160551", "first_name": "RONALD", "last_name": "GALBREATH", "display_name": "RONALD G GALBREATH", "address_line1": "12522 E. LAMBERT ROAD, SUITE D", "city": "WHITTIER", "state": "CA", "postal_code": "90606", "country": "US", "specialties": ["Family Practice"], "overall_confidence": 89.0, "status": "verified", "npi_status": "VALID", "email": "ronald.galbreath@example.com", "phone": "6369764886"},
        #     {"npi": "1518929124", "first_name": "RALPH", "last_name": "BOONE", "display_name": "RALPH M BOONE", "address_line1": "1215 DUNN AVE", "city": "JACKSONVILLE", "state": "FL", "postal_code": "32218", "country": "US", "specialties": ["Family Practice"], "overall_confidence": 84.0, "status": "verified", "npi_status": "VALID", "email": "ralph.boone@example.com", "phone": "6369764886"},
        #     {"npi": "1396781134", "practice_name": "METWEST INC", "display_name": "METWEST INC", "address_line1": "695 S BROADWAY", "city": "DENVER", "state": "CO", "postal_code": "80209", "country": "US", "specialties": ["Clinical Laboratory"], "overall_confidence": 75.0, "status": "needs_review", "npi_status": "VALID", "email": "contact@metwestinc.com", "phone": "6369764886"},
        #     {"npi": "1205869104", "first_name": "LAUREN", "last_name": "ROSEN", "display_name": "LAUREN S ROSEN", "address_line1": "306 E LANCASTER AVE STE 300", "city": "WYNNEWOOD", "state": "PA", "postal_code": "19096", "country": "US", "specialties": ["Internal Medicine"], "overall_confidence": 88.0, "status": "verified", "npi_status": "VALID", "email": "lauren.rosen@example.com"},
        #     {"npi": "1720086507", "first_name": "ERIC", "last_name": "RODRIGUEZ", "display_name": "ERIC J RODRIGUEZ", "address_line1": "2323 W ROSE GARDEN LN", "city": "PHOENIX", "state": "AZ", "postal_code": "85027", "country": "US", "specialties": ["Diagnostic Radiology"], "overall_confidence": 87.0, "status": "verified", "npi_status": "VALID", "email": "eric.rodriguez@example.com"},
        #     {"npi": "1871511741", "first_name": "MUKESH", "last_name": "MADUPUR", "display_name": "MUKESH K MADUPUR", "address_line1": "2201 LEXINGTON AVE", "city": "ASHLAND", "state": "KY", "postal_code": "41101", "country": "US", "specialties": ["Diagnostic Radiology"], "overall_confidence": 85.0, "status": "verified", "npi_status": "VALID", "email": "mukesh.madupur@example.com"},
        #     {"npi": "1942246814", "first_name": "BABAK", "last_name": "SARANI", "display_name": "BABAK SARANI", "address_line1": "2150 PENNSYLVANIA AVE NW, STE 6B", "city": "WASHINGTON", "state": "DC", "postal_code": "20037", "country": "US", "specialties": ["General Surgery"], "overall_confidence": 91.0, "status": "verified", "npi_status": "VALID", "email": "babak.sarani@example.com"},
        #     {"npi": "1184886806", "first_name": "GAURAV", "last_name": "BHATIA", "display_name": "GAURAV BHATIA", "address_line1": "1860 TOWN CENTER DR, SUITE 300", "city": "RESTON", "state": "VA", "postal_code": "20190", "country": "US", "specialties": ["Pain Management"], "overall_confidence": 86.0, "status": "verified", "npi_status": "VALID", "email": "gaurav.bhatia@example.com"},
        #     {"npi": "1679737241", "first_name": "AMY", "last_name": "HENKEL", "display_name": "AMY E HENKEL", "address_line1": "801 S STEVENS ST", "city": "SPOKANE", "state": "WA", "postal_code": "99204", "country": "US", "specialties": ["Diagnostic Radiology"], "overall_confidence": 88.0, "status": "verified", "npi_status": "VALID", "email": "amy.henkel@example.com"},
        #     {"npi": "1366846719", "first_name": "MARIA", "last_name": "ORREGO", "display_name": "MARIA X ORREGO", "address_line1": "1801 INWOOD RD FL 7, SUITE 120", "city": "DALLAS", "state": "TX", "postal_code": "75390", "country": "US", "specialties": ["Physician Assistant"], "overall_confidence": 82.0, "status": "verified", "npi_status": "VALID", "email": "maria.orrego@example.com"},
        #     {"npi": "1710088190", "first_name": "AARON", "last_name": "CAMPBELL", "display_name": "AARON W CAMPBELL", "address_line1": "605 MEDICAL COURTS, SUITE 203", "city": "BRENHAM", "state": "TX", "postal_code": "77833", "country": "US", "specialties": ["Obstetrics & Gynecology"], "overall_confidence": 87.0, "status": "verified", "npi_status": "VALID", "email": "aaron.campbell@example.com"},
        #     {"npi": "1801136759", "first_name": "GREGORY", "last_name": "BERNARDO", "display_name": "GREGORY BERNARDO", "address_line1": "1925 PACIFIC AVE", "city": "ATLANTIC CITY", "state": "NJ", "postal_code": "08401", "country": "US", "specialties": ["Internal Medicine"], "overall_confidence": 85.0, "status": "verified", "npi_status": "VALID", "email": "gregory.bernardo@example.com"},
        # 
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
from Agents.call_agent import CallVerificationAgent

# Import Response & Form for Twilio
from fastapi import Request, Form
from fastapi.responses import Response

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
        
        # Update fields if provided — with audit trail
        # We explicitly trust the provider input here
        verification_fields_personal = {
            'first_name': 'first_name', 'last_name': 'last_name',
            'display_name': 'display_name', 'email': 'email', 'phone': 'phone'
        }
        for field_key, attr_name in verification_fields_personal.items():
            if field_key in data:
                old_val = getattr(p, attr_name, None)
                new_val = data[field_key]
                if is_significant_change(attr_name, old_val, new_val):
                    log_field_change(db, p.npi, attr_name, old_val, new_val, 'verification', 'personal', 'provider')
                    setattr(p, attr_name, new_val)
        
        # Professional fields
        verification_fields_prof = {
            'practice_name': 'practice_name', 'website': 'website',
            'accepting_new_patients': 'accepting_new_patients', 'telehealth': 'telehealth'
        }
        for field_key, attr_name in verification_fields_prof.items():
            if field_key in data:
                old_val = getattr(prof, attr_name, None)
                new_val = data[field_key]
                if is_significant_change(attr_name, old_val, new_val):
                    log_field_change(db, p.npi, attr_name, old_val, new_val, 'verification', 'professional', 'provider')
                    setattr(prof, attr_name, new_val)
        
        # Address (Sync both for simplicity in this flow)
        for addr_field in ['address_line1', 'city', 'state', 'postal_code']:
            if addr_field in data:
                old_val = getattr(p, addr_field, None)
                new_val = data[addr_field]
                if is_significant_change(addr_field, old_val, new_val):
                    log_field_change(db, p.npi, addr_field, old_val, new_val, 'verification', 'personal', 'provider')
                    setattr(p, addr_field, new_val)
                    setattr(prof, addr_field, new_val)
            
        # Update Meta Status
        log_field_change(db, p.npi, 'status', meta.status, 'verified_by_provider', 'verification', 'meta', 'provider')
        meta.status = "verified_by_provider"
        log_field_change(db, p.npi, 'overall_confidence', meta.overall_confidence, 100.0, 'verification', 'meta', 'provider')
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

@app.post("/providers/{provider_id}/call")
async def initiate_provider_call(provider_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Initiates a verification phone call for a provider using Twilio.
    """
    try:
        result = await db.execute(select(ProviderPersonal).options(selectinload(ProviderPersonal.meta)).filter(ProviderPersonal.npi == provider_id))
        provider = result.scalars().first()
        
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        if not provider.phone:
            raise HTTPException(status_code=400, detail="Provider has no phone number on record")
            
            
        # Prioritize WEBHOOK_BASE_URL from env
        import os
        webhook_base = os.getenv("WEBHOOK_BASE_URL")
        
        if not webhook_base:
            host = request.headers.get("host", "localhost:8000")
            scheme = request.headers.get("x-forwarded-proto", "http")
            webhook_base = f"{scheme}://{host}"
            
        call_agent = CallVerificationAgent(webhook_base_url=webhook_base)
        
        success = call_agent.initiate_verification_call(
            provider_id=provider.npi,
            to_number=provider.phone,
            provider_name=provider.display_name or provider.last_name or "Doctor"
        )
        
        if success:
            return {"success": True, "message": f"Calling {provider.phone} now..."}
        else:
            raise HTTPException(status_code=500, detail="Failed to initiate call")

    except Exception as e:
        logger.error(f"Error starting call: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Call failed: {str(e)}")

from fastapi.responses import StreamingResponse
import asyncio

# Global dictionary to hold SSE queues for real-time call updates
provider_call_events = {}

@app.get("/providers/{provider_id}/call-stream")
async def call_stream(provider_id: str):
    async def event_generator():
        if provider_id not in provider_call_events:
            provider_call_events[provider_id] = asyncio.Queue()
        queue = provider_call_events[provider_id]
        
        try:
            while True:
                message = await queue.get()
                yield f"data: {json.dumps(message)}\n\n"
        except asyncio.CancelledError:
            pass
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/twilio/call/{provider_id}/step/{step}")
async def twilio_call_webhook(
    provider_id: str, 
    step: str,
    request: Request,
    SpeechResult: Optional[str] = Form(None),
    Digits: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook for Twilio TwiML responses during the call.
    Each step returns XML (TwiML) text that Twilio parses out.
    """
    logger.info(f"Twilio Webhook: Provider {provider_id} | Step {step} | SpeechResult: {SpeechResult} | Digits: {Digits}")
    
    # Broadcast to SSE
    if provider_id in provider_call_events:
        await provider_call_events[provider_id].put({
            "step": step,
            "speech": SpeechResult,
            "digits": Digits,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    # Needs to return valid application/xml response
    result = await db.execute(select(ProviderPersonal).options(
        selectinload(ProviderPersonal.professional),
        selectinload(ProviderPersonal.meta)
    ).filter(ProviderPersonal.npi == provider_id))
    provider = result.scalars().first()
    
    if not provider:
         return Response(content="<Response><Say>Invalid Provider ID. Goodbye.</Say><Hangup/></Response>", media_type="application/xml")
         
    # Generate provider data dict to pass
    provider_data = {
        "last_name": provider.last_name,
        "practice_name": provider.professional.practice_name if provider.professional else None,
        "address_line1": provider.address_line1,
        "city": provider.city,
    }
    
    call_agent = CallVerificationAgent()
    xml_response, extracted_updates = call_agent.generate_twiml_for_step(provider_id, step, provider_data, SpeechResult, Digits)
    
    # If final step, we update status to verified_by_provider
    if step == "process_update" and extracted_updates:
        try:
            if not provider.meta:
                provider.meta = ProviderMeta(npi=provider.npi)
             
            for field, val in extracted_updates.items():
                if not val: continue
                # simple mapping (in a real scenario, use more robust mapping/validation)
                if field in ["address_line1", "city", "state", "postal_code", "phone", "email"]:
                    old_val = getattr(provider, field, None)
                    if is_significant_change(field, old_val, val):
                        setattr(provider, field, val)
                        log_field_change(db, provider.npi, field, old_val, val, 'phone_verification', 'personal', 'provider')
                        if provider.professional and field in ["address_line1", "city", "state", "postal_code"]:
                            setattr(provider.professional, field, val)
                        
                elif field in ["practice_name", "website", "accepting_new_patients", "telehealth"]:
                     if provider.professional:
                         old_val = getattr(provider.professional, field, None)
                         if is_significant_change(field, old_val, val):
                             setattr(provider.professional, field, val)
                             log_field_change(db, provider.npi, field, old_val, val, 'phone_verification', 'professional', 'provider')
             
            old_status = provider.meta.status
            provider.meta.status = "verified_by_provider"
            provider.meta.overall_confidence = 100.0
             
            log_field_change(db, provider.npi, 'status', old_status, 'verified_by_provider', 'phone_verification', 'meta', 'provider')
            await db.commit()
            
            # Broadcast update success
            if provider_id in provider_call_events:
                await provider_call_events[provider_id].put({
                    "step": "completed",
                    "updates": extracted_updates,
                    "timestamp": datetime.utcnow().isoformat()
                })
             
            logger.info(f"Verified & updated {provider.npi} purely via phone interaction! Updates: {extracted_updates}")
        except Exception as e:
            await db.rollback()
            logger.error(f"Error verifying provider via phone call: {e}")

    return Response(content=xml_response, media_type="application/xml")



@app.post("/providers/{provider_id}/enrich")
async def enrich_provider_manual(provider_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Manually trigger enrichment for a provider.
    """
    # Verify provider exists
    result = await db.execute(select(ProviderPersonal).filter(ProviderPersonal.npi == provider_id))
    provider = result.scalars().first()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
        
    # Trigger background task
    background_tasks.add_task(EnrichmentService.enrich_provider, npi=provider_id)
    return {"message": "Enrichment started in background"}


@app.post("/providers/batch-enrich")
async def batch_enrich_providers(
    background_tasks: BackgroundTasks,
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger enrichment for a batch of providers.
    Payload: {"npi_list": ["123", "456"]}
    """
    npi_list = data.get("npi_list", [])
    if not npi_list:
        raise HTTPException(status_code=400, detail="No NPI list provided")
    
    count = 0
    for npi in npi_list:
         background_tasks.add_task(EnrichmentService.enrich_provider, npi=npi)
         count += 1
         
    return {"message": f"Started enrichment for {count} providers"}


@app.post("/providers/batch-call")
async def batch_call_providers(
    request: Request,
    background_tasks: BackgroundTasks,
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger phone calls for a batch of providers.
    """
    npi_list = data.get("npi_list", [])
    if not npi_list:
        raise HTTPException(status_code=400, detail="No NPI list provided")
    
    # helper for call
    async def run_call(npi_id: str):
        # We need a new session per task usually, or carefully use the one we have
        # But BackgroundTasks in FastAPI doesn't easily share the request session if it's already closed
        # EnrichmentService.enrich_provider handles its own session, let's do similar for call
        async with AsyncSessionLocal() as dbs:
            res = await dbs.execute(select(ProviderPersonal).filter(ProviderPersonal.npi == npi_id))
            p = res.scalars().first()
            if p and p.phone:
                import os
                webhook_base = os.getenv("WEBHOOK_BASE_URL")
                if not webhook_base:
                    # Fallback — though in prod this MUST be set
                    webhook_base = "http://localhost:8000"
                
                from Agents.call_agent import CallVerificationAgent
                agent = CallVerificationAgent(webhook_base_url=webhook_base)
                agent.initiate_verification_call(
                    provider_id=p.npi,
                    to_number=p.phone,
                    provider_name=p.display_name or p.last_name or "Doctor"
                )

    count = 0
    for npi in npi_list:
         background_tasks.add_task(run_call, npi)
         count += 1
         
    return {"message": f"Initiated calls for {count} providers"}


@app.get("/providers/{provider_id}/audit-log")
async def get_provider_audit_log(provider_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get the full audit trail / change history for a provider.
    Returns all field-level changes ordered by most recent first.
    """
    try:
        stmt = select(ProviderAuditLog).filter(
            ProviderAuditLog.npi == provider_id
        ).order_by(desc(ProviderAuditLog.changed_at))

        result = await db.execute(stmt)
        entries = result.scalars().all()

        return [
            {
                "id": entry.id,
                "field_name": entry.field_name,
                "table_name": entry.table_name,
                "old_value": entry.old_value,
                "new_value": entry.new_value,
                "change_source": entry.change_source,
                "actor": entry.actor,
                "changed_at": entry.changed_at.isoformat() if entry.changed_at else None
            }
            for entry in entries
        ]

    except Exception as e:
        logger.error(f"Error fetching audit log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/geo-distribution")
async def get_geo_distribution(specialty: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """
    Get provider counts by state, optionally filtered by specialty.
    """
    try:
        # Group by state from ProviderProfessional (which has practice address)
        stmt = select(
            ProviderProfessional.state, 
            func.count(ProviderProfessional.id)
        )

        if specialty:
            # Filter where the specialty is in the array
            # SQLAlchemy's contains operator for PG arrays: array_column.contains([val])
            stmt = stmt.filter(ProviderProfessional.specialties.contains([specialty]))

        stmt = stmt.group_by(ProviderProfessional.state)
        
        result = await db.execute(stmt)
        rows = result.all()
        
        # Convert to dictionary { "CA": 120, "TX": 50, ... }
        state_counts = {
            row[0]: row[1] 
            for row in rows 
            if row[0]
        }
        
        return state_counts
    except Exception as e:
        logger.error(f"Error fetching geo analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/specialties")
async def get_specialties(db: AsyncSession = Depends(get_db)):
    """
    Get list of unique specialties for filtering.
    """
    try:
        # Unnest the array and get distinct values
        stmt = select(func.unnest(ProviderProfessional.specialties)).distinct()
        result = await db.execute(stmt)
        specialties = result.scalars().all()
        
        # Filter out None and sort
        return sorted([s for s in specialties if s])
    except Exception as e:
        logger.error(f"Error fetching specialties: {e}")
        # Fallback if unnest isn't supported (e.g. SQLite) - though we expect PG
        # Logic: Fetch all arrays and flat map in python
        try:
             stmt = select(ProviderProfessional.specialties).filter(ProviderProfessional.specialties != None)
             result = await db.execute(stmt)
             all_lists = result.scalars().all()
             unique_set = set()
             for lst in all_lists:
                 if lst:
                     unique_set.update(lst)
             return sorted(list(unique_set))
        except Exception as inner_e:
             raise HTTPException(status_code=500, detail=str(inner_e))
        


@app.post("/analyze/map-data")
async def analyze_map_data(data: dict = Body(...)):

    """
    Analyze geographic distribution data using Groq AI (Llama 3).
    """
    try:
        import json
        from Validation.groq_client import generate_text
        
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
        
        # Use Groq instead of Gemini
        analysis_text = generate_text(
            prompt=prompt,
            model="llama-3.3-70b-versatile",
            json_mode=False
        )
        
        return {
            "success": True,
            "analysis": analysis_text
        }
        
    except Exception as e:
        logger.error(f"Groq analysis error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/analyze/context-data")
async def get_analysis_context(specialty: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """
    Fetch rich contextual data for the analysis chat, filtered by taxonomy/specialty.
    Returns provider counts, confidence stats, status distribution, and sample provider details.
    """
    try:
        # Base query for providers with their professional and meta data
        base_stmt = select(ProviderPersonal).options(
            selectinload(ProviderPersonal.meta),
            selectinload(ProviderPersonal.professional)
        )

        # If specialty filter, join on professional and filter
        if specialty:
            base_stmt = base_stmt.join(ProviderProfessional).filter(
                ProviderProfessional.specialties.contains([specialty])
            )

        result = await db.execute(base_stmt)
        providers = result.scalars().all()

        # --- Aggregate stats ---
        total_count = len(providers)
        states_map = {}
        confidence_scores = []
        status_counts = {"verified": 0, "needs_review": 0, "verified_by_provider": 0, "other": 0}
        specialties_set = set()
        provider_details = []

        for p in providers:
            prof = p.professional
            meta = p.meta

            # State distribution
            st = (prof.state if prof else None) or p.state
            if st:
                states_map[st] = states_map.get(st, 0) + 1

            # Confidence
            if meta and meta.overall_confidence is not None:
                confidence_scores.append(meta.overall_confidence)

            # Status
            if meta:
                status_val = meta.status or "other"
                if status_val in status_counts:
                    status_counts[status_val] += 1
                else:
                    status_counts["other"] += 1

            # Specialties
            if prof and prof.specialties:
                for s in prof.specialties:
                    specialties_set.add(s)

            # Collect provider detail (limit to 50 for context window)
            if len(provider_details) < 50:
                provider_details.append({
                    "npi": p.npi,
                    "name": p.display_name,
                    "state": st,
                    "specialties": prof.specialties if prof else [],
                    "confidence": round(meta.overall_confidence, 1) if meta and meta.overall_confidence else None,
                    "status": meta.status if meta else "unknown",
                    "practice_name": prof.practice_name if prof else None,
                    "city": (prof.city if prof else None) or p.city,
                    "email": p.email,
                    "telehealth": prof.telehealth if prof else None,
                    "accepting_new_patients": prof.accepting_new_patients if prof else None
                })

        avg_confidence = round(sum(confidence_scores) / len(confidence_scores), 1) if confidence_scores else 0
        top_states = sorted(states_map.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "filter": specialty or "All Specialties",
            "total_providers": total_count,
            "avg_confidence": avg_confidence,
            "min_confidence": round(min(confidence_scores), 1) if confidence_scores else 0,
            "max_confidence": round(max(confidence_scores), 1) if confidence_scores else 0,
            "status_distribution": status_counts,
            "states_with_providers": len(states_map),
            "top_states": [{"state": s, "count": c} for s, c in top_states],
            "all_state_counts": states_map,
            "unique_specialties": sorted(list(specialties_set)),
            "providers": provider_details
        }

    except Exception as e:
        logger.error(f"Error fetching analysis context: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/chat")
async def analyze_chat(data: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """
    Multi-turn conversational analysis endpoint.
    Accepts conversation history and injects relevant context data based on the selected taxonomy.
    """
    try:
        from Validation.groq_client import generate_text
        from groq import Groq

        messages = data.get("messages", [])  # [{role, content}, ...]
        specialty = data.get("specialty", None)
        context_data = data.get("context_data", {})  # Pre-fetched context

        if not messages:
            raise HTTPException(status_code=400, detail="No messages provided")

        # Build system prompt with injected context
        system_prompt = f"""You are an expert healthcare data analyst assistant for HealthValidator.ai — a platform that validates, enriches, and manages healthcare provider data.

You have access to the following LIVE DATA from the platform's database. Use this data to answer questions accurately and provide actionable insights.

=== CURRENT DATA CONTEXT ===
Filter: {context_data.get('filter', 'All Specialties')}
Total Providers: {context_data.get('total_providers', 0)}
Average Confidence Score: {context_data.get('avg_confidence', 0)}%
Min Confidence: {context_data.get('min_confidence', 0)}% | Max Confidence: {context_data.get('max_confidence', 0)}%
States with Providers: {context_data.get('states_with_providers', 0)}

Status Distribution:
{json.dumps(context_data.get('status_distribution', {}), indent=2)}

Top States by Provider Count:
{json.dumps(context_data.get('top_states', []), indent=2)}

All State Counts:
{json.dumps(context_data.get('all_state_counts', {}), indent=2)}

Unique Specialties in Dataset:
{json.dumps(context_data.get('unique_specialties', []), indent=2)}

Provider Details (sample up to 50):
{json.dumps(context_data.get('providers', []), indent=2)}
=== END DATA CONTEXT ===

IMPORTANT GUIDELINES:
- Ground your analysis in the actual data provided above.
- When the user asks about specific states, providers, or specialties, reference the real data.
- Provide specific numbers, percentages, and comparisons when possible.
- If the user asks about data you don't have, clearly state that.
- Keep responses concise but insightful. Use bullet points and bold text for readability.
- You can suggest follow-up questions the user might want to ask.
- Format your response with markdown for readability (bold, bullets, headers).
"""

        # Build Groq message array
        groq_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            groq_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        # Call Groq with the full conversation
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=groq_messages,
            temperature=0.7,
            max_tokens=4096,
            top_p=1,
            stream=False
        )

        response_text = completion.choices[0].message.content

        return {
            "success": True,
            "response": response_text
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat analysis error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.get("/providers/{provider_id}/manual-review")
async def get_manual_review_data(provider_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get all candidate values for each attribute grouped by source,
    pulled from the audit log exactly to help manual review.
    """
    try:
        stmt = select(ProviderAuditLog).filter(ProviderAuditLog.npi == provider_id).order_by(ProviderAuditLog.changed_at)
        res = await db.execute(stmt)
        entries = res.scalars().all()
        
        fields_data = {}
        for entry in entries:
            fname = entry.field_name
            if fname not in fields_data:
                fields_data[fname] = {}
            if entry.new_value is not None:
                # Store the latest non-null value from this source
                fields_data[fname][entry.change_source] = entry.new_value
        
        return fields_data
    except Exception as e:
        logger.error(f"Error fetching manual review data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/providers/{provider_id}/manual-review")
async def submit_manual_review(provider_id: str, payload: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """
    Submit manual review updates. Will convert provider to a golden record.
    payload: {"updates": {"first_name": "John", "last_name": "Doe", ...}}
    """
    try:
        updates = payload.get("updates", {})
        if not updates:
            return {"success": True, "message": "No updates provided"}
            
        result = await db.execute(select(ProviderPersonal).options(
            selectinload(ProviderPersonal.professional),
            selectinload(ProviderPersonal.meta)
        ).filter(ProviderPersonal.npi == provider_id))
        provider = result.scalars().first()
        
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
            
        for field, val in updates.items():
            # If val is string 'None' or empty, maybe None, but let's just keep as is
            # Update Personal
            if hasattr(provider, field) and field not in ['npi', 'id', 'field_metadata']:
                old_val = getattr(provider, field, None)
                if is_significant_change(field, old_val, val):
                    setattr(provider, field, val)
                    log_field_change(db, provider.npi, field, old_val, val, 'manual_admin', 'personal', 'admin')
            
            # Update Professional
            if provider.professional and hasattr(provider.professional, field) and field not in ['npi', 'id', 'field_metadata']:
                old_val = getattr(provider.professional, field, None)
                # Parse specialties list string if it is a string
                if field == "specialties" and isinstance(val, str):
                    if val.startswith("[") and val.endswith("]"):
                        import ast
                        try:
                            val = ast.literal_eval(val)
                        except:
                            val = [s.strip() for s in val.replace("[","").replace("]","").split(",") if s.strip()]
                    else:
                        val = [s.strip() for s in val.split(",") if s.strip()]
                        
                if is_significant_change(field, old_val, val):
                    setattr(provider.professional, field, val)
                    log_field_change(db, provider.npi, field, old_val, val, 'manual_admin', 'professional', 'admin')
                    
        # Mark as golden record / verified
        if provider.meta:
            old_status = provider.meta.status
            provider.meta.status = "verified_manual"
            provider.meta.overall_confidence = 100.0
            log_field_change(db, provider.npi, 'status', old_status, 'verified_manual', 'manual_admin', 'meta', 'admin')
            
            flags = provider.meta.data_quality_flags or []
            flags = [f for f in flags if "mismatch" not in f]
            if "manual_golden_record" not in flags:
                flags.append("manual_golden_record")
            provider.meta.data_quality_flags = flags
            provider.meta.manual_review_required = False
            
        await db.commit()
        return {"success": True, "message": "Provider successfully updated as Golden Record."}
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error submitting manual review: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/providers/{provider_id}/manual-review")
async def get_manual_review_data(provider_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get all candidate values for each attribute grouped by source,
    pulled from the audit log exactly to help manual review.
    """
    try:
        stmt = select(ProviderAuditLog).filter(ProviderAuditLog.npi == provider_id).order_by(ProviderAuditLog.changed_at)
        res = await db.execute(stmt)
        entries = res.scalars().all()
        
        fields_data = {}
        for entry in entries:
            fname = entry.field_name
            if fname not in fields_data:
                fields_data[fname] = {}
            if entry.new_value is not None:
                # Store the latest non-null value from this source
                fields_data[fname][entry.change_source] = entry.new_value
        
        return fields_data
    except Exception as e:
        logger.error(f"Error fetching manual review data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/providers/{provider_id}/manual-review")
async def submit_manual_review(provider_id: str, payload: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """
    Submit manual review updates. Will convert provider to a golden record.
    payload: {"updates": {"first_name": "John", "last_name": "Doe", ...}}
    """
    try:
        updates = payload.get("updates", {})
        if not updates:
            return {"success": True, "message": "No updates provided"}
            
        result = await db.execute(select(ProviderPersonal).options(
            selectinload(ProviderPersonal.professional),
            selectinload(ProviderPersonal.meta)
        ).filter(ProviderPersonal.npi == provider_id))
        provider = result.scalars().first()
        
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
            
        for field, val in updates.items():
            # If val is string 'None' or empty, maybe None, but let's just keep as is
            # Update Personal
            if hasattr(provider, field) and field not in ['npi', 'id', 'field_metadata']:
                old_val = getattr(provider, field, None)
                if is_significant_change(field, old_val, val):
                    setattr(provider, field, val)
                    log_field_change(db, provider.npi, field, old_val, val, 'manual_admin', 'personal', 'admin')
            
            # Update Professional
            if provider.professional and hasattr(provider.professional, field) and field not in ['npi', 'id', 'field_metadata']:
                old_val = getattr(provider.professional, field, None)
                # Parse specialties list string if it is a string
                if field == "specialties" and isinstance(val, str):
                    if val.startswith("[") and val.endswith("]"):
                        import ast
                        try:
                            val = ast.literal_eval(val)
                        except:
                            val = [s.strip() for s in val.replace("[","").replace("]","").split(",") if s.strip()]
                    else:
                        val = [s.strip() for s in val.split(",") if s.strip()]
                        
                if is_significant_change(field, old_val, val):
                    setattr(provider.professional, field, val)
                    log_field_change(db, provider.npi, field, old_val, val, 'manual_admin', 'professional', 'admin')
                    
        # Mark as golden record / verified
        if provider.meta:
            old_status = provider.meta.status
            provider.meta.status = "verified_manual"
            provider.meta.overall_confidence = 100.0
            log_field_change(db, provider.npi, 'status', old_status, 'verified_manual', 'manual_admin', 'meta', 'admin')
            
            flags = provider.meta.data_quality_flags or []
            flags = [f for f in flags if "mismatch" not in f]
            if "manual_golden_record" not in flags:
                flags.append("manual_golden_record")
            provider.meta.data_quality_flags = flags
            provider.meta.manual_review_required = False
            
        await db.commit()
        return {"success": True, "message": "Provider successfully updated as Golden Record."}
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error submitting manual review: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

