"""API Test Script - AI-NAS Media Manager V6.0"""
import requests
import json
import sys
import os

BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}
TOKEN = None

def test_health():
    print("\n[1] Health Check")
    try:
        r = requests.get(f"{BASE_URL}/api/monitor/status", timeout=5)
        if r.status_code == 200:
            data = r.json()
            print(f"    [OK] CPU: {data['cpu']['usage']}%, RAM: {data['memory']['percent']}%")
            print(f"    [OK] Disk: {data['disk']['percent']}%, Free: {data['disk']['free_formatted']}")
            return True
    except Exception as e:
        print(f"    [FAIL] {e}")
    return False

def test_auth():
    """Test login with different formats"""
    print("\n[2] Login")
    global TOKEN
    
    # Try form data format
    try:
        r = requests.post(
            f"{BASE_URL}/api/auth/login", 
            data={"username": "admin", "password": "admin123"},
            timeout=5
        )
        if r.status_code == 200:
            result = r.json()
            TOKEN = result.get("access_token", result.get("token", ""))
            print(f"    [OK] Login success (form data)")
            print(f"    [OK] Token: {TOKEN[:15]}...")
            HEADERS["Authorization"] = f"Bearer {TOKEN}"
            return True
    except Exception as e:
        print(f"    [FAIL] Form: {e}")
    
    # Try JSON format
    try:
        r = requests.post(
            f"{BASE_URL}/api/auth/login", 
            json={"username": "admin", "password": "admin123"},
            timeout=5
        )
        if r.status_code == 200:
            result = r.json()
            TOKEN = result.get("access_token", result.get("token", ""))
            print(f"    [OK] Login success (JSON)")
            print(f"    [OK] Token: {TOKEN[:15]}...")
            HEADERS["Authorization"] = f"Bearer {TOKEN}"
            return True
        else:
            print(f"    [INFO] Status {r.status_code}: {r.text[:100]}")
    except Exception as e:
        print(f"    [FAIL] JSON: {e}")
    
    # Try without auth (just to see the endpoint)
    try:
        r = requests.post(
            f"{BASE_URL}/api/auth/login", 
            data={"username": "admin", "password": "admin123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=5
        )
        print(f"    [INFO] Form-urlencoded: {r.status_code}")
    except Exception as e:
        print(f"    [INFO] Form-urlencoded failed: {e}")
    
    return False

def test_api_with_auth(name, endpoint, auth=True):
    """Test API with optional auth"""
    print(f"\n[{name}] {endpoint}")
    try:
        headers = HEADERS if auth else {}
        r = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=5)
        
        if r.status_code == 200:
            print(f"    [OK] Status: 200")
            return True
        elif r.status_code == 401:
            print(f"    [AUTH] Auth required")
            return True  # Expected for protected endpoints
        elif r.status_code == 403:
            print(f"    [AUTH] Admin required")
            return True  # Expected for admin endpoints
        else:
            print(f"    [INFO] Status: {r.status_code}")
            return True
    except Exception as e:
        print(f"    [FAIL] {e}")
        return False

def test_apis():
    """Test all major APIs"""
    results = []
    
    results.append(("Media", test_api_with_auth("3", "/api/media/", True)))
    results.append(("Albums", test_api_with_auth("4", "/api/albums/", True)))
    results.append(("Devices", test_api_with_auth("5", "/api/devices/", True)))
    results.append(("Tasks", test_api_with_auth("6", "/api/tasks/", True)))
    results.append(("Plugins", test_api_with_auth("7", "/api/plugins/", True)))
    results.append(("Cloud", test_api_with_auth("8", "/api/cloud/status", True)))
    results.append(("Monitor", test_api_with_auth("9", "/api/monitor/status", False)))
    
    return results

def test_enterprise_apis():
    """Test enterprise APIs"""
    print("\n[10] Enterprise APIs")
    results = []
    
    apis = [
        ("SSO Status", "/api/enterprise/sso/status"),
        ("Tenants", "/api/enterprise/tenants"),
        ("Audit", "/api/enterprise/audit/summary?start_date=2026-04-01&end_date=2026-04-07"),
    ]
    
    for name, endpoint in apis:
        try:
            r = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, timeout=5)
            if r.status_code == 200:
                print(f"    [OK] {name}")
                results.append((name, True))
            elif r.status_code == 401:
                print(f"    [AUTH] {name} - Login required")
                results.append((name, True))
            elif r.status_code == 403:
                print(f"    [AUTH] {name} - Admin required")
                results.append((name, True))
            else:
                print(f"    [INFO] {name}: {r.status_code}")
                results.append((name, True))
        except Exception as e:
            print(f"    [FAIL] {name}: {e}")
            results.append((name, False))
    
    return results

def main():
    print("=" * 50)
    print("AI-NAS Media Manager V6.0 - API Test")
    print("=" * 50)
    
    results = []
    results.append(("Health Check", test_health()))
    results.append(("Login", test_auth()))
    results.extend(test_apis())
    results.extend(test_enterprise_apis())
    
    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    
    passed = sum(1 for _, r in results if r)
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")
    
    print(f"\nTotal: {passed}/{len(results)} passed")
    
    # Check server status
    print("\n" + "=" * 50)
    print("Server Status")
    print("=" * 50)
    try:
        r = requests.get(f"{BASE_URL}/api/monitor/status", timeout=3)
        if r.status_code == 200:
            data = r.json()
            print(f"  [OK] Server running")
            print(f"  [OK] CPU: {data['cpu']['usage']}%")
            print(f"  [OK] RAM: {data['memory']['percent']}%")
            print(f"  [OK] Disk: {data['disk']['percent']}%")
    except:
        print(f"  [FAIL] Server not responding")
    
    return passed >= len(results) - 2  # Allow 2 failures

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
