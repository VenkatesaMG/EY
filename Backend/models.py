from sqlalchemy import String, Float, Text, JSON, DateTime, Integer, Boolean, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey
from datetime import datetime
from uuid import uuid4
from database import Base

class Provider_Personal(Base):
    __tablename__ = "providers_master_per"

    # Primary Key
    # provider_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Core Identification
    npi: Mapped[str] = mapped_column(String, primary_key=True, nullable=True)
    display_name: Mapped[str] = mapped_column(String, nullable=True) # Full Name # Can be removed
    
    # Granular components for validation (mapped to display_name parts usually)
    first_name: Mapped[str] = mapped_column(String, nullable=True) 
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    sex: Mapped[str] = mapped_column(String, nullable=True)
    
    # Contact Info
    phone: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True)
    
    # Address
    address_line1: Mapped[str] = mapped_column(String, nullable=True)
    city: Mapped[str] = mapped_column(String, nullable=True)
    state: Mapped[str] = mapped_column(String, nullable=True)
    postal_code: Mapped[str] = mapped_column(String, nullable=True)
    country: Mapped[str] = mapped_column(String, nullable=True)

class Provider_Professional(Base):
    __tablename__ = "providers_master_prof"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign Key
    npi: Mapped[str] = mapped_column(String, ForeignKey("providers_master_per.npi"), nullable=False)

    # Practice Info
    practice_name: Mapped[str] = mapped_column(String, nullable=True) # organization_name
    website: Mapped[str] = mapped_column(String, nullable=True)

    # Operational
    accepting_new_patients: Mapped[bool] = mapped_column(Boolean, nullable=True)
    telehealth: Mapped[bool] = mapped_column(Boolean, nullable=True)
    languages: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    
    # Organization Address
    address_line1: Mapped[str] = mapped_column(String, nullable=True)
    city: Mapped[str] = mapped_column(String, nullable=True)
    state: Mapped[str] = mapped_column(String, nullable=True)
    postal_code: Mapped[str] = mapped_column(String, nullable=True)
    country: Mapped[str] = mapped_column(String, nullable=True)

    # Professional Details
    taxonomies: Mapped[list[dict]] = mapped_column(JSON, nullable=True)
    # taxonomy_code: Mapped[str] = mapped_column(String, nullable=True)
    # specialties: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    # license_number: Mapped[str] = mapped_column(String, nullable=True) # From original request

    # --- RAW DATA STORE ---
    # raw_data_json: Mapped[dict] = mapped_column(JSON, nullable=True)

class Provider_Meta(Base):
    __tablename__ = "providers_master_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    npi: Mapped[String] = mapped_column(String, ForeignKey("providers_master_per.npi"), nullable=False)

    # --- VALIDATION METADATA (Per Attribute) ---
    # Capturing validation status/confidence for key fields as requested
    
    npi_status: Mapped[str] = mapped_column(String, nullable=True)
    npi_confidence: Mapped[float] = mapped_column(Float, nullable=True)

    name_status: Mapped[str] = mapped_column(String, nullable=True) # Validates display_name/first/last
    name_confidence: Mapped[float] = mapped_column(Float, nullable=True)

    practice_status: Mapped[str] = mapped_column(String, nullable=True)
    practice_confidence: Mapped[float] = mapped_column(Float, nullable=True)

    address_status: Mapped[str] = mapped_column(String, nullable=True)
    address_confidence: Mapped[float] = mapped_column(Float, nullable=True)

    taxonomy_status: Mapped[str] = mapped_column(String, nullable=True)
    taxonomy_confidence: Mapped[float] = mapped_column(Float, nullable=True)

    license_status: Mapped[str] = mapped_column(String, nullable=True)
    license_confidence: Mapped[float] = mapped_column(Float, nullable=True)

    # Metadata
    last_verified: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    overall_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, default="needs_review") # verified / needs_review / rejected

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RawProviderSubmission(Base):
    __tablename__ = "raw_provider_submissions"

    submission_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String, nullable=False) # 'form', 'csv'
    npi: Mapped[str] = mapped_column(String, nullable=True)
    
    input_payload: Mapped[dict] = mapped_column(JSON, nullable=True)
    npi_api_response: Mapped[dict] = mapped_column(JSON, nullable=True)
    
    processing_status: Mapped[str] = mapped_column(String, default="pending")
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)