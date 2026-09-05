import os
import time
import psycopg2 # type: ignore

try:
    import redis # type: ignore
except ImportError:
    redis = None

# 1. Pull secret credentials from our .env ecosystem
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_NAME = os.getenv("POSTGRES_DB", "fhir_triage_records")
DB_USER = os.getenv("POSTGRES_USER", "health_admin")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "SecureHospitalNetwork2026!")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# --- BUCKET A CONNECTOR: REDIS LIVE MEMORY ---
def get_redis_connection():
    """Establishes a high-velocity link to the Redis live cache cluster."""
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        # Ping check to confirm it is alive
        r.ping()
        return r
    except redis.ConnectionError:
        print(" CRITICAL ERROR: Could not connect to Redis Cache!")
        return None

# --- BUCKET B CONNECTOR: POSTGRESQL PERMANENT STORAGE ---
def get_postgres_connection():
    """Establishes a connection to our long-term relational ledger."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn
    except Exception as e:
        print(f" CRITICAL ERROR: Could not connect to PostgreSQL Database! Details: {e}")
        return None