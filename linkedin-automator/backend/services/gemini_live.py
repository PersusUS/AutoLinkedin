import base64
import logging
from collections.abc import AsyncIterator

from google import genai
from google.genai import types

from config import settings

logger = logging.getLogger(__name__)

INTERVIEWER_SYSTEM_INSTRUCTION = (
    "Eres un entrevistador experto en personal branding y LinkedIn.\n"
    "Tu objetivo es hacer preguntas abiertas que extraigan historias concretas,\n"
    "logros medibles, perspectivas únicas y momentos de cambio.\n"
    "Haz UNA pregunta a la vez. Profundiza en las respuestas con \"¿Por qué?\",\n"
    "\"¿Qué pasó después?\", \"¿Cómo lo resolviste?\".\n"
    "Evita preguntas genéricas. Cuando hayas recibido 3+ respuestas sustanciales,\n"
    "puedes sugerir al usuario que puede terminar si lo desea.\n"
    "Idioma: español."
)

MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"


class GeminiLiveSession:
    """Proxy class wrapping a Gemini Live audio session."""

    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._session: genai.live.AsyncSession | None = None
        self._transcript_parts: list[str] = []

    async def connect(self) -> None:
        """Open the Gemini Live session."""
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO", "TEXT"],
            system_instruction=INTERVIEWER_SYSTEM_INSTRUCTION,
            input_audio_transcription={},
            output_audio_transcription={},
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Aoede"
                    )
                )
            ),
        )
        self._session = await self._client.aio.live.connect(
            model=MODEL,
            config=config,
        )
        logger.info("Gemini Live session connected")

    async def send_audio(self, audio_b64: str) -> None:
        """Send a base64-encoded PCM16 16kHz audio chunk to Gemini."""
        if self._session is None:
            return
        raw_bytes = base64.b64decode(audio_b64)
        await self._session.send_realtime_input(
            audio=types.Blob(
                data=raw_bytes,
                mime_type="audio/pcm;rate=16000",
            )
        )

    async def receive(self) -> AsyncIterator[dict]:
        """Async generator that yields message dicts from Gemini.

        Yields dicts with:
          {"type": "audio", "data": "<base64 PCM16 24kHz>"}
          {"type": "user_transcript", "data": "..."}
          {"type": "ai_transcript", "data": "..."}
          {"type": "turn_complete", "data": None}
        """
        if self._session is None:
            return

        async for message in self._session.receive():
            sc = message.server_content
            if sc is None:
                continue

            # Input transcription (what the user said)
            if sc.input_transcription and sc.input_transcription.text:
                text = sc.input_transcription.text
                self._transcript_parts.append(f"Usuario: {text}")
                yield {"type": "user_transcript", "data": text}

            # Output transcription (what the AI said)
            if sc.output_transcription and sc.output_transcription.text:
                text = sc.output_transcription.text
                self._transcript_parts.append(f"Entrevistador: {text}")
                yield {"type": "ai_transcript", "data": text}

            # Audio and text from model turn
            if sc.model_turn and sc.model_turn.parts:
                for part in sc.model_turn.parts:
                    if part.inline_data and part.inline_data.data:
                        audio_b64 = base64.b64encode(
                            part.inline_data.data
                        ).decode("ascii")
                        yield {"type": "audio", "data": audio_b64}

            # Turn complete
            if sc.turn_complete:
                yield {"type": "turn_complete", "data": None}

    def get_full_transcript(self) -> str:
        """Return the accumulated transcript."""
        return "\n".join(self._transcript_parts)

    async def disconnect(self) -> None:
        """Close the Gemini Live session."""
        if self._session is not None:
            await self._session.close()
            self._session = None
            logger.info("Gemini Live session disconnected")
