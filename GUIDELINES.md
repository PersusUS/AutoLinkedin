# GUIDELINES.md
# LinkedIn Post Automator — Referencia técnica completa

> Este archivo es la fuente de verdad técnica del proyecto.
> Contiene el stack, documentación de cada API con ejemplos reales, decisiones de arquitectura y reglas de código.
> Consúltalo antes de implementar cualquier llamada externa.

---

## QUÉ HACE ESTE PROYECTO

Webapp personal para automatizar posts de LinkedIn a partir de entrevistas de voz.
El usuario habla con una IA entrevistadora, que extrae contenido relevante.
Gemini 2.5 Pro genera N posts trilingües (ES/EN/ZH) que el usuario revisa y publica.

**Usuarios**: solo el propietario (uso personal, sin multi-tenant, sin auth de usuarios)
**Entorno**: solo local (`localhost`)

---

## STACK

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Backend | Python + FastAPI | Python 3.11+, FastAPI 0.115 |
| Servidor ASGI | Uvicorn | 0.30 |
| WebSocket backend | websockets | 11.0.3 |
| IA entrevista | Gemini Live API | `gemini-2.5-flash-native-audio-preview-12-2025` |
| IA posts | Gemini 2.5 Pro | `gemini-2.5-pro` |
| Embeddings RAG | Gemini Embeddings | `text-embedding-004` |
| SDK IA | google-genai | 1.0.0 |
| Base de datos | Supabase (PostgreSQL + pgvector) | supabase-py 2.9.0 |
| HTTP cliente | httpx | 0.27 |
| Validación | Pydantic + pydantic-settings | 2.9 |
| Frontend | React + TypeScript + Vite | React 19, TS 5.x |
| Estilos | Tailwind CSS v4 | 4.x |
| Router frontend | react-router-dom | 7.x |
| HTTP frontend | axios | — |
| Testing | pytest + pytest-asyncio | — |

---

## DOCUMENTACIÓN: GEMINI LIVE API

**Documentación oficial**: https://ai.google.dev/gemini-api/docs/live
**Referencia WebSocket**: https://ai.google.dev/api/live
**Guía de capacidades**: https://ai.google.dev/gemini-api/docs/live-guide

### Modelo
```
gemini-2.5-flash-native-audio-preview-12-2025
```

### Arquitectura para este proyecto
El backend FastAPI actúa como proxy WebSocket entre el frontend y Gemini Live.
El frontend NO conecta directamente a Gemini (la API key queda en el backend).

```
Browser (React)
  ↕ WebSocket ws://localhost:8000/api/interview/session
FastAPI Backend
  ↕ google-genai SDK (aio.live.connect)
Gemini Live API
```

### Conexión con el SDK Python (`google-genai`)

```python
from google import genai
from google.genai import types

client = genai.Client(api_key="TU_API_KEY")

config = types.LiveConnectConfig(
    response_modalities=["AUDIO", "TEXT"],
    system_instruction="...",
    input_audio_transcription={},   # Transcripción de lo que dice el usuario
    output_audio_transcription={},  # Transcripción de lo que dice la IA
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
        )
    )
)

async with client.aio.live.connect(
    model="gemini-2.5-flash-native-audio-preview-12-2025",
    config=config
) as session:
    # Enviar audio del micrófono (PCM16, 16000 Hz, base64)
    await session.send_realtime_input(
        audio=types.Blob(
            data=base64_audio_chunk,
            mime_type="audio/pcm;rate=16000"
        )
    )

    # Recibir respuestas
    async for response in session.receive():
        if response.data:
            # Audio de respuesta: PCM16, 24000 Hz, base64
            yield {"type": "audio", "data": response.data}
        if response.text:
            yield {"type": "text", "data": response.text}
        if hasattr(response, 'server_content') and response.server_content:
            sc = response.server_content
            if hasattr(sc, 'input_transcription') and sc.input_transcription:
                # Lo que dijo el usuario (transcrito)
                yield {"type": "user_transcript", "data": sc.input_transcription.text}
            if hasattr(sc, 'output_transcription') and sc.output_transcription:
                # Lo que dijo la IA (transcrito)
                yield {"type": "ai_transcript", "data": sc.output_transcription.text}
            if sc.turn_complete:
                yield {"type": "turn_complete", "data": None}
```

### Formato de audio
- **Entrada** (micrófono): PCM16, 16000 Hz, mono, chunks de 1024 samples
- **Salida** (respuesta IA): PCM16, 24000 Hz, mono
- En base64 para transmisión por WebSocket

### Capacidades importantes
- VAD (Voice Activity Detection): automático, no requiere configuración
- Barge-in: el usuario puede interrumpir a la IA en cualquier momento
- Sesión máxima: 10 minutos
- El cliente debe esperar el mensaje de setup completado antes de enviar audio

### Protocolo WebSocket frontend → backend (formato JSON)
```json
// Enviar chunk de audio
{"type": "audio", "data": "<base64 PCM16 16kHz>"}

// Finalizar sesión
{"type": "end_session"}
```

### Protocolo WebSocket backend → frontend (formato JSON)
```json
// Audio de respuesta de la IA
{"type": "audio", "data": "<base64 PCM16 24kHz>"}

// Transcripción del usuario
{"type": "user_transcript", "data": "texto que dijo el usuario"}

// Transcripción de la IA
{"type": "ai_transcript", "data": "texto que dijo la IA"}

// Fin de turno de la IA
{"type": "turn_complete", "data": null}

// Sesión terminada
{"type": "session_ended", "transcript_id": "<uuid>", "transcript": "<texto completo>"}
```

---

## DOCUMENTACIÓN: GEMINI 2.5 PRO (Generación de Posts)

**Documentación oficial**: https://ai.google.dev/api
**Modelos disponibles**: https://ai.google.dev/gemini-api/docs/models

### Modelo
```
gemini-2.5-pro
```

### Llamada con SDK Python

```python
from google import genai

client = genai.Client(api_key="TU_API_KEY")

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[{"role": "user", "parts": [{"text": prompt}]}],
    config={
        "temperature": 0.7,
        "max_output_tokens": 16000,
        "response_mime_type": "application/json",
        "system_instruction": system_prompt
    }
)

# Acceder al texto de respuesta
json_text = response.text
import json
posts_data = json.loads(json_text)  # {"posts": [...]}
```

### Schema de respuesta esperado (JSON forzado)
```json
{
  "posts": [
    {
      "title": "título interno descriptivo del post",
      "topic": "tema central en una frase corta",
      "content_es": "contenido completo en español con hashtags",
      "content_en": "full content in English with hashtags",
      "content_zh": "包含标签的完整中文内容"
    }
  ]
}
```

El número de objetos en `posts` varía entre 1 y ~6 según la riqueza del transcript.

---

## DOCUMENTACIÓN: GEMINI EMBEDDINGS (RAG)

**Documentación**: https://ai.google.dev/gemini-api/docs/embeddings

### Modelo
```
text-embedding-004
```
Dimensión de salida: **768** (importante: el schema de Supabase usa `VECTOR(768)`)

### Llamada con SDK Python
```python
from google import genai

client = genai.Client(api_key="TU_API_KEY")

response = client.models.embed_content(
    model="text-embedding-004",
    content={"parts": [{"text": "texto a vectorizar"}]}
)

embedding = response.embedding.values  # list[float], 768 elementos
```

---

## DOCUMENTACIÓN: SUPABASE + PGVECTOR

**Documentación general**: https://supabase.com/docs/guides/ai
**pgvector en Supabase**: https://supabase.com/docs/guides/database/extensions/pgvector
**Vector columns**: https://supabase.com/docs/guides/ai/vector-columns

### Instalación del cliente Python
```bash
pip install supabase==2.9.0
```

### Inicialización
```python
from supabase import create_client, Client

supabase: Client = create_client(
    supabase_url="https://xxxxx.supabase.co",
    supabase_key="SERVICE_KEY"  # usar la service key en backend, nunca la anon key pública
)
```

### Guardar transcript con embedding
```python
data = {
    "raw_text": transcript_text,
    "duration_seconds": 320,
    "embedding": embedding_list,  # list[float] de 768 elementos — supabase-py lo convierte
    "metadata": {"date": "2025-03-06"}
}
result = supabase.table("transcripts").insert(data).execute()
transcript_id = result.data[0]["id"]
```

### Búsqueda vectorial (RPC)
```python
# La función match_transcripts está definida en SQL (ver INSTRUCTIONS.md M2)
result = supabase.rpc("match_transcripts", {
    "query_embedding": query_embedding,  # list[float] 768 elementos
    "match_threshold": 0.7,
    "match_count": 5
}).execute()

similar = result.data  # [{"id": "...", "raw_text": "...", "created_at": "...", "similarity": 0.85}, ...]
```

### Guardar posts
```python
posts_to_insert = [
    {
        "transcript_id": transcript_id,
        "post_title": post["title"],
        "topic": post["topic"],
        "content_es": post["content_es"],
        "content_en": post["content_en"],
        "content_zh": post["content_zh"],
        "status": "draft"
    }
    for post in posts_list
]
result = supabase.table("posts").insert(posts_to_insert).execute()
post_ids = [row["id"] for row in result.data]
```

### Actualizar post tras publicar
```python
supabase.table("posts").update({
    "linkedin_post_id_es": "urn:li:ugcPost:123456",
    "published_at_es": "2025-03-06T10:30:00Z"
}).eq("id", post_id).execute()
```

---

## DOCUMENTACIÓN: LINKEDIN API

**LinkedIn Developer Portal**: https://www.linkedin.com/developers/apps
**OAuth 2.0 docs**: https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow
**UGC Posts API**: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/ugc-post-api
**Posts API (nueva)**: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api

### Setup inicial (el usuario lo hace manualmente una vez)
1. Crear app en https://www.linkedin.com/developers/apps
2. Products → solicitar: "Share on LinkedIn" + "Sign In with LinkedIn using OpenID Connect"
3. Auth → Authorized redirect URLs → `http://localhost:8000/api/linkedin/callback`
4. Copiar Client ID y Client Secret al `.env`

### Flujo OAuth — Paso 1: Redirigir al usuario
```
GET https://www.linkedin.com/oauth/v2/authorization
  ?response_type=code
  &client_id={LINKEDIN_CLIENT_ID}
  &redirect_uri={LINKEDIN_REDIRECT_URI}
  &scope=openid%20email%20profile%20w_member_social
  &state={random_string_csrf}
```

Scopes necesarios:
- `openid` — identificación del usuario
- `email` — email del usuario
- `profile` — nombre del usuario
- `w_member_social` — crear posts en LinkedIn

### Flujo OAuth — Paso 2: Intercambiar código por token (desde el backend)
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code_recibido_del_callback,
            "redirect_uri": settings.linkedin_redirect_uri,
            "client_id": settings.linkedin_client_id,
            "client_secret": settings.linkedin_client_secret
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token_data = response.json()
    access_token = token_data["access_token"]
    # expires_in: 5184000 segundos (~60 días)
```

### Flujo OAuth — Paso 3: Obtener URN del usuario
```python
async with httpx.AsyncClient() as client:
    response = await client.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    user_info = response.json()
    user_urn = user_info["sub"]   # Ej: "AbC123xYz" — se usa como "urn:li:person:AbC123xYz"
    user_name = user_info["name"]
```

### Publicar un post (UGC Posts API)
```python
import httpx

post_body = {
    "author": f"urn:li:person:{user_urn}",
    "lifecycleState": "PUBLISHED",
    "specificContent": {
        "com.linkedin.ugc.ShareContent": {
            "shareCommentary": {
                "text": content  # máx 3000 caracteres
            },
            "shareMediaCategory": "NONE"
        }
    },
    "visibility": {
        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
    }
}

async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://api.linkedin.com/v2/ugcPosts",
        json=post_body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
    )

    if response.status_code == 201:
        linkedin_post_id = response.headers.get("x-restli-id")
        # linkedin_post_id tendrá la forma "urn:li:ugcPost:1234567890"
    elif response.status_code == 401:
        raise Exception("Token de LinkedIn expirado. Reconecta tu cuenta.")
    elif response.status_code == 422:
        raise Exception("Contenido inválido para LinkedIn. Verifica que no supere 3000 caracteres.")
    else:
        raise Exception(f"Error de LinkedIn API: {response.status_code} — {response.text}")
```

### Límites importantes
- Máximo **3000 caracteres** por post
- El token dura ~60 días (no hay refresh token en el flujo estándar)
- Rate limits: no documentados públicamente, no publicar más de ~20 posts/día

---

## ARQUITECTURA DE DATOS

### Flujo completo
```
Micrófono → PCM16 16kHz → WebSocket → FastAPI proxy → Gemini Live
                                            ↓ (audio PCM16 24kHz + transcripts)
                                       Frontend (reproduce audio, muestra transcript)
                                            ↓ (end_session)
                                       Acumula transcript completo
                                            ↓
                              save_transcript() → Supabase (raw_text + embedding)
                                            ↓
                              generate_posts(transcript_id, transcript_text)
                                  ├── get_similar_transcripts() → contexto RAG
                                  └── Gemini 2.5 Pro → N posts trilingües
                                            ↓
                              save_posts() → Supabase (N filas en tabla posts)
                                            ↓
                              Frontend: Review page (preview + edición)
                                            ↓ (usuario aprueba idioma X)
                              publish_post(post_id, lang) → LinkedIn API
                                            ↓
                              update_post_published() → Supabase
```

### Schema de base de datos

```sql
-- transcripts: una fila por entrevista
transcripts {
  id: UUID PK
  created_at: TIMESTAMPTZ
  raw_text: TEXT          -- transcript bruto completo
  duration_seconds: INT
  embedding: VECTOR(768)  -- para búsqueda RAG
  metadata: JSONB
}

-- posts: N filas por entrevista, cada una con los 3 idiomas
posts {
  id: UUID PK
  created_at: TIMESTAMPTZ
  transcript_id: UUID FK → transcripts.id
  post_title: TEXT        -- título interno, no se publica
  topic: TEXT             -- tema en una frase
  content_es: TEXT        -- post en español (principal)
  content_en: TEXT        -- post en inglés
  content_zh: TEXT        -- post en chino
  status: TEXT            -- 'draft' por defecto
  linkedin_post_id_es: TEXT (nullable)
  linkedin_post_id_en: TEXT (nullable)
  linkedin_post_id_zh: TEXT (nullable)
  published_at_es: TIMESTAMPTZ (nullable)
  published_at_en: TIMESTAMPTZ (nullable)
  published_at_zh: TIMESTAMPTZ (nullable)
  metadata: JSONB
}
```

---

## REGLAS DE CÓDIGO

### Python (Backend)
- Type hints en todas las funciones
- Pydantic models para todos los request/response bodies de FastAPI
- Toda función async que llame a APIs externas debe tener try/except con errores tipados
- Sin prints en producción — usar `import logging`
- Variables de entorno solo a través de `config.settings`, nunca `os.environ` directo

### TypeScript (Frontend)
- Sin `any` bajo ningún concepto
- Todos los tipos globales en `src/types/index.ts`
- Sin lógica de negocio en componentes — la lógica va en hooks o en `src/api/`
- Sin prop drilling de más de 2 niveles — usar Context o composición

### Estilo general
- Componentes React en PascalCase
- Archivos de lógica en camelCase
- Una responsabilidad por función/módulo
- Sin secrets en el código, solo en `.env`

### Audio (Frontend)
- Captura con `AudioWorklet` (no `ScriptProcessorNode`, que está deprecado)
- Formato de captura: PCM16, 16000 Hz, mono
- Formato de reproducción: PCM16, 24000 Hz, mono

---

## VARIABLES DE ENTORNO

```bash
# Google AI Studio: https://aistudio.google.com
GEMINI_API_KEY=

# Supabase Dashboard: https://supabase.com/dashboard
# Usar la SERVICE KEY (no la anon key) para el backend
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_KEY=

# LinkedIn Developer Portal: https://www.linkedin.com/developers/apps
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
LINKEDIN_REDIRECT_URI=http://localhost:8000/api/linkedin/callback
```

---

## DECISIONES DE ARQUITECTURA

| Decisión | Elección | Razón |
|----------|----------|-------|
| Backend | FastAPI | Async nativo, ideal para WebSocket proxy, type hints integrados |
| Proxy para Gemini Live | FastAPI WebSocket | La API key queda en el backend, no expuesta al browser |
| SDK IA | google-genai | SDK oficial de Google, soporta Live API con `aio.live.connect` |
| Base de datos | Supabase | pgvector incluido, cliente Python maduro, dashboard fácil de usar |
| Embeddings | text-embedding-004 | Consistencia con el resto del stack Gemini, 768 dims |
| Índice vectorial | HNSW | Mejor recall que IVFFlat para datasets pequeños/medianos |
| Token LinkedIn | Dict en memoria | Uso personal, sin necesidad de persistencia entre reinicios |
| Frontend | React + Vite | Ecosistema maduro, dev server rápido |
| HTTP cliente | httpx | Async nativo en Python, reemplaza requests para FastAPI |
| WebSocket lib | websockets 11.0.3 | Versión que Google ha probado con Gemini Live |

---

## COMANDOS DE DESARROLLO

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Pruebas backend
pytest tests/ -v
pytest tests/test_rag.py -v        # solo módulo RAG
pytest tests/test_post_generator.py -v

# Frontend
cd frontend
npm install
npm run dev       # http://localhost:5173
npm run build
npm run preview
```

---

## REFERENCIAS Y LINKS ÚTILES

- Gemini Live API overview: https://ai.google.dev/gemini-api/docs/live
- Gemini Live API reference (WebSocket): https://ai.google.dev/api/live
- Gemini Live capabilities guide: https://ai.google.dev/gemini-api/docs/live-guide
- Gemini models: https://ai.google.dev/gemini-api/docs/models
- Gemini embeddings: https://ai.google.dev/gemini-api/docs/embeddings
- google-genai Python SDK: https://pypi.org/project/google-genai/
- Demo FastAPI + Gemini Live (referencia): https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/multimodal-live-api
- Supabase pgvector: https://supabase.com/docs/guides/database/extensions/pgvector
- Supabase vector columns: https://supabase.com/docs/guides/ai/vector-columns
- supabase-py client: https://supabase.com/docs/reference/python/introduction
- LinkedIn OAuth: https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow
- LinkedIn UGC Posts API: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/ugc-post-api
- FastAPI WebSocket docs: https://fastapi.tiangolo.com/advanced/websockets/
- FastAPI docs: https://fastapi.tiangolo.com
