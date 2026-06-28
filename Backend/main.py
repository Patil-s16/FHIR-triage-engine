import os
from fastapi import FastAPI # type: ignore
from database import get_postgres_connection, get_redis_connection

app = FastAPI(title="FHIR Triage Core API Engine")

def initialize_database_schemas():
    """Reads our SQL script and safely initializes PostgreSQL tables on startup."""
    conn = get_postgres_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # Read our layout script file
            sql_file_path = os.path.join(os.path.dirname(__file__), "init_db.sql")
            with open(sql_file_path, "r") as f:
                sql_script = f.read()
            
            # Execute the setup commands
            cursor.execute(sql_script)
            conn.commit()
            print("🚀 DATABASE SUCCESS: PostgreSQL relational tables built and sample patients registered.")
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"❌ DATABASE ERROR: Failed to run schema build: {e}")
    else:
        print("❌ DATABASE ERROR: PostgreSQL connection unavailable during initialization phase.")

@app.on_event("startup")
async def startup_event():
    # Automatically execute database verification when the app turns on
    initialize_database_schemas()

# --- MAKE SURE THIS EXACT BLOCK BELOW IS IN YOUR FILE ---
@app.get("/api/v1/debug/databases")
def test_database_health():
    """An API path to verify both storage buckets are alive and responsive."""
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