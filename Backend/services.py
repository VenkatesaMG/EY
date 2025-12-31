from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Provider, RawProviderSubmission
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
        3. Upsert to Golden Record if confidence is sufficient.
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
            
            # Logic: If confidence > 80, we consider it GOLDEN (or provisionally golden).
            # If less, we might still save it but mark as 'needs_review' or triggers enrichment.
            
            status = "verified" if (overall_match and overall_confidence >= 80) else "needs_review"
            
            # 3. Upsert to Golden Record Provider Table
            # STRATEGY: Update Master Table with NPI Registry Data (The Source of Truth)
            
            existing_q = await db.execute(select(Provider).filter(Provider.npi == npi_val))
            provider = existing_q.scalars().first()
            
            if not provider:
                provider = Provider(npi=npi_val)
                db.add(provider)
            
            # Map NPI Registry Data (Golden Source)
            provider.first_name = npi_info.get("first_name")
            provider.last_name = npi_info.get("last_name")
            
            # Org Name if applicable logic (NPI basic has organization_name sometimes)
            if npi_info.get("enumeration_type") == "NPI-2": # Organization
                provider.practice_name = npi_info.get("raw", {}).get("basic", {}).get("organization_name")
                provider.display_name = provider.practice_name
            else:
                provider.display_name = f"{provider.first_name} {provider.last_name}".strip()

            # Taxonomy
            if npi_info.get("primary_taxonomy"):
                provider.taxonomy_code = npi_info.get("primary_taxonomy", {}).get("code")
                # provider.specialties = [npi_info.get("primary_taxonomy", {}).get("desc")] # If we had desc
            
            # Address from NPI
            npi_addr = npi_info.get("primary_practice_address", {})
            provider.address_line1 = npi_addr.get("address_1")
            provider.city = npi_addr.get("city")
            provider.state = npi_addr.get("state")
            provider.postal_code = npi_addr.get("postal_code")
            
            # Phone from NPI (Fallback to user input if missing)
            provider.phone = npi_addr.get("telephone_number") or data.get("phone")
            
            # Metadata from User Input (things NPI doesn't have)
            provider.email = data.get("primary_email")
            provider.website = data.get("website")
            
            # Save Raw Input for reference
            provider.raw_data_json = data 
            
            provider.status = status
            provider.overall_confidence = overall_confidence
            provider.npi_status = "VALID"
            provider.npi_confidence = 100.0
            
            # Map detailed validation
            fields = comparison.get("fields", {})
            
            name_res = fields.get("name", {})
            provider.name_status = "VERIFIED" if name_res.get("match") else "MISMATCH"
            provider.name_confidence = name_res.get("confidence", 0.0)

            addr_res = fields.get("address", {})
            provider.address_status = "VERIFIED" if addr_res.get("match") else "MISMATCH"
            provider.address_confidence = addr_res.get("confidence", 0.0)
            
            spec_res = fields.get("specialty", {})
            provider.taxonomy_status = "VERIFIED" if spec_res.get("match") else "MISMATCH"
            provider.taxonomy_confidence = spec_res.get("confidence", 0.0)
            
            provider.last_verified = datetime.utcnow()
            
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
    async def enrich_provider(provider: Provider, submission: RawProviderSubmission, db: AsyncSession):
        """
        Scrapes web to find missing fields for the provider.
        Uses enrichment_agent_v0 which uses Selenium + Ollama.
        """
        logger.info(f"🔍 Enriching Provider: {provider.display_name} (NPI: {provider.npi})")
        
        # Identify missing critical fields
        missing_keys = []
        if not provider.phone: missing_keys.append("phone")
        if not provider.address_line1: missing_keys.append("practice_address")
        if not provider.website: missing_keys.append("website")
        
        if not missing_keys:
            logger.info("✅ No missing fields. Skipping enrichment.")
            submission.processing_status = "processed"
            await db.commit()
            return

        # Prepare partial profile for the agent
        partial_profile = {
            "first_name": provider.first_name,
            "last_name": provider.last_name,
            "credential": provider.taxonomy_code, # approx
            "city": provider.city,
            "state": provider.state,
            "npi": provider.npi
        }

        try:
            manager = EnrichmentManager()
            # enrichment_agent_v0 only takes partial_profile
            result = manager.enrich_profile(partial_profile)
            
            # Parse result if string
            if isinstance(result, str):
                try: 
                    # Attempt to extract JSON from markdown block if present
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
                if result.get("phone") and not provider.phone:
                    provider.phone = result.get("phone")
                
                if result.get("website") and not provider.website:
                    provider.website = result.get("website")
                
                if result.get("practice_address") and not provider.address_line1:
                    provider.address_line1 = result.get("practice_address")
                
                # Also check for address fields in the v0 format
                if result.get("address_line1") and not provider.address_line1:
                    provider.address_line1 = result.get("address_line1")
                
                provider.status = "enriched"
                submission.processing_status = "enriched"
                logger.info("✅ Enrichment Complete")
                await db.commit()

        except Exception as e:
            logger.error(f"❌ Enrichment Error: {e}")
            submission.processing_status = "processed"  # Still mark as processed even if enrichment fails
            await db.commit()

