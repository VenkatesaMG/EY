from sqlalchemy import String, Float, Text, JSON, DateTime, Integer, Boolean, ARRAY, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from uuid import uuid4
from database import Base

# 1. Personal Info Table
class ProviderPersonal(Base):
    __tablename__ = "providers_master_per"

    # Core Identification
    npi: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(String, nullable=True) # Full Name
    
    # Granular components
    first_name: Mapped[str] = mapped_column(String, nullable=True) 
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    
    # Contact Info
    phone: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True)
    
    # Personal Address (if applicable, though often practice address is used)
    address_line1: Mapped[str] = mapped_column(String, nullable=True)
    city: Mapped[str] = mapped_column(String, nullable=True)
    state: Mapped[str] = mapped_column(String, nullable=True)
    postal_code: Mapped[str] = mapped_column(String, nullable=True)
    country: Mapped[str] = mapped_column(String, nullable=True)
    
    # Data Governance Sidecar
    field_metadata: Mapped[dict] = mapped_column(JSON, default={}, nullable=True)

    # Relationships
    professional: Mapped["ProviderProfessional"] = relationship(back_populates="personal", uselist=False, cascade="all, delete-orphan")
    meta: Mapped["ProviderMeta"] = relationship(back_populates="personal", uselist=False, cascade="all, delete-orphan")


# 2. Professional Info Table
class ProviderProfessional(Base):
    __tablename__ = "providers_master_prof"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key
    npi: Mapped[str] = mapped_column(String, ForeignKey("providers_master_per.npi"), nullable=False, unique=True)
    
    # Practice Info
    practice_name: Mapped[str] = mapped_column(String, nullable=True) 
    website: Mapped[str] = mapped_column(String, nullable=True)
    
    # Operational
    accepting_new_patients: Mapped[bool] = mapped_column(Boolean, nullable=True)
    telehealth: Mapped[bool] = mapped_column(Boolean, nullable=True)
    languages: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    
    # Organization Address / Practice Address
    address_line1: Mapped[str] = mapped_column(String, nullable=True)
    city: Mapped[str] = mapped_column(String, nullable=True)
    state: Mapped[str] = mapped_column(String, nullable=True)
    postal_code: Mapped[str] = mapped_column(String, nullable=True)
    country: Mapped[str] = mapped_column(String, nullable=True)

    # Professional Details
    taxonomies: Mapped[list[dict]] = mapped_column(JSON, nullable=True)
    # Keeping these for backward compatibility/ease of access if needed, or derived from taxonomies
    taxonomy_code: Mapped[str] = mapped_column(String, nullable=True) 
    specialties: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    
    # Data Governance Sidecar
    field_metadata: Mapped[dict] = mapped_column(JSON, default={}, nullable=True)

    # Relationship
    personal: Mapped["ProviderPersonal"] = relationship(back_populates="professional")


# 3. Meta/Validation Table
class ProviderMeta(Base):
    __tablename__ = "providers_master_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    npi: Mapped[str] = mapped_column(String, ForeignKey("providers_master_per.npi"), nullable=False, unique=True)

    # Validation Field Status
    npi_status: Mapped[str] = mapped_column(String, nullable=True)
    npi_confidence: Mapped[float] = mapped_column(Float, nullable=True)

    name_status: Mapped[str] = mapped_column(String, nullable=True)
    name_confidence: Mapped[float] = mapped_column(Float, nullable=True)

    practice_status: Mapped[str] = mapped_column(String, nullable=True)
    practice_confidence: Mapped[float] = mapped_column(Float, nullable=True)

    address_status: Mapped[str] = mapped_column(String, nullable=True)
    address_confidence: Mapped[float] = mapped_column(Float, nullable=True)

    taxonomy_status: Mapped[str] = mapped_column(String, nullable=True)
    taxonomy_confidence: Mapped[float] = mapped_column(Float, nullable=True)

    license_status: Mapped[str] = mapped_column(String, nullable=True)
    license_confidence: Mapped[float] = mapped_column(Float, nullable=True)

    # Overall Metadata
    last_verified: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    overall_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, default="needs_review") 
    
    # Data Governance Flags
    manual_review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    data_quality_flags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)

    # We can store the raw payload here or in a separate raw_data column if needed, 
    # but the prompt didn't specify it in this table. 
    # However, keeping it is useful for the app logic.
    raw_data_json: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    personal: Mapped["ProviderPersonal"] = relationship(back_populates="meta")


# 4. Submission Log
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


# 5. Market Opportunities (Kept as is)
class MarketExpansionOpportunity(Base):
    __tablename__ = "market_expansion_opportunities"

    opportunity_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    
    # Association with Provider
    provider_id: Mapped[int] = mapped_column(Integer, nullable=True) # Linked to providers_master id if we had one, or use NPI
    provider_npi: Mapped[str] = mapped_column(String, nullable=True) # Adding NPI reference since ID is split

    # Category and Geography
    category: Mapped[str] = mapped_column(String, nullable=False)
    target_region: Mapped[str] = mapped_column(String, nullable=True)
    state: Mapped[str] = mapped_column(String, nullable=True)
    
    # Market Metrics
    patient_demand_index: Mapped[float] = mapped_column(Float, nullable=True)
    current_network_adequacy: Mapped[float] = mapped_column(Float, nullable=True)
    competition_density: Mapped[float] = mapped_column(Float, nullable=True)
    
    # Financials
    avg_procedure_cost: Mapped[float] = mapped_column(Float, nullable=True)
    projected_revenue_growth: Mapped[float] = mapped_column(Float, nullable=True)
    
    # Analysis
    expansion_priority_score: Mapped[float] = mapped_column(Float, nullable=True)
    recommendation_status: Mapped[str] = mapped_column(String, default="potential")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_analyzed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
