import asyncio
import json
import sys

import httpx
import websockets

API = "http://localhost:8000"   # on the server: "https://<DOMAIN>"
WS = "ws://localhost:8000"      # on the server: "wss://<DOMAIN>"


async def main(email: str, password: str, text: str):
    # 1 and 2: normal HTTP requests
    async with httpx.AsyncClient() as http:
        login = await http.post(f"{API}/auth/login", data={"username": email, "password": password})
        login.raise_for_status()
        token = login.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}
        conv = await http.post(f"{API}/conversations", json={"title": "ws test"}, headers=headers)
        conv.raise_for_status()
        conversation_id = conv.json()["id"]

    # 3: open the WebSocket for this conversation
    async with websockets.connect(f"{WS}/ws/conversations/{conversation_id}") as ws:
        # 4: log in on the WebSocket
        await ws.send(json.dumps({"type": "auth", "token": token}))
        print(await ws.recv())                       # expect {"type": "ready"}

        # 5: send the chat message
        await ws.send(json.dumps({"type": "message", "text": text}))

        # 6: read events until the task is done
        async for raw in ws:
            event = json.loads(raw)
            if event["type"] == "token":
                print(event["text"], end="", flush=True)
            elif event["type"] == "approval_required":
                print(f"\n[approval_required] {event['calls']}")
                answer = (await asyncio.to_thread(input, "Approve? (y/n) ")).strip().lower()
                await ws.send(json.dumps({
                    "type": "approval",
                    "approval_id": event["approval_id"],
                    "approved": answer == "y",
                }))
            else:
                print(f"\n[{event['type']}] {event}")
            if event["type"] == "done" and event.get("state") != "waiting_approval":
                break


asyncio.run(main(*sys.argv[1:4]))