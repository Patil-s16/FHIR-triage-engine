import os
import json
from fastapi import FastAPI # type: ignore
from pydantic import BaseModel # pyright: ignore[reportMissingImports]
from database import get_postgres_connection, get_redis_connection
from triage_engine import calculate_news2_score

app = FastAPI(title="FHIR Triage Core API Engine")

class TelemetryPayload(BaseModel):
    bed_id: str
    heart_rate: int
    blood_pressure: str
    spo2: int
    status: str

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
                print("DATABASE SUCCESS: PostgreSQL tables built successfully.")
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"DATABASE ERROR: Schema build failed: {e}")

@app.on_event("startup")
async def startup_event():
    initialize_database_schemas()

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

@app.post("/api/v1/telemetry")
async def receive_telemetry(payload: TelemetryPayload):
    # 1. Parse Systolic BP from format like "120/80"
    try:
        sys_bp = int(payload.blood_pressure.split("/")[0])
    except Exception:
        sys_bp = 120

    # 2. Compute NEWS2 clinical risk score
    triage_result = calculate_news2_score(payload.heart_rate, payload.spo2, sys_bp)

    # 3. Create full structured record
    processed_record = {
        "bed_id": payload.bed_id,
        "heart_rate": payload.heart_rate,
        "blood_pressure": payload.blood_pressure,
        "spo2": payload.spo2,
        "news2_score": triage_result["news2_score"],
        "triage_priority": triage_result["triage_priority"]
    }

    # 4. Cache in Redis for instant retrieval (Key: bed_id)
    redis_client = get_redis_connection()
    if redis_client:
        redis_client.set(f"bed:{payload.bed_id}", json.dumps(processed_record))

    print(f" 🚨 TRIAGE EVALUATED [{payload.bed_id}]: {triage_result['triage_priority']} (Score: {triage_result['news2_score']})")

    return {
        "status": "processed", 
        "triage_result": processed_record
    }

# --- NEW ENDPOINT: Get Latest Status for Any Bed from Redis ---
@app.get("/api/v1/bed/{bed_id}")
def get_bed_status(bed_id: str):
    """Fetches real-time cached triage status for a specific bed from Redis."""
    redis_client = get_redis_connection()
    if not redis_client:
        return {"error": "Redis cache unavailable"}
        
    data = redis_client.get(f"bed:{bed_id}")
    if data:
        return json.loads(data)
    return {"message": f"No telemetry data found in cache for {bed_id}"}