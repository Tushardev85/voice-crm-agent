from datetime import datetime
import signal
import sys
import os
from types import FrameType
import json
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
import uvicorn
from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    Request,
    WebSocketException,
    Depends,
    Query
)
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse
from bot import run_bot
from utils.logging import logger
from twilio.rest import Client
from dotenv import load_dotenv
from sqlmodel import select, Session
from contextlib import asynccontextmanager
from db import Agent, Hubspot, get_session
from typing import Annotated, Any, Dict, List, Optional
from helper import analyze_transcription, dynamic_variable_update, get_transcription, strip_html_tags
import requests

load_dotenv(override=True)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # create_db_and_tables()
    yield
app = FastAPI(lifespan=lifespan)
SessionDep = Annotated[Session, Depends(get_session)]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variable to store call metadata
app.state.call_metadata = {}

@app.get("/")
async def hello(session: SessionDep) -> dict:
    try:
        return { "message": "Successfully running Cat." }
    except Exception as e:
        print("Failed to get / route.............")

@app.post("/agent")
async def agent(
    request: Request,
    session: SessionDep,
    ):
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
        print(f"failed to make call using agent {e}");
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, session: SessionDep):
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
 
        # Check if call metadata exists for this call
        if call_sid not in app.state.call_metadata:
            print("call metadata not found for this call, raising exception.....................................")
            raise WebSocketException(status_code=404, detail="Call metadata not found")

        await run_bot(
            websocket,
            call_data_start["streamSid"],
            call_sid,
            call_data_start["accountSid"],
        )
        
        # Memory cleanup - remove call metadata after call is complete
        if call_sid in app.state.call_metadata:
            del app.state.call_metadata[call_sid]
            print(f"Cleaned up metadata for call {call_sid}")
        
        # Keep the connection open until websocket is closed by client
        try:
            # Wait for any final data from the client before considering the connection complete
            while True:
                data = await websocket.receive_text()
                if not data:
                    break
        except Exception:
            # Client disconnected or connection error
            pass
            
        print("bot run successful.....................................");
    except Exception as e:
        print(f"Failed to make call to AI chatbot.................................... {e}")

class AnalyzeCallRequest(BaseModel):
    questions: Optional[List[Dict[str, Any]]] = None  
    agent_id: Optional[int] = None

@app.post("/analyze-call")
async def analyze_call(
    session: SessionDep,
    request: AnalyzeCallRequest,
    call_sid: str = Query(..., description="Twilio Call SID"),
    ):
    print("here in analyze function-----------------")
    try:
        print("started call analysis")
        transcript = await get_transcription(call_sid)
        if transcript:
            print("transcript found in GCP bucket----------------------")

        if isinstance(transcript, dict) and transcript.get("error"):
            logger.warning("Transcription not found.")
            raise HTTPException(status_code=404, detail="Transcription not found")
        questions = request.questions
        if not questions and request.agent_id:
            agent = session.exec(select(Agent).where(Agent.id == request.agent_id)).first()
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            questions = agent.post_call_questions or []  

        if not questions:
            raise HTTPException(status_code=400, detail="No questions provided")

        # Analyze transcription
        analysis = await analyze_transcription(transcript, questions)

        print("analysed call sending it in response----------------------------")

        return {"analysis": jsonable_encoder(analysis)}
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Analysis failed")


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