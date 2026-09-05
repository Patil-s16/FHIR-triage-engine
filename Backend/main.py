import os
import json
from fastapi import FastAPI # type: ignore
from pydantic import BaseModel
from database import get_postgres_connection, get_redis_connection
from triage_engine import calculate_news2_score
from fhir_mapper import convert_telemetry_to_fhir_bundle

app = FastAPI(title="FHIR Triage Core API Engine")

# --- DATA MODELS ---
class TelemetryPayload(BaseModel):
    bed_id: str
    heart_rate: int
    blood_pressure: str
    spo2: int
    status: str

# --- DATABASE SCHEMA SETUP ---
def initialize_database_schemas():
    conn = get_postgres_connection()
    if conn:
        try:
            cursor = conn.cursor()
            sql_file_path = os.path.join(os.path.dirname(__file__), "init_db.sql")
            if os.path.exists(sql_file_path):
                with open(sql_file_path, "r") as f:
                    sql_script = f.read()
                cursor.execute(sql_script)
                conn.commit()
                print("DATABASE SUCCESS: PostgreSQL tables built and verified successfully.")
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"DATABASE ERROR: Schema build failed: {e}")

@app.on_event("startup")
async def startup_event():
    initialize_database_schemas()

# --- HEALTH CHECK ENDPOINT ---
@app.get("/api/v1/debug/databases")
def test_database_health():
    redis_client = get_redis_connection()
    pg_conn = get_postgres_connection()
    
    redis_status = "Connected" if redis_client and redis_client.ping() else "Disconnected"
    pg_status = "Connected" if pg_conn else "Disconnected"
    
    if pg_conn:
        pg_conn.close()
        
    return {
        "bucket_a_redis_live_cache": redis_status,
        "bucket_b_postgres_historical_vault": pg_status
    }

# --- TELEMETRY INGESTION ENDPOINT ---
@app.post("/api/v1/telemetry")
async def receive_telemetry(payload: TelemetryPayload):
    # 1. Parse Blood Pressure ("120/80" -> 120 and 80)
    try:
        bp_parts = payload.blood_pressure.split("/")
        sys_bp = int(bp_parts[0])
        dia_bp = int(bp_parts[1]) if len(bp_parts) > 1 else 80
    except Exception:
        sys_bp, dia_bp = 120, 80

    # 2. Compute NEWS2 clinical risk score
    triage_result = calculate_news2_score(payload.heart_rate, payload.spo2, sys_bp)

    # 3. Build HL7 FHIR Bundle
    fhir_bundle = convert_telemetry_to_fhir_bundle(payload.bed_id, payload.heart_rate, payload.spo2, sys_bp)

    # 4. Create processed response structure
    processed_record = {
        "bed_id": payload.bed_id,
        "heart_rate": payload.heart_rate,
        "blood_pressure": payload.blood_pressure,
        "spo2": payload.spo2,
        "news2_score": triage_result["news2_score"],
        "triage_priority": triage_result["triage_priority"],
        "fhir_bundle": fhir_bundle
    }

    # 5. Cache Live Status in Redis
    redis_client = get_redis_connection()
    if redis_client:
        redis_client.set(f"bed:{payload.bed_id}", json.dumps(processed_record))

    # 6. Archive Historical Record in PostgreSQL
    pg_conn = get_postgres_connection()
    if pg_conn:
        try:
            cursor = pg_conn.cursor()
            insert_query = """
                INSERT INTO vitals_history 
                (patient_id, heart_rate, systolic_bp, diastolic_bp, spo2, triage_score, status, fhir_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """
            cursor.execute(insert_query, (
                payload.bed_id,
                payload.heart_rate,
                sys_bp,
                dia_bp,
                payload.spo2,
                triage_result["news2_score"],
                triage_result["triage_priority"],
                json.dumps(fhir_bundle)
            ))
            pg_conn.commit()
            cursor.close()
            pg_conn.close()
        except Exception as e:
            print(f" PostgreSql Archive Error: {e}")

    print(f" 🚨 TRIAGE & FHIR STORED [{payload.bed_id}]: {triage_result['triage_priority']} (Score: {triage_result['news2_score']})")

    return {
        "status": "processed", 
        "triage_result": processed_record
    }

# --- REAL-TIME BED STATUS ENDPOINT (REDIS) ---
@app.get("/api/v1/bed/{bed_id}")
def get_bed_status(bed_id: str):
    """Fetches real-time cached triage status and FHIR bundle for a bed from Redis."""
    redis_client = get_redis_connection()
    if not redis_client:
        return {"error": "Redis cache unavailable"}
        
    data = redis_client.get(f"bed:{bed_id}")
    if data:
        return json.loads(data)
    return {"message": f"No telemetry data found in cache for {bed_id}"}

# --- FHIR BUNDLE EXPORTER ENDPOINT ---
@app.get("/api/v1/bed/{bed_id}/fhir")
def get_bed_fhir_bundle(bed_id: str):
    """Retrieves standard FHIR Bundle JSON structure for EMR system integration."""
    redis_client = get_redis_connection()
    if not redis_client:
        return {"error": "Redis cache unavailable"}
        
    data = redis_client.get(f"bed:{bed_id}")
    if data:
        record = json.loads(data)
        return record.get("fhir_bundle", {})
    return {"message": f"No FHIR data found for {bed_id}"}

# --- HISTORICAL VITALS ENDPOINT (POSTGRESQL) ---
@app.get("/api/v1/bed/{bed_id}/history")
def get_bed_vitals_history(bed_id: str, limit: int = 10):
    """Retrieves the most recent historical vital records from PostgreSQL for plotting clinical trends."""
    pg_conn = get_postgres_connection()
    if not pg_conn:
        return {"error": "PostgreSQL database connection unavailable"}
    
    try:
        cursor = pg_conn.cursor()
        query = """
            SELECT record_id, patient_id, timestamp, heart_rate, systolic_bp, diastolic_bp, spo2, triage_score, status
            FROM vitals_history
            WHERE patient_id = %s
            ORDER BY timestamp DESC
            LIMIT %s;
        """
        cursor.execute(query, (bed_id, limit))
        rows = cursor.fetchall()
        
        history = []
        for row in rows:
            history.append({
                "record_id": row[0],
                "bed_id": row[1],
                "timestamp": row[2].isoformat() if row[2] else None,
                "heart_rate": row[3],
                "systolic_bp": row[4],
                "diastolic_bp": row[5],
                "spo2": row[6],
                "triage_score": row[7],
                "status": row[8]
            })
            
        cursor.close()
        pg_conn.close()
        return {
            "bed_id": bed_id,
            "total_records_retrieved": len(history),
            "vitals_history": history
        }
    except Exception as e:
        return {"error": f"Database query failed: {str(e)}"}