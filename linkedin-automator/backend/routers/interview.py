import asyncio
import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.gemini_live import GeminiLiveSession
from services import rag

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interview", tags=["interview"])


@router.websocket("/session")
async def interview_session(ws: WebSocket) -> None:
    await ws.accept()
    session = GeminiLiveSession()

    try:
        await session.connect()
    except Exception as e:
        logger.error("Failed to connect Gemini Live: %s", e)
        await ws.send_json({"type": "error", "data": str(e)})
        await ws.close()
        return

    start_time = time.time()
    stop_event = asyncio.Event()

    async def client_to_gemini() -> None:
        """Read messages from the browser WebSocket and forward to Gemini."""
        try:
            while not stop_event.is_set():
                raw = await ws.receive_text()
                msg = json.loads(raw)
                if msg["type"] == "audio":
                    await session.send_audio(msg["data"])
                elif msg["type"] == "end_session":
                    stop_event.set()
        except WebSocketDisconnect:
            stop_event.set()

    async def gemini_to_client() -> None:
        """Read messages from Gemini and forward to the browser WebSocket."""
        try:
            async for msg in session.receive():
                if stop_event.is_set():
                    break
                await ws.send_json(msg)
        except Exception as e:
            if not stop_event.is_set():
                logger.error("Gemini receive error: %s", e)
                stop_event.set()

    task_c2g = asyncio.create_task(client_to_gemini())
    task_g2c = asyncio.create_task(gemini_to_client())

    # Wait until either task finishes or stop_event is set
    done, pending = await asyncio.wait(
        [task_c2g, task_g2c],
        return_when=asyncio.FIRST_COMPLETED,
    )
    stop_event.set()
    for t in pending:
        t.cancel()

    # Disconnect Gemini and save transcript
    await session.disconnect()
    transcript = session.get_full_transcript()
    duration = int(time.time() - start_time)

    try:
        if transcript.strip():
            transcript_id = rag.save_transcript(transcript, duration)
            await ws.send_json({
                "type": "session_ended",
                "transcript_id": transcript_id,
                "transcript": transcript,
            })
        else:
            await ws.send_json({
                "type": "session_ended",
                "transcript_id": None,
                "transcript": "",
            })
    except WebSocketDisconnect:
        logger.warning("Client disconnected before session_ended was sent")
    except Exception as e:
        logger.error("Error saving transcript: %s", e)
