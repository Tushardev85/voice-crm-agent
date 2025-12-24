import os
from pipecat.frames.frames import EndFrame, LLMMessagesFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketTransport,
    FastAPIWebsocketParams,
)
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
# import sys

from loguru import logger

from dotenv import load_dotenv

# from voicemail_utilis import switch_to_voicemail_response

load_dotenv(override=True)

logger.remove(0)
# only use it for debugging
# logger.add(sys.stderr, level="DEBUG")

async def run_bot(websocket_client, stream_sid, call_sid, account_sid):
    try:
        print("run_bot method called.........................................................");

        transport = FastAPIWebsocketTransport(
            websocket=websocket_client,
            params=FastAPIWebsocketParams(
                audio_out_enabled=True,
                add_wav_header=False,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
                vad_audio_passthrough=True,
                serializer=TwilioFrameSerializer(
                    stream_sid,
                    call_sid=call_sid,
                    account_sid=account_sid,
                    auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
                ),
            ),
        )

        llm = OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o-mini",
        )

        # Initialize STT service with optimized settings
        stt = DeepgramSTTService(
            api_key=os.getenv("DEEPGRAM_API_KEY"),
            model="nova-3",
            detect_language=True,
            language='multi'
        )

        # Initialize TTS service with optimized settings
        tts = ElevenLabsTTSService(
            api_key=os.getenv("ELEVENLABS_API_KEY"), 
            voice_id="9BWtsMINqrJLrRacOk9x",
        )

        # Initialize context based on LLM type
        messages = [{"role": "system", "content": "You are a helpful assistant."}]

        context = OpenAILLMContext(messages=messages)
        context_aggregator = llm.create_context_aggregator(context)

        tma_in = context_aggregator.user()
        tma_out = context_aggregator.assistant()

        pipeline = Pipeline(
            [
                transport.input(),  # Websocket input from client
                stt,  # Speech-To-Text
                tma_in,  # User responses
                llm,  # LLM
                tts,  # Text-To-Speech
                transport.output(),  # Websocket output to client
                tma_out,  # LLM responses
            ]
        )

        print("pipeline setup.....................")

        task = PipelineTask(
            pipeline, params=PipelineParams(allow_interruptions=True)
        )

        @transport.event_handler("on_client_connected")
        async def on_client_connected(transport, client):
            # Kick off the conversation.
            print("Kick off the conversation........................", client)
            try:
                messages.append({
                    "role": "system",
                    "content": "Please introduce yourself to the user.",
                })
                await task.queue_frames([LLMMessagesFrame(messages)])
            except Exception as e:
                print("failed to start conversation.........................", e);

        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):
            try:
                await task.queue_frames([EndFrame()])
            except Exception as e:
                print("Error in client disconnect handler.........................", e)

        runner = PipelineRunner(handle_sigint=False)
        await runner.run(task)
    except Exception as e:
        print("failed to run bot................................", e)
