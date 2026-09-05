import asyncio
import random
import httpx
import logging

# Configure clear logging output
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BACKEND_URL = "http://127.0.0.1:8000/api/v1/telemetry" # Your FastAPI endpoint
TOTAL_BEDS = 50
SIMULATION_INTERVAL = 3.0  # Sends vitals every 3 seconds

def generate_vitals(bed_id: int):
    """Generates realistic vital signs based on patient state spikes"""
    state = random.choices(["stable", "critical"], weights=[0.85, 0.15])[0]
    
    if state == "stable":
        return {
            "bed_id": f"BED-{bed_id:03d}",
            "heart_rate": random.randint(65, 95),
            "blood_pressure": f"{random.randint(110, 130)}/{random.randint(70, 85)}",
            "spo2": random.randint(95, 100),
            "status": "STABLE"
        }
    else:
        return {
            "bed_id": f"BED-{bed_id:03d}",
            "heart_rate": random.choice([random.randint(40, 55), random.randint(120, 160)]),
            "blood_pressure": f"{random.randint(85, 100)}/{random.randint(50, 65)}",
            "spo2": random.randint(82, 89),
            "status": "CRITICAL"
        }

async def simulate_single_bed(bed_id: int, client: httpx.AsyncClient):
    """Manages an infinite background loop for one specific hospital bed"""
    logging.info(f"Initialized background task for Bed #{bed_id}")
    while True:
        vitals = generate_vitals(bed_id)
        try:
            # Send payload asynchronously over HTTP POST
            response = await client.post(BACKEND_URL, json=vitals, timeout=2.0)
            if response.status_code == 200:
                logging.info(f" Successfully transmitted metrics for {vitals['bed_id']} | Status: {vitals['status']}")
            else:
                logging.warning(f" Backend rejected packet from Bed {bed_id}: Status {response.status_code}")
        except httpx.RequestError as exc:
            logging.error(f" Network connection error for Bed {bed_id}: {exc}")
        
        # Non-blocking pause before sending the next telemetry broadcast
        await asyncio.sleep(SIMULATION_INTERVAL)

async def main():
    """Spawns 50 parallel asynchronous tasks managing concurrent telemetry loops"""
    logging.info(f"Starting FHIR Triage Engine Telemetry Core. Activating {TOTAL_BEDS} beds...")
    
    # Using an AsyncClient connection pool for rapid high-throughput connections
    async with httpx.AsyncClient() as client:
        tasks = [simulate_single_bed(bed_id, client) for bed_id in range(1, TOTAL_BEDS + 1)]
        # Run all 50 loops completely concurrently
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Telemetry generation manually halted. Shutting down simulator safely.")