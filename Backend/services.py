from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from models import ProviderPersonal, ProviderProfessional, ProviderMeta, RawProviderSubmission
from Validation.NPI import lookup_npi
# from Validation.gemini_compare import compare_row_with_npi_gemini
from Validation.groq_compare import compare_row_with_npi_groq
from Agents.enrichment_agent_v0 import EnrichmentManager
import json
import logging
from fastapi import Depends
from database import get_db, AsyncSessionLocal
import asyncio

# Setup logger
logger = logging.getLogger("HealthValidator")

class ValidationService:
    @staticmethod
    async def process_submission(submission_id: int):
        async with AsyncSessionLocal() as db:
            submission = await db.get(RawProviderSubmission, submission_id)

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

        # 2. Deterministic Verification & Conflict Resolution
        try:
            # We process verification LOCALLY instead of asking Gemini for basic matching
            
            from difflib import SequenceMatcher
            
            def calculate_similarity(a, b):
                if not a or not b: return 0.0
                return SequenceMatcher(None, str(a).lower().strip(), str(b).lower().strip()).ratio() * 100

            def calculate_jaccard(a, b):
                if not a or not b: return 0.0
                set_a = set(str(a).lower().split())
                set_b = set(str(b).lower().split())
                if not set_a or not set_b: return 0.0
                intersection = len(set_a.intersection(set_b))
                union = len(set_a.union(set_b))
                return (intersection / union) * 100

            # Prepare comparisons
            input_first = data.get('first_name') or data.get('fname') or ''
            input_last = data.get('last_name') or data.get('lname') or ''
            input_name = f"{input_first} {input_last}".strip() or data.get("organization_name", "")

            npi_name = f"{npi_info.get('first_name', '')} {npi_info.get('last_name', '')}".strip()
            if not npi_name.strip(): npi_name = npi_info.get("raw", {}).get("basic", {}).get("organization_name", "")

            name_score = calculate_similarity(input_name, npi_name)
            
            # Address construction
            # Address construction
            # Handle both nested 'locations' (JSON/API) and flat structure (CSV)
            locations_data = data.get('locations')
            if locations_data and isinstance(locations_data, list) and len(locations_data) > 0:
                input_addr_1 = locations_data[0].get('street_address_1', '')
                input_city = locations_data[0].get('city', '')
            else:
                # Fallback for CSV flat structure
                # Check multiple common keys
                input_addr_1 = data.get('addr1') or data.get('address_line1') or data.get('street_address_1') or ''
                input_city = data.get('city') or ''
            
            input_addr = f"{input_addr_1} {input_city}"
            
            npi_addr_dict = npi_info.get("primary_practice_address", {})
            npi_addr = f"{npi_addr_dict.get('address_1', '')} {npi_addr_dict.get('city', '')}"
            
            addr_score = calculate_jaccard(input_addr, npi_addr)
            
            # Phone verification (Exact match on last 10 digits)
            # Handle 'phone' or 'telephone_number' from CSV/API
            raw_phone = data.get("phone") or data.get("telephone_number") or ""
            input_phone = "".join(filter(str.isdigit, str(raw_phone)))
            npi_phone = "".join(filter(str.isdigit, str(npi_addr_dict.get("telephone_number") or "")))
            phone_match = (input_phone[-10:] == npi_phone[-10:]) and len(input_phone) >= 10
            
            # --- Weighted Confidence Calculation ---
            # Formula: (NPI_Exact * 40) + (Name_Sim * 0.2) + (Addr_Sim * 0.2) + (Phone * 10) ... roughly
            # Simplified based on user request:
            # Base 40 for NPI existing (which is true here)
            score = 40.0
            
            # Name Sim (Max 20 points)
            score += (name_score / 100.0) * 20.0
            
            # Address Sim (Max 20 points)
            score += (addr_score / 100.0) * 20.0
            
            # Phone Match (10 points)
            if phone_match: score += 10.0
            
            # Penalties based on critical mismatches
            manual_review = False
            flags = []
            
            if name_score < 70: 
                score -= 20
                flags.append("name_mismatch")
                manual_review = True
                
            if addr_score < 50:
                flags.append("address_mismatch")
                # We don't penalize score too heavily for address as providers move
                
            # Cap score
            final_confidence = max(0, min(100, score))
            if final_confidence < 60: manual_review = True

            logger.info(f"⚖️ Verifiction: Name={name_score:.1f}% | Addr={addr_score:.1f}% | Phone={phone_match}")
            logger.info(f"📊 Confidence Score: {final_confidence:.1f} | Manual Review: {manual_review}")

            # 3. Upsert to Golden Record Provider Tables
            
            stmt = select(ProviderPersonal).options(
                selectinload(ProviderPersonal.professional),
                selectinload(ProviderPersonal.meta)
            ).filter(ProviderPersonal.npi == npi_val)
            
            result = await db.execute(stmt)
            provider = result.scalars().first()
            
            if not provider:
                provider = ProviderPersonal(npi=npi_val)
                db.add(provider)
                prof = ProviderProfessional(npi=npi_val)
                meta = ProviderMeta(npi=npi_val)
                provider.professional = prof
                provider.meta = meta
                db.add(prof)
                db.add(meta)
            else:
                if not provider.professional: provider.professional = ProviderProfessional(npi=npi_val)
                if not provider.meta: provider.meta = ProviderMeta(npi=npi_val)
            
            # --- Apply Field-Level Locking (Source of Truth) ---
            now_str = datetime.utcnow().isoformat()
            
            # Helper to update metadata
            def update_meta(obj, field, source):
                current_meta = obj.field_metadata or {}
                current_meta[field] = {
                    "source": source,
                    "confidence": 100.0 if source == 'npi' else final_confidence,
                    "verified_at": now_str
                }
                # Re-assign to trigger SQLalchemy detection (for JSON mutation)
                obj.field_metadata = dict(current_meta)

            # 1. LOCKED FIELDS (NPI Source)
            # We always overwrite with NPI data if available, regardless of input
            provider.first_name = npi_info.get("first_name")
            update_meta(provider, 'first_name', 'npi')
            
            provider.last_name = npi_info.get("last_name")
            update_meta(provider, 'last_name', 'npi')
            
            if npi_info.get("enumeration_type") == "NPI-2":
                org_name = npi_info.get("raw", {}).get("basic", {}).get("organization_name")
                provider.display_name = org_name
            else:
                provider.display_name = f"{provider.first_name} {provider.last_name}".strip()
            update_meta(provider, 'display_name', 'npi')

            # Taxonomy Locked
            if npi_info.get("primary_taxonomy"):
                provider.professional.taxonomy_code = npi_info.get("primary_taxonomy", {}).get("code")
                provider.professional.taxonomies = npi_info.get("taxonomies", [])
                update_meta(provider.professional, 'taxonomy_code', 'npi')

            # 2. ENRICHABLE FIELDS (Scrape/Input Source)
            # Only update from input if NPI is empty OR if input is deemed high quality (e.g. website)
            
            # Phone: If NPI has it, use it. If not, use Input.
            if npi_addr_dict.get("telephone_number"):
                provider.phone = npi_addr_dict.get("telephone_number")
                update_meta(provider, 'phone', 'npi')
            elif data.get("phone"):
                provider.phone = data.get("phone")
                update_meta(provider, 'phone', 'submission')

            # Addresses: Keep NPI as primary for now (simplification), log mismatch
            # We store NPI address to ensure mailing works
            provider.address_line1 = npi_addr_dict.get("address_1")
            provider.city = npi_addr_dict.get("city")
            provider.state = npi_addr_dict.get("state")
            provider.postal_code = npi_addr_dict.get("postal_code")
            provider.country = npi_addr_dict.get("country_code", "US")
            update_meta(provider, 'address', 'npi')
            
            # Website: NPI usually doesn't have it, so Input wins
            if data.get("website"):
                provider.professional.website = data.get("website")
                update_meta(provider.professional, 'website', 'submission')
            
            # 3. Update Meta
            provider.meta.raw_data_json = data 
            provider.meta.status = "needs_review" if manual_review else "verified"
            provider.meta.manual_review_required = manual_review
            provider.meta.confidence_score = final_confidence
            provider.meta.data_quality_flags = flags
            
            # Deprecated fields (kept for compatibility)
            provider.meta.npi_status = "VALID"
            provider.meta.npi_confidence = 100.0
            provider.meta.name_status = "VERIFIED" if name_score > 80 else "MISMATCH"
            provider.meta.name_confidence = name_score
            provider.meta.address_status = "VERIFIED" if addr_score > 70 else "MISMATCH" 
            provider.meta.address_confidence = addr_score
            provider.meta.overall_confidence = final_confidence
            
            provider.meta.last_verified = datetime.utcnow()
            
            submission.processing_status = "processed"
            await db.commit()
            
            # Trigger Enrichment only if we strictly need it AND not purely for correction
            # If manual review is needed, enrichment might help clarify
            if manual_review and not flags: # If no specific flags but low score?
                pass
            elif manual_review and "name_mismatch" in flags:
                # Name mismatch shouldn't trigger auto-enrichment usually as it might be wrong person
                pass
            
        except Exception as e:
            logger.error(f"❌ Validation Error: {e}")
            submission.processing_status = "failed_validation"
            submission.error_message = str(e)
            await db.commit()

def extract_json_block(text: str):
    import re, json
    block = re.search(r"\{.*\}", text, re.DOTALL)
    if block:
        return json.loads(block.group(0))
    raise ValueError("No JSON found")

class EnrichmentService:

    @staticmethod
    async def enrich_provider(submission_id: int):

        print("Starting Enrichment...")

        async with AsyncSessionLocal() as db:

            submission = await db.get(RawProviderSubmission, submission_id)
            if not submission:
                logger.error("Submission not found")
                return

            provider = provider = await db.scalar(
    select(ProviderPersonal)
    .options(
        selectinload(ProviderPersonal.professional),
        selectinload(ProviderPersonal.meta),
    )
    .where(ProviderPersonal.npi == submission.npi)
)

            provider_prof = await db.scalar(
                select(ProviderProfessional)
                .where(ProviderProfessional.npi == submission.npi)
            )

            if not provider or not provider_prof:
                logger.warning("Provider records incomplete — skipping")
                submission.processing_status = "processed"
                await db.commit()
                return

            logger.info(f"🔍 Enriching Provider: {provider.display_name}")

            # ---- detect missing ----

            missing_keys = []

            if not provider.phone:
                missing_keys.append("phone")

            if not provider_prof.address_line1:
                missing_keys.append("practice_address")

            if not provider_prof.website:
                missing_keys.append("website")

            if not missing_keys:
                submission.processing_status = "processed"
                await db.commit()
                return

            # ---- build profile ----

            partial_profile = {
                "first_name": provider.first_name,
                "last_name": provider.last_name,
                "credential": provider_prof.taxonomy_code,
                "city": provider.city,
                "state": provider.state,
                "npi": provider.npi,
                "missing_fields": missing_keys
            }

            try:

                manager = EnrichmentManager()

                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None,
                    manager.enrich_profile,
                    partial_profile
                )

                print(result)

                # ---- parse agent output ----

                if isinstance(result, str):
                    result = extract_json_block(result)

                if not isinstance(result, dict):
                    raise ValueError("Agent returned non-dict")

                # ---- apply updates ----

                if result.get("phone") and not provider.phone:
                    provider.phone = result["phone"]

                if result.get("website") and not provider_prof.website:
                    provider_prof.website = result["website"]

                if result.get("practice_address") and not provider_prof.address_line1:
                    provider_prof.address_line1 = result["practice_address"]

                if provider.meta:
                    provider.meta.status = "enriched"
                    provider.meta.last_verified = datetime.utcnow()

                submission.processing_status = "enriched"

                await db.commit()

                logger.info("✅ Enrichment complete")

            except Exception as e:
                logger.exception("❌ Enrichment failed")

                submission.processing_status = "processed"
                await db.commit()

class SubmissionPipeline:
    @staticmethod
    async def run(submission_id: int):
        await ValidationService.process_submission(submission_id)
        await EnrichmentService.enrich_provider(submission_id)