CREATE TABLE raw_provider_submissions (
    submission_id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL, -- 'form', 'csv', 'api'
    npi VARCHAR(20),
    input_payload JSONB, -- The exact data sent from frontend/CSV
    npi_api_response JSONB, -- The raw response from NPI registry lookup
    processing_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processed', 'failed', 'enriched'
    error_message TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);
