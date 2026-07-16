from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

@app.post("/test/{room_name}")
async def test_route(room_name: str):
    return {"room": room_name}

client = TestClient(app)
resp = client.post("/test/myroom", data={"AnsweredBy": "human"})
print(resp.status_code)
print(resp.json())
