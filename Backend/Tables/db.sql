-- 1. Table: providers_master_per (Personal Info)
CREATE TABLE providers_master_per (
    npi VARCHAR PRIMARY KEY,
    display_name VARCHAR,
    first_name VARCHAR,
    last_name VARCHAR,
    phone VARCHAR,
    email VARCHAR,
    address_line1 VARCHAR,
    city VARCHAR,
    state VARCHAR,
    postal_code VARCHAR,
    country VARCHAR,
    field_metadata JSONB DEFAULT '{}'::jsonb
);
-- 2. Table: providers_master_prof (Professional Info)
CREATE TABLE providers_master_prof (
    id SERIAL PRIMARY KEY,
    npi VARCHAR NOT NULL REFERENCES providers_master_per(npi),
    practice_name VARCHAR,
    website VARCHAR,
    accepting_new_patients BOOLEAN,
    telehealth BOOLEAN,
    languages VARCHAR[], -- Array type for multiple languages
    address_line1 VARCHAR,
    city VARCHAR,
    state VARCHAR,
    postal_code VARCHAR,
    country VARCHAR,
    taxonomies JSONB, -- Storing list of dicts as JSONB
    taxonomy_code VARCHAR,
    specialties VARCHAR[],
    field_metadata JSONB DEFAULT '{}'::jsonb
);
-- 3. Table: providers_master_meta (Validation Metadata)
CREATE TABLE providers_master_meta (
    id SERIAL PRIMARY KEY,
    npi VARCHAR NOT NULL REFERENCES providers_master_per(npi),
    npi_status VARCHAR,
    npi_confidence FLOAT,
    name_status VARCHAR,
    name_confidence FLOAT,
    practice_status VARCHAR,
    practice_confidence FLOAT,
    address_status VARCHAR,
    address_confidence FLOAT,
    taxonomy_status VARCHAR,
    taxonomy_confidence FLOAT,
    license_status VARCHAR,
    license_confidence FLOAT,
    last_verified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    overall_confidence FLOAT,
    status VARCHAR DEFAULT 'needs_review',
    raw_data_json JSONB,
    manual_review_required BOOLEAN DEFAULT FALSE,
    confidence_score FLOAT DEFAULT 0.0,
    data_quality_flags VARCHAR[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- 4. Table: raw_provider_submissions (Submission Logs)
CREATE TABLE raw_provider_submissions (
    submission_id SERIAL PRIMARY KEY,
    source VARCHAR NOT NULL, -- 'form', 'csv'
    npi VARCHAR,
    input_payload JSONB,
    npi_api_response JSONB,
    processing_status VARCHAR DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);