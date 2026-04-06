import json
import logging

from google import genai
from google.genai import types

from config import settings
from services import rag

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Eres un experto en personal branding y copywriting para LinkedIn.
Recibirás la transcripción bruta de una entrevista y debes:

1. Identificar todos los temas distintos que merezcan un post independiente
2. Generar UN post por tema, con los 3 idiomas integrados en el mismo objeto

El número de posts (N) depende de la riqueza del contenido.
Si la entrevista toca 1 tema, genera 1 post.
Si toca 4 temas distintos, genera 4 posts.

REGLAS PARA ESPAÑOL (idioma principal):
- Tono personal, directo, primera persona
- Máximo 3000 caracteres
- Estructura: gancho potente (1-2 líneas) + desarrollo + aprendizaje o CTA
- Párrafos de máximo 3 líneas para facilitar lectura en móvil
- 3-5 hashtags relevantes al final
- Incluye términos de búsqueda naturales (SEO)

REGLAS PARA INGLÉS:
- Adaptación cultural, NO traducción literal
- Mismo tono y estructura, hashtags en inglés
- Máximo 3000 caracteres

REGLAS PARA CHINO:
- Adaptación para audiencia profesional china en LinkedIn
- Terminología de negocio apropiada, tono profesional pero cercano
- Máximo 3000 caracteres

PROHIBIDO en todos los idiomas:
- Inventar datos, métricas o logros que no estén en la transcripción
- Clichés: "¡Estoy emocionado!", "Incredibly excited", "Thrilled to share"
- Lenguaje corporativo vacío
- Exagerar logros"""

USER_PROMPT_TEMPLATE = """\
CONTEXTO DE ENTREVISTAS ANTERIORES (para coherencia de voz y evitar repetición):
{rag_context}

TRANSCRIPCIÓN A ANALIZAR:
{transcript}

Responde ÚNICAMENTE con JSON válido siguiendo exactamente este schema:
{{"posts": [{{"title": "...", "topic": "...", "content_es": "...", "content_en": "...", "content_zh": "..."}}]}}

Cada campo content_* debe contener el post completo con hashtags incluidos al final.
No uses campos adicionales ni nombres diferentes a los especificados."""

RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "posts": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "title": types.Schema(type=types.Type.STRING),
                    "topic": types.Schema(type=types.Type.STRING),
                    "content_es": types.Schema(type=types.Type.STRING),
                    "content_en": types.Schema(type=types.Type.STRING),
                    "content_zh": types.Schema(type=types.Type.STRING),
                },
                required=["title", "topic", "content_es", "content_en", "content_zh"],
            ),
        ),
    },
    required=["posts"],
)


def _build_rag_context(transcript_text: str) -> str:
    """Fetch similar past transcripts and format as plain-text context."""
    try:
        similar = rag.get_similar_transcripts(transcript_text, limit=3)
    except Exception:
        logger.warning("RAG context retrieval failed, proceeding without context")
        return "(sin entrevistas anteriores)"

    if not similar:
        return "(sin entrevistas anteriores)"

    lines: list[str] = []
    for t in similar:
        date = t.get("created_at", "fecha desconocida")
        snippet = t.get("raw_text", "")[:300]
        lines.append(f"- [{date}] {snippet}")
    return "\n".join(lines)


async def generate_posts(transcript_id: str, transcript_text: str) -> list[dict]:
    """Generate N trilingual posts from a transcript using Gemini 2.5 Pro.

    Returns the list of post dicts (with 'id' from Supabase).
    """
    rag_context = _build_rag_context(transcript_text)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        rag_context=rag_context,
        transcript=transcript_text,
    )

    client = genai.Client(api_key=settings.gemini_api_key)

    response = await client.aio.models.generate_content(
        model=settings.post_generator_model,
        contents=user_prompt,
        config={
            "temperature": 0.7,
            "max_output_tokens": 16000,
            "response_mime_type": "application/json",
            "response_schema": RESPONSE_SCHEMA,
            "system_instruction": SYSTEM_PROMPT,
        },
    )

    if not response.text:
        return []

    data = json.loads(response.text)
    posts_list: list[dict] = data["posts"]

    logger.info(
        "Gemini generated %d posts for transcript %s",
        len(posts_list),
        transcript_id,
    )

    post_ids = rag.save_posts(transcript_id, posts_list)

    result: list[dict] = []
    for post, pid in zip(posts_list, post_ids):
        result.append({**post, "id": pid})

    return result
