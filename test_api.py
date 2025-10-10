# test_api.py
import sys
import traceback

try:
    print("Testing app import...")
    import app
    print("PASS: App imported successfully")
    
    print("Testing FastAPI app creation...")
    from fastapi.testclient import TestClient
    client = TestClient(app.app)
    print("PASS: TestClient created successfully")
    
    print("Testing rankings endpoint...")
    response = client.get("/api/rankings?state=AZ&gender=MALE&year=2014")
    print(f"PASS: Rankings endpoint status: {response.status_code}")
    print(f"PASS: Response data length: {len(response.json()) if response.status_code == 200 else 'Error'}")
    
except Exception as e:
    print(f"ERROR: {e}")
    print("Full traceback:")
    traceback.print_exc()