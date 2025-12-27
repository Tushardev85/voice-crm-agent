import signal
import sys
import os
from types import FrameType
import json
import uvicorn
from fastapi import (
    FastAPI,
    WebSocket,
    Request,
    WebSocketException,
)
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse
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
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
            <Response>
                <Connect>
                    <Stream url="wss://{request.headers.get("host")}/ws"></Stream>
                </Connect>
                <Say>The bot connection has been terminated.</Say>
            </Response>"""
        return HTMLResponse(content=twiml, media_type="application/xml")
    except Exception as e:
        print(f"failed to make call using agent {e}")

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
 
        # Fetch prompt and metadata from Redis
        redis_data = RedisClient.get_call_prompt(call_sid)
        if not redis_data:
            print(f"No prompt data found in Redis for call {call_sid}")
            raise WebSocketException(status_code=404, detail="Call prompt not found in cache")
        
        # Extract data from Redis
        agent_id = redis_data.get("agent_id")
        prompt = redis_data.get("prompt")
        agent_name = redis_data.get("agent_name")
        
        if not agent_id or not prompt:
            print(f"Incomplete data in Redis for call {call_sid}")
            raise WebSocketException(status_code=400, detail="Invalid call metadata")
        
        print(f"Agent validated: {agent_name} (ID: {agent_id})")
        print(f"Using processed prompt: {prompt[:100]}...")

        # Pass prompt and metadata directly to run_bot
        await run_bot(
            websocket,
            call_data_start["streamSid"],
            call_sid,
            call_data_start["accountSid"],
            prompt=prompt,
            agent_name=agent_name,
        )
        
        # Cleanup Redis data
        RedisClient.delete_call_prompt(call_sid)
        print(f"Deleted Redis data for call {call_sid}")
        
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