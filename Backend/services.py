from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from models import ProviderPersonal, ProviderProfessional, ProviderMeta, RawProviderSubmission
from Validation.NPI import lookup_npi
from Validation.gemini_compare import compare_row_with_npi_gemini
from Agents.enrichment_agent_v0 import EnrichmentManager
import json
import logging

# Setup logger
logger = logging.getLogger("HealthValidator")

class ValidationService:
    @staticmethod
    async def process_submission(submission: RawProviderSubmission, db: AsyncSession):
        """
        Process a raw submission:
        1. Access NPI API (if not already done).
        2. Validate/Compare using Gemini.
        3. Upsert to Golden Record tables if confidence is sufficient.
        """
        logger.info(f"📥 Processing Submission #{submission.submission_id} | NPI: {submission.npi}")
        
        data = submission.input_payload or {}
        npi_val = submission.npi
        
        # 1. NPI Lookup
        npi_info = None
        if not npi_val:
            submission.processing_status = "failed"
            submission.error_message = "Missing NPI"
            await db.commit()
            return
        
        # Update status to show NPI lookup in progress
        submission.processing_status = "npi_lookup"
        await db.commit()
        logger.info(f"🔍 Step 1: NPI Registry Lookup for {npi_val}")
            
        try:
            npi_info = lookup_npi(npi_val)
            submission.npi_api_response = npi_info
            await db.commit()  # Save NPI response immediately
            logger.info(f"✅ NPI Lookup Complete")
        except Exception as e:
            logger.error(f"❌ NPI Lookup Failed: {e}")
            submission.processing_status = "failed"
            submission.error_message = f"NPI API Error: {str(e)}"
            await db.commit()
            return # Retry later?

        if not npi_info:
            submission.processing_status = "rejected_invalid_npi"
            submission.error_message = "NPI not found in registry"
            await db.commit()
            return
        
        # Update status to show AI validation in progress
        submission.processing_status = "validating"
        await db.commit()
        logger.info(f"🤖 Step 2: AI Validation in progress...")

        # 2. Compare with Gemini
        row_data = {
            "name": f"{data.get('first_name', '')} {data.get('last_name', '')}".strip() or data.get("organization_name"),
            "address": f"{data.get('locations', [{}])[0].get('street_address_1')}, {data.get('locations', [{}])[0].get('city')}",
            "phone": data.get("phone"),
            "specialty": data.get("specialties", [""])[0] if data.get("specialties") else "",
        }

        try:
            comparison = compare_row_with_npi_gemini(row_data, npi_info)
            
            overall_confidence = comparison.get("confidence", 0.0)
            overall_match = comparison.get("overall_match", False)
            
            logger.info(f"🤖 AI Validation: Confidence={overall_confidence}% | Match={overall_match}")
            
            status = "verified" if (overall_match and overall_confidence >= 80) else "needs_review"
            
            # 3. Upsert to Golden Record Provider Tables
            
            # Fetch existing provider with all relations
            stmt = select(ProviderPersonal).options(
                selectinload(ProviderPersonal.professional),
                selectinload(ProviderPersonal.meta)
            ).filter(ProviderPersonal.npi == npi_val)
            
            result = await db.execute(stmt)
            provider = result.scalars().first()
            
            # Create if not exists
            if not provider:
                provider = ProviderPersonal(npi=npi_val)
                db.add(provider)
                
                # Must flush to ensure existence before creating related records if strictly enforced FKs in separate transactions (but here same transaction is fine)
                # We will create the children objects
                prof = ProviderProfessional(npi=npi_val)
                meta = ProviderMeta(npi=npi_val)
                
                # Link them (SQLAlchemy should handle FK assignment via relationship, but explicit is safer for insert)
                provider.professional = prof
                provider.meta = meta
                
                db.add(prof)
                db.add(meta)
            else:
                # Ensure relations exist (in case of partial data corruption)
                if not provider.professional:
                    provider.professional = ProviderProfessional(npi=npi_val)
                if not provider.meta:
                    provider.meta = ProviderMeta(npi=npi_val)
            
            # --- Map Data to Normalized Tables ---
            
            # 1. Personal Info
            provider.first_name = npi_info.get("first_name")
            provider.last_name = npi_info.get("last_name")
            
            if npi_info.get("enumeration_type") == "NPI-2": # Organization
                org_name = npi_info.get("raw", {}).get("basic", {}).get("organization_name")
                provider.display_name = org_name
                provider.professional.practice_name = org_name
            else:
                provider.display_name = f"{provider.first_name} {provider.last_name}".strip()

            # Contact & Address (Use NPI address as primary)
            npi_addr = npi_info.get("primary_practice_address", {})
            
            # Personal Contact Info (from NPI or User Input)
            provider.phone = npi_addr.get("telephone_number") or data.get("phone")
            provider.email = data.get("primary_email")
            
            # Personal Address
            provider.address_line1 = npi_addr.get("address_1")
            provider.city = npi_addr.get("city")
            provider.state = npi_addr.get("state")
            provider.postal_code = npi_addr.get("postal_code")
            provider.country = npi_addr.get("country_code", "US")

            # 2. Professional Info
            # Also map address to professional (practice address)
            provider.professional.address_line1 = npi_addr.get("address_1")
            provider.professional.city = npi_addr.get("city")
            provider.professional.state = npi_addr.get("state")
            provider.professional.postal_code = npi_addr.get("postal_code")
            provider.professional.country = npi_addr.get("country_code", "US")
            
            provider.professional.website = data.get("website")
            
            # Taxonomy
            if npi_info.get("primary_taxonomy"):
                provider.professional.taxonomy_code = npi_info.get("primary_taxonomy", {}).get("code")
                # Store full taxonomies list as JSON
                provider.professional.taxonomies = npi_info.get("taxonomies", [])

            # 3. Validation Meta
            provider.meta.raw_data_json = data 
            provider.meta.status = status
            provider.meta.overall_confidence = overall_confidence
            provider.meta.npi_status = "VALID"
            provider.meta.npi_confidence = 100.0
            
            # Map detailed validation
            fields = comparison.get("fields", {})
            
            name_res = fields.get("name", {})
            provider.meta.name_status = "VERIFIED" if name_res.get("match") else "MISMATCH"
            provider.meta.name_confidence = name_res.get("confidence", 0.0)

            addr_res = fields.get("address", {})
            provider.meta.address_status = "VERIFIED" if addr_res.get("match") else "MISMATCH"
            provider.meta.address_confidence = addr_res.get("confidence", 0.0)
            
            spec_res = fields.get("specialty", {})
            provider.meta.taxonomy_status = "VERIFIED" if spec_res.get("match") else "MISMATCH"
            provider.meta.taxonomy_confidence = spec_res.get("confidence", 0.0)
            
            provider.meta.last_verified = datetime.utcnow()
            
            submission.processing_status = "processed"
            
            await db.commit()
            
            # Trigger Enrichment if confidence is low
            if status == "needs_review":
                logger.warning(f"⚠️  Confidence {overall_confidence}% < 80% → Triggering Enrichment Agent")
                # Update status to enriching
                submission.processing_status = "enriching"
                await db.commit()
                logger.info(f"🌐 Step 3: Web Enrichment in progress...")
                await EnrichmentService.enrich_provider(provider, submission, db)
            
        except Exception as e:
            logger.error(f"❌ Validation Error: {e}")
            submission.processing_status = "failed_validation"
            submission.error_message = str(e)
            await db.commit()


class EnrichmentService:
    @staticmethod
    async def enrich_provider(provider: ProviderPersonal, submission: RawProviderSubmission, db: AsyncSession):
        """
        Scrapes web to find missing fields for the provider.
        """
        # Ensure relations are loaded if passed from elsewhere
        # (In process_submission they are loaded, but let's be safe if possible, though async attributes are tricky)
        # We assume they are loaded.
        
        logger.info(f"🔍 Enriching Provider: {provider.display_name} (NPI: {provider.npi})")
        
        # Identify missing critical fields
        missing_keys = []
        if not provider.phone: missing_keys.append("phone")
        
        # Check professional address
        if not provider.professional.address_line1: missing_keys.append("practice_address")
        if not provider.professional.website: missing_keys.append("website")
        
        if not missing_keys:
            logger.info("✅ No missing fields. Skipping enrichment.")
            submission.processing_status = "processed"
            await db.commit()
            return

        # Prepare partial profile for the agent
        partial_profile = {
            "first_name": provider.first_name,
            "last_name": provider.last_name,
            "credential": provider.professional.taxonomy_code, 
            "city": provider.city,
            "state": provider.state,
            "npi": provider.npi
        }

        try:
            manager = EnrichmentManager()
            result = manager.enrich_profile(partial_profile)
            
            # Parse result if string
            if isinstance(result, str):
                try: 
                    if "```json" in result:
                        import re
                        match = re.search(r"```json\s*(\{.*?\})\s*```", result, re.DOTALL)
                        if match:
                            result = json.loads(match.group(1))
                    else:
                        result = json.loads(result)
                except:
                    logger.warning("⚠️  Could not parse Agent output as JSON")
                    submission.processing_status = "processed"
                    await db.commit()
                    return

            # Update provider with found data
            if isinstance(result, dict):
                updated = False
                if result.get("phone") and not provider.phone:
                    provider.phone = result.get("phone")
                    updated = True
                
                if result.get("website") and not provider.professional.website:
                    provider.professional.website = result.get("website")
                    updated = True
                
                if result.get("practice_address") and not provider.professional.address_line1:
                    provider.professional.address_line1 = result.get("practice_address")
                    updated = True
                
                if result.get("address_line1") and not provider.professional.address_line1:
                     provider.professional.address_line1 = result.get("address_line1")
                     updated = True
                
                if updated:
                    provider.meta.status = "enriched"
                    submission.processing_status = "enriched"
                    logger.info("✅ Enrichment Complete")
                else:
                    submission.processing_status = "processed"
                    logger.info("✅ Enrichment Complete (No new data)")
                    
                await db.commit()

        except Exception as e:
            logger.error(f"❌ Enrichment Error: {e}")
            submission.processing_status = "processed"  
            await db.commit()
