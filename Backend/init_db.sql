-- This script creates our permanent digital filing cabinet tables.

-- Table 1: Patient Demographics Master Registry
CREATE TABLE IF NOT EXISTS patients (
    patient_id VARCHAR(50) PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    bed_number VARCHAR(10) NOT NULL,
    admission_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table 2: Historical Telemetry Records (For long-term clinical charts)
CREATE TABLE IF NOT EXISTS vitals_history (
    record_id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES patients(patient_id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,
    heart_rate INT NOT NULL,
    systolic_bp INT NOT NULL,
    diastolic_bp INT NOT NULL,
    spo2 INT NOT NULL,
    triage_score INT NOT NULL,
    status VARCHAR(20) NOT NULL
);

-- Let's populate the registry with 3 sample patient beds for testing
INSERT INTO patients (patient_id, full_name, bed_number) 
VALUES 
('PT-001', 'Alice Smith', 'ICU-A1')
ON CONFLICT (patient_id) DO NOTHING;

INSERT INTO patients (patient_id, full_name, bed_number) 
VALUES 
('PT-002', 'Bob Jones', 'ICU-A2')
ON CONFLICT (patient_id) DO NOTHING;

INSERT INTO patients (patient_id, full_name, bed_number) 
VALUES 
('PT-003', 'Charlie Brown', 'ER-04')
ON CONFLICT (patient_id) DO NOTHING;
