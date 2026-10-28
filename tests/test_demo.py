from fastapi import FastAPI
from fastapi.testclient import TestClient


demo_app = FastAPI()

@demo_app.get("/")
def demo_home():
    return {"message" : "Hello"}

client = TestClient(demo_app)

def test_home_page():
    response = client.get("/")
    assert response.status_code == 200
    
# This is synchronous approach but since our app uses an async database stack. so we have an async engine, async routers etc
# therefore for our app we will use asynchronous approach
    