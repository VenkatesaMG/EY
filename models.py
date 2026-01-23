import os
import shutil
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, DateTime, func, String, Float, Boolean, Integer
from sqlalchemy.dialects.postgresql import JSONB, ARRAY

ROOT_DIRECTORY = ""
# --- 1. The Master Table (Target) ---
class ProvidersMaster(SQLModel, table=True):
    __tablename__ = "providers_master"

    # Primary Key
    provider_id: Optional[int] = Field(default=None, primary_key=True)
    
    # Basic Info
    display_name: Optional[str] = None
    npi: Optional[str] = Field(default=None, index=True)
    taxonomy_code: Optional[str] = None
    org_or_ind: Optional[bool] = None
    
    # Array Fields (Requires sa_column for PostgreSQL Arrays)
    specialties: List[str] = Field(default=[], sa_column=Column(ARRAY(String)))
    languages: List[str] = Field(default=[], sa_column=Column(ARRAY(String)))

    # Contact Info
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    practice_name: Optional[str] = None
    
    # Location
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    
    # Note: Geolocation (GEOGRAPHY) usually requires GeoAlchemy2. 
    # For standard SQLModel, we often skip defining it here or use a raw column if needed.
    # geolocation: Optional[Any] = Field(default=None, sa_column=Column(Geography...))

    # Operational
    accepting_new_patients: Optional[bool] = None
    telehealth: Optional[bool] = None
    
    # Metadata
    last_verified: Optional[datetime] = None
    overall_confidence: Optional[float] = None
    status: Optional[str] = Field(default="verified") # verified / needs_review / rejected
    
    # Timestamps
    created_at: Optional[datetime] = Field(
        default=None, 
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        default=None, 
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    )

# --- 2. The Raw Ingestion Table (Source) ---
class ProvidersRaw(SQLModel, table=True):
    __tablename__ = "providers_raw"

    raw_id: Optional[int] = Field(default=None, primary_key=True)

    # JSONB Payload
    payload: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    
    uploaded_at: Optional[datetime] = Field(
        default=None, 
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    
    status: Optional[str] = Field(default="new")
    
    # Directory Path
    directory: List[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))

    # Foreign Key Linking to Master
    provider_master_id: Optional[int] = Field(
        default=None, 
        foreign_key="providers_master.provider_id"
    )