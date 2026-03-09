import signal
import sys
import os
import asyncio
from types import FrameType
import json
import uvicorn
import requests
from fastapi import (
    FastAPI,
    WebSocket,
    Request,
    Response,
)
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse, JSONResponse
from bot import run_bot
from utils.logging import logger
from utils.redis_client import RedisClient
from twilio.rest import Client
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv(override=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def hello() -> dict:
    try:
        return {"message": "Successfully running Cat."}
    except Exception as e:
        print("Failed to get / route.............")

@app.post("/agent")
async def agent(request: Request):
    try:
        print("hititng twiml...........................")
        call_id = request.query_params.get("call_id", "").strip()
        stream_param_block = ""
        if call_id:
            stream_param_block = f'<Parameter name="call_id" value="{call_id}" />'

        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
            <Response>
                <Connect>
                    <Stream url="wss://{request.headers.get("host")}/ws">
                        {stream_param_block}
                    </Stream>
                </Connect>
                <Say>The bot connection has been terminated.</Say>
            </Response>"""
        return HTMLResponse(content=twiml, media_type="application/xml")
    except Exception as e:
        print(f"failed to make call using agent {e}")


@app.post("/api/v1/call/webhook")
async def proxy_call_status_webhook(request: Request):
    """
    Relay Twilio status callbacks to voice-crm backend.
    This allows using a single public ngrok URL (agent) while backend runs locally.
    """
    backend_base = (os.getenv("BACKEND_URL") or "http://localhost:8000").rstrip("/")
    target_url = f"{backend_base}/api/v1/call/webhook"

    try:
        raw_body = await request.body()
        content_type = request.headers.get("content-type", "application/x-www-form-urlencoded")
        forwarded = requests.post(
            target_url,
            data=raw_body,
            headers={"content-type": content_type},
            timeout=10,
        )
        return Response(
            content=forwarded.text,
            status_code=forwarded.status_code,
            media_type=forwarded.headers.get("content-type", "application/json"),
        )
    except Exception as e:
        print(f"Failed to proxy Twilio webhook to backend: {e}")
        return JSONResponse(
            status_code=502,
            content={"detail": "Failed to proxy call webhook to backend"},
        )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        print("websocket connection initiated....................................")
        await websocket.accept()
        start_data = websocket.iter_text()
        await start_data.__anext__()
        call_data = json.loads(await start_data.__anext__())
        logger.info(call_data=call_data)
        call_data_start = call_data["start"]
        print("websocket_connection accepted------------------------------")
        twilio = Client(
            call_data_start["accountSid"],
            os.getenv("TWILIO_AUTH_TOKEN"),
        )
        call_sid = call_data_start["callSid"]
        twilio.calls(call_sid).recordings.create()
        print("started recording calls...........................")
 
        custom_params = call_data_start.get("customParameters") or {}
        call_id = str(custom_params.get("call_id") or "").strip()
        redis_lookup_key = call_id or call_sid

        # Fetch prompt and metadata from Redis.
        # Twilio media stream can arrive slightly before backend persistence completes.
        redis_data = RedisClient.get_call_prompt(redis_lookup_key)

        print("got some redis data-----------------", redis_data)

        if not redis_data:
            print(
                f"No prompt data found in Redis for call "
                f"call_id={call_id or 'n/a'}, call_sid={call_sid}"
            )
            await websocket.close(code=1011, reason="Call prompt not found in cache")
            return
        
        # Extract data from Redis
        agent_id = redis_data.get("agent_id")
        workspace_id = redis_data.get("workspace_id")
        prompt = redis_data.get("prompt")
        agent_name = redis_data.get("agent_name")
        lead_id = redis_data.get("lead_id")
        auth_header = redis_data.get("auth_header")
        
        if not agent_id or not prompt:
            print(f"Incomplete data in Redis for call {call_sid}")
            await websocket.close(code=1011, reason="Invalid call metadata")
            return
        
        print(f"Agent validated: {agent_name} (ID: {agent_id})")
        print(f"Using processed prompt: {prompt[:100]}...")

        call_metadata = {
            "agent_id": agent_id,
            "workspace_id": workspace_id,
            "lead_id": lead_id,
            "call_sid": call_sid,
            "call_id": call_id or None,
            "auth_header": auth_header,
        }

        await run_bot(
            websocket,
            call_data_start["streamSid"],
            call_sid,
            call_data_start["accountSid"],
            prompt=prompt,
            agent_name=agent_name,
            call_metadata=call_metadata,
        )
        
        # Cleanup Redis data
        RedisClient.delete_call_prompt(redis_lookup_key)
        print(f"Deleted Redis data for key {redis_lookup_key}")
        
        # Keep the connection open until websocket is closed by client
        try:
            while True:
                data = await websocket.receive_text()
                if not data:
                    break
        except Exception:
            # Client disconnected or connection error
            pass
            
        print("bot run successful.....................................")
    except Exception as e:
        print(f"Failed to make call to AI chatbot.................................... {e}")
        try:
            await websocket.close(code=1011, reason="Agent websocket failure")
        except Exception:
            pass


def shutdown_handler(signal_int: int, frame: FrameType) -> None:
    logger.info(f"Caught Signal {signal.strsignal(signal_int)}")
    from utils.logging import flush
    flush()
    # Safely exit program
    sys.exit(0)
if __name__ == "__main__":
    # Running application locally, outside of a Google Cloud Environment
    # handles Ctrl-C termination
    signal.signal(signal.SIGINT, shutdown_handler)
    uvicorn.run(app, host="0.0.0.0", port=8080)
else:
    # handles Cloud Run container termination
    signal.signal(signal.SIGTERM, shutdown_handler)
