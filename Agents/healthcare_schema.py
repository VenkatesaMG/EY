from typing import List, Optional, Dict, Any, Literal
from datetime import date
from pydantic import BaseModel, Field, field_validator

class Address(BaseModel):
    street_address_1: Optional[str] = Field(None, description="Primary street line")
    street_address_2: Optional[str] = Field(None, description="Suite, Unit, or Building")
    city: Optional[str] = Field(None)
    state: Optional[str] = Field(None, description="2-letter state code")
    zip_code: Optional[str] = Field(None, description="5 or 9 digit zip")
    address_type: Literal["Practice", "Mailing", "Billing"] = "Practice"
    phone: Optional[str] = None
    fax: Optional[str] = None
    is_wheelchair_accessible: Optional[bool] = None

class License(BaseModel):
    license_number: Optional[str] = None
    state: Optional[str] = None
    license_type: Optional[str] = None
    status: Optional[str] = None
    expiry_date: Optional[date] = None

class Certification(BaseModel):
    board_name: Optional[str] = None
    specialty_name: Optional[str] = None
    initial_certification_date: Optional[date] = None

class Affiliation(BaseModel):
    entity_name: Optional[str] = None
    relationship_type: Optional[str] = None
    start_date: Optional[date] = None

# --- Main Profile Schema (Updated for Organizations) ---

class HealthcareProviderProfile(BaseModel):
    # -- Core Identity --
    provider_type: Literal["Individual", "Organization", "Unknown"] = Field("Unknown", description="Is this a person (Doctor) or an Entity (Hospital/Clinic)?")
    
    npi: Optional[str] = Field(None, description="10-digit National Provider Identifier")
    tax_id: Optional[str] = Field(None, description="EIN or TIN for Organizations")
    
    # -- Individual Fields --
    first_name: Optional[str] = Field(None)
    last_name: Optional[str] = Field(None)
    middle_name: Optional[str] = None
    credential: Optional[str] = None # MD, DO, NP
    gender: Optional[str] = None
    
    # -- Organization Fields (NEW) --
    organization_name: Optional[str] = Field(None, description="Legal Business Name if Provider is an Organization")
    
    # -- Contact --
    primary_email: Optional[str] = None
    website_url: Optional[str] = None
    
    # -- Professional --
    taxonomy_codes: List[str] = Field(default_factory=list)
    specialties: List[str] = Field(default_factory=list)
    licenses: List[License] = Field(default_factory=list)
    certifications: List[Certification] = Field(default_factory=list)
    
    # -- Operations --
    accepting_new_patients: Optional[bool] = None
    offers_telehealth: Optional[bool] = None
    languages_spoken: List[str] = Field(default_factory=list)
    
    # -- Locations & Affiliations --
    locations: List[Address] = Field(default_factory=list)
    affiliations: List[Affiliation] = Field(default_factory=list)

    # -- Metadata --
    data_confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    last_verified_date: Optional[date] = None
    verification_sources: List[str] = Field(default_factory=list)
    
    # -- Catch-all for "Additional Fields" --
    other_info: Dict[str, Any] = Field(default_factory=dict, description="Any other relevant identifiers found (e.g. DEA Number, CLIA ID, etc.)")

    @field_validator('npi', mode='before')
    @classmethod
    def validate_npi(cls, v):
        if not v or v == "null" or v == "":
            return None
        if len(str(v)) != 10:
            return None
        return str(v)