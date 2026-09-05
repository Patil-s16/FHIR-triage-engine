# backend/fhir_mapper.py

from datetime import datetime, timezone

# LOINC Codes for standardized medical coding
LOINC_CODES = {
    "heart_rate": {"code": "8867-4", "display": "Heart rate", "unit": "beats/min", "unit_code": "/min"},
    "spo2": {"code": "2708-6", "display": "Oxygen saturation in Arterial blood by Pulse oximetry", "unit": "%", "unit_code": "%"},
    "systolic_bp": {"code": "8480-6", "display": "Systolic blood pressure", "unit": "mmHg", "unit_code": "mm[Hg]"}
}

def create_fhir_observation(bed_id: str, vital_type: str, value: int) -> dict:
    """
    Builds an HL7 FHIR R4 compliant Observation Resource for a single vital sign.
    """
    meta = LOINC_CODES.get(vital_type, {})
    timestamp = datetime.now(timezone.utc).isoformat()
    
    fhir_resource = {
        "resourceType": "Observation",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": meta.get("code", "UNKNOWN"),
                    "display": meta.get("display", vital_type)
                }
            ],
            "text": meta.get("display", vital_type)
        },
        "subject": {
            "reference": f"Patient/{bed_id}",
            "display": f"Patient assigned to Bed {bed_id}"
        },
        "effectiveDateTime": timestamp,
        "valueQuantity": {
            "value": value,
            "unit": meta.get("unit", ""),
            "system": "http://unitsofmeasure.org",
            "code": meta.get("unit_code", "")
        }
    }
    return fhir_resource

def convert_telemetry_to_fhir_bundle(bed_id: str, heart_rate: int, spo2: int, sys_bp: int) -> dict:
    """
    Packages all individual vital observations into a unified FHIR Bundle.
    """
    hr_obs = create_fhir_observation(bed_id, "heart_rate", heart_rate)
    spo2_obs = create_fhir_observation(bed_id, "spo2", spo2)
    bp_obs = create_fhir_observation(bed_id, "systolic_bp", sys_bp)
    
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {"resource": hr_obs},
            {"resource": spo2_obs},
            {"resource": bp_obs}
        ]
    }
    return bundle