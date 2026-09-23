import asyncio
from httpx import AsyncClient
from backend.app.main import app
from backend.app.core.firebase import set_mock_firebase_token

async def run():
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = "mock-token-random@gmail.com"
        set_mock_firebase_token(token, {"uid": "rnd_uid", "email": "random@gmail.com", "email_verified": True})
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post("/api/v1/auth/sync-user", headers=headers, json={"full_name": "Random Parent"})
        print(resp.json())

if __name__ == "__main__":
    import sys
    sys.path.append('backend')
    asyncio.run(run())
