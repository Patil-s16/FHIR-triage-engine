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

def get_postgres_connection():
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="fhir_triage",
            user="user",
            password="password"
        )
        return conn
    except Exception as e:
        print(f"CRITICAL ERROR: Could not connect to PostgreSQL Database! Details: {e}")
        return None

def get_redis_connection():
    try:
        client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
        return client
    except Exception as e:
        print(f"CRITICAL ERROR: Could not connect to Redis! Details: {e}")
        return None