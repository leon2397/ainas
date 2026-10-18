import requests
from loguru import logger
import json

# Test API
BASE_URL = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc3NTY4OTk2MX0.tDJSDC_-gEJk8gpgdIrq9Fl921w_wnx9rJi-_Wax-3E"

headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# Test GET settings
logger.info("=== GET /api/system/settings ===")
resp = requests.get(f"{BASE_URL}/api/system/settings", headers=headers)
logger.info(f"Status: {resp.status_code}")
logger.info(f"Response: {json.dumps(resp.json(), indent=2, ensure_ascii=False)[:500]}...")

# Test PUT settings
logger.info("\n=== PUT /api/system/settings ===")
data = {"category": "global", "settings": {"server": {"host": "AI-NAS-Test-v2"}}}
resp = requests.put(f"{BASE_URL}/api/system/settings", headers=headers, json=data)
logger.info(f"Status: {resp.status_code}")
logger.info(f"Response: {resp.text}")

# Verify update
logger.info("\n=== Verify Update ===")
resp = requests.get(f"{BASE_URL}/api/system/settings?category=global", headers=headers)
logger.info(f"Status: {resp.status_code}")
data = resp.json()
logger.info(f"server.host = {data.get('server', {}).get('host', 'N/A')}")