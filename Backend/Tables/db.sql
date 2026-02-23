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
    languages VARCHAR[], 
    address_line1 VARCHAR,
    city VARCHAR,
    state VARCHAR,
    postal_code VARCHAR,
    country VARCHAR,
    taxonomies JSONB, 
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
    verification_token VARCHAR UNIQUE,
    token_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Table: raw_provider_submissions (Submission Logs)
CREATE TABLE raw_provider_submissions (
    submission_id SERIAL PRIMARY KEY,
    source VARCHAR NOT NULL, 
    npi VARCHAR,
    input_payload JSONB,
    npi_api_response JSONB,
    processing_status VARCHAR DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Table: market_expansion_opportunities (Analytics/Opportunities)
CREATE TABLE market_expansion_opportunities (
    opportunity_id VARCHAR PRIMARY KEY,
    provider_id INTEGER,
    provider_npi VARCHAR,
    category VARCHAR NOT NULL,
    target_region VARCHAR,
    state VARCHAR,
    patient_demand_index FLOAT,
    current_network_adequacy FLOAT,
    competition_density FLOAT,
    avg_procedure_cost FLOAT,
    projected_revenue_growth FLOAT,
    expansion_priority_score FLOAT,
    recommendation_status VARCHAR DEFAULT 'potential',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Table: provider_audit_log (Change History / Audit Trail)
CREATE TABLE provider_audit_log (
    id SERIAL PRIMARY KEY,
    npi VARCHAR NOT NULL,
    field_name VARCHAR NOT NULL,
    table_name VARCHAR,
    old_value TEXT,
    new_value TEXT,
    change_source VARCHAR NOT NULL,
    actor VARCHAR,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_log_npi ON provider_audit_log(npi);
CREATE INDEX idx_audit_log_changed_at ON provider_audit_log(changed_at);
