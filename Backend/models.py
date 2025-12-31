from sqlalchemy import String, Float, Text, JSON, DateTime, Integer, Boolean, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from uuid import uuid4
from database import Base

class Provider(Base):
    __tablename__ = "providers_master"

    # Primary Key
    provider_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Core Identification
    npi: Mapped[str] = mapped_column(String, unique=True, nullable=True)
    display_name: Mapped[str] = mapped_column(String, nullable=True) # Full Name
    
    # Granular components for validation (mapped to display_name parts usually)
    first_name: Mapped[str] = mapped_column(String, nullable=True) 
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    
    # Professional Details
    taxonomy_code: Mapped[str] = mapped_column(String, nullable=True)
    specialties: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    license_number: Mapped[str] = mapped_column(String, nullable=True) # From original request
    
    # Contact Info
    phone: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True)
    website: Mapped[str] = mapped_column(String, nullable=True)
    
    # Practice Info
    practice_name: Mapped[str] = mapped_column(String, nullable=True) # organization_name
    
    # Address (Golden Record)
    address_line1: Mapped[str] = mapped_column(String, nullable=True)
    city: Mapped[str] = mapped_column(String, nullable=True)
    state: Mapped[str] = mapped_column(String, nullable=True)
    postal_code: Mapped[str] = mapped_column(String, nullable=True)
    country: Mapped[str] = mapped_column(String, nullable=True)
    
    # Operational
    accepting_new_patients: Mapped[bool] = mapped_column(Boolean, nullable=True)
    telehealth: Mapped[bool] = mapped_column(Boolean, nullable=True)
    languages: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    
    # Metadata
    last_verified: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    overall_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, default="needs_review") # verified / needs_review / rejected
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # --- RAW DATA STORE ---
    raw_data_json: Mapped[dict] = mapped_column(JSON, nullable=True)

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
