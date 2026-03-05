# INSTRUCTIONS.md
# LinkedIn Post Automator — Plan de construcción para Copilot

> Lee este archivo completo antes de escribir una sola línea de código.
> Construye en el orden exacto indicado. No saltes pasos. No combines tareas.
> Cuando termines un módulo, ejecuta sus pruebas antes de continuar.

---

## QUÉ ESTAMOS CONSTRUYENDO

Una webapp personal para automatizar posts de LinkedIn a partir de entrevistas de voz.

**Flujo completo:**
1. El usuario inicia una sesión de entrevista de voz con **Gemini Live** (audio bidireccional en tiempo real)
2. La IA entrevistadora hace preguntas inteligentes para extraer contenido valioso
3. Al finalizar, el transcript bruto se guarda en **Supabase** con embeddings vectoriales (RAG)
4. **Gemini 2.5 Pro** analiza el transcript y decide cuántos posts generar (N variable, entre 1 y ~6, según la riqueza del contenido)
5. Cada post es un objeto único con los 3 idiomas integrados: español (principal), inglés y chino
6. El usuario ve un **preview** de cada post con sus 3 idiomas y aprueba/publica por idioma
7. Los posts aprobados se **publican en LinkedIn** vía API

**Stack:** FastAPI (Python) + React (TypeScript) + Supabase + Gemini API
**Entorno:** solo local, sin deployment

---

## ESTRUCTURA DE CARPETAS

Crea exactamente esta estructura antes de empezar a codear:

```
linkedin-automator/
├── backend/
│   ├── main.py                     # FastAPI app entry point
│   ├── config.py                   # Settings desde .env
│   ├── requirements.txt
│   ├── .env                        # Nunca al repo
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── interview.py            # WebSocket endpoint para Gemini Live
│   │   ├── posts.py                # CRUD de posts generados
│   │   └── linkedin.py             # OAuth y publicación LinkedIn
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gemini_live.py          # Proxy WebSocket hacia Gemini Live
│   │   ├── post_generator.py       # Generación de N posts con Gemini 2.5 Pro
│   │   ├── rag.py                  # Embeddings y búsqueda vectorial Supabase
│   │   └── linkedin_publisher.py   # Publicación en LinkedIn API
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py              # Pydantic models
│   └── tests/
│       ├── test_rag.py
│       ├── test_post_generator.py
│       └── test_linkedin.py
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── api/
        │   ├── interview.ts
        │   ├── posts.ts
        │   └── linkedin.ts
        ├── components/
        │   ├── ui/
        │   └── layout/
        │       ├── Sidebar.tsx
        │       └── Layout.tsx
        ├── hooks/
        │   ├── useAudioStream.ts
        │   └── useInterview.ts
        ├── pages/
        │   ├── Interview.tsx
        │   ├── Review.tsx
        │   └── History.tsx
        └── types/
            └── index.ts
```

---

## MÓDULOS Y ORDEN

```
M1 — Setup base
M2 — Módulo RAG (Supabase + embeddings)
M3 — Módulo de entrevista (Gemini Live WebSocket proxy)
M4 — Módulo de generación de posts (Gemini 2.5 Pro)
M5 — Módulo LinkedIn (OAuth + publicación)
M6 — Frontend completo
M7 — Integración y prueba end-to-end
```

---

## M1 — SETUP BASE

### Paso 1.1 — Backend

Crea `backend/requirements.txt`:
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
websockets==11.0.3
google-genai==1.0.0
supabase==2.9.0
python-dotenv==1.0.1
httpx==0.27.0
pydantic==2.9.0
pydantic-settings==2.5.0
pytest==8.3.0
pytest-asyncio==0.24.0
```

Crea `backend/.env` con estas claves vacías:
```
GEMINI_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
LINKEDIN_REDIRECT_URI=http://localhost:8000/api/linkedin/callback
```

Crea `backend/config.py` usando `pydantic-settings` con `BaseSettings`, cargando todas las variables del `.env`. Exporta una instancia global `settings`.

Crea `backend/main.py`: FastAPI app con CORS habilitado para `http://localhost:5173`, que incluya los tres routers bajo el prefijo `/api`.

### Paso 1.2 — Frontend

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install
npm install axios react-router-dom
npm install -D tailwindcss @tailwindcss/vite
```

Configura Tailwind en `vite.config.ts` y añade `@import "tailwindcss"` en el CSS global.

### Paso 1.3 — `.gitignore` en la raíz:
```
backend/.env
backend/__pycache__/
backend/.pytest_cache/
frontend/node_modules/
frontend/dist/
*.pyc
```

### ✅ PRUEBA M1
- [ ] `cd backend && uvicorn main:app --reload` → sin errores en `http://localhost:8000`
- [ ] `cd frontend && npm run dev` → sin errores en `http://localhost:5173`
- [ ] `http://localhost:8000/docs` muestra Swagger UI
- [ ] `.env` aparece en `.gitignore`

**No avances hasta que las 4 pasen.**

---

## M2 — MÓDULO RAG

### Paso 2.1 — Schema SQL en Supabase

Ejecuta en el SQL Editor del Dashboard de Supabase (https://supabase.com/dashboard):

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    raw_text TEXT NOT NULL,
    duration_seconds INTEGER,
    embedding VECTOR(768),
    metadata JSONB DEFAULT '{}'
);

-- Cada fila es UN post con sus 3 idiomas integrados
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    transcript_id UUID REFERENCES transcripts(id) ON DELETE CASCADE,
    post_title TEXT,
    topic TEXT,
    content_es TEXT NOT NULL,
    content_en TEXT NOT NULL,
    content_zh TEXT NOT NULL,
    status TEXT DEFAULT 'draft',
    linkedin_post_id_es TEXT,
    linkedin_post_id_en TEXT,
    linkedin_post_id_zh TEXT,
    published_at_es TIMESTAMPTZ,
    published_at_en TIMESTAMPTZ,
    published_at_zh TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX ON transcripts USING hnsw (embedding vector_cosine_ops);

CREATE OR REPLACE FUNCTION match_transcripts(
    query_embedding VECTOR(768),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5
)
RETURNS TABLE (id UUID, raw_text TEXT, created_at TIMESTAMPTZ, similarity FLOAT)
LANGUAGE SQL STABLE AS $$
    SELECT id, raw_text, created_at,
           1 - (embedding <=> query_embedding) AS similarity
    FROM transcripts
    WHERE 1 - (embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
$$;
```

### Paso 2.2 — Servicio RAG (`backend/services/rag.py`)

Implementa con `google-genai` para embeddings y `supabase-py` para persistencia:

- `generate_embedding(text: str) -> list[float]` — modelo `text-embedding-004`, 768 dimensiones
- `save_transcript(raw_text: str, duration_seconds: int) -> str` — guarda y devuelve UUID
- `get_similar_transcripts(query: str, limit: int = 5) -> list[dict]` — llama al RPC `match_transcripts`
- `save_posts(transcript_id: str, posts: list[dict]) -> list[str]` — guarda N posts, devuelve lista de UUIDs
- `get_posts(transcript_id: str = None, status: str = None) -> list[dict]` — lista posts con filtros opcionales
- `get_post(post_id: str) -> dict` — un post por ID
- `update_post_content(post_id: str, lang: str, content: str)` — edición inline
- `update_post_published(post_id: str, lang: str, linkedin_post_id: str)` — tras publicar

### ✅ PRUEBA M2

Crea `backend/tests/test_rag.py`:
- `test_save_and_retrieve_transcript` — guarda y verifica UUID válido + embedding no nulo en Supabase
- `test_similarity_search` — guarda 2 transcripts distintos, busca uno, verifica resultados ordenados
- `test_save_and_list_posts` — guarda N posts y los recupera filtrando por transcript_id

```bash
cd backend && pytest tests/test_rag.py -v
```

Prueba manual: verificar en el Dashboard de Supabase que los registros existen con `embedding` no null.

```
git commit -m "feat: RAG module with Supabase pgvector and Gemini embeddings"
```

---

## M3 — MÓDULO DE ENTREVISTA (Gemini Live)

> El backend es proxy WebSocket entre el frontend y Gemini Live API.
> El frontend captura audio del micrófono → lo envía al backend como base64 → el backend lo reenvía a Gemini → Gemini responde con audio → el backend lo reenvía al frontend.

### Paso 3.1 — Servicio Gemini Live (`backend/services/gemini_live.py`)

Implementa `GeminiLiveSession` usando `client.aio.live.connect()` del SDK `google-genai`.

Modelo a usar: `gemini-2.5-flash-native-audio-preview-12-2025`

Config de la sesión:
- `response_modalities`: `["AUDIO", "TEXT"]`
- `input_audio_transcription`: `{}` (para obtener transcript del usuario)
- `output_audio_transcription`: `{}` (para obtener transcript de la IA)
- `speech_config`: voz `Aoede`
- `system_instruction`: el prompt del entrevistador (ver más abajo)

Prompt del entrevistador (system_instruction):
```
Eres un entrevistador experto en personal branding y LinkedIn.
Tu objetivo es hacer preguntas abiertas que extraigan historias concretas,
logros medibles, perspectivas únicas y momentos de cambio.
Haz UNA pregunta a la vez. Profundiza en las respuestas con "¿Por qué?",
"¿Qué pasó después?", "¿Cómo lo resolviste?".
Evita preguntas genéricas. Cuando hayas recibido 3+ respuestas sustanciales,
puedes sugerir al usuario que puede terminar si lo desea.
Idioma: español.
```

Métodos de la clase:
- `async connect()` — abre la sesión
- `async send_audio(audio_b64: str)` — envía chunk de micrófono (PCM16 16kHz base64)
- `async receive()` — generador async que hace yield de dicts `{"type": "audio"|"user_transcript"|"ai_transcript"|"turn_complete", "data": str}`
- `get_full_transcript() -> str` — devuelve el transcript acumulado
- `async disconnect()` — cierra la sesión

### Paso 3.2 — Router WebSocket (`backend/routers/interview.py`)

Endpoint: `WebSocket /api/interview/session`

Lógica:
1. Al conectar: crea `GeminiLiveSession` y llama `connect()`
2. Dos tareas asyncio concurrentes:
   - **cliente→Gemini**: lee mensajes JSON del WebSocket. Si `type=="audio"`, llama `send_audio(data)`. Si `type=="end_session"`, cancela ambas tareas.
   - **Gemini→cliente**: itera `session.receive()`, reenvía cada mensaje al WebSocket como JSON
3. Al recibir `end_session`:
   - Llama `session.disconnect()`
   - Guarda transcript con `rag.save_transcript(transcript, duration)`
   - Envía `{"type": "session_ended", "transcript_id": "<uuid>", "transcript": "<texto>"}`
4. Maneja `WebSocketDisconnect` sin crash

### Paso 3.3 — Hook de audio (`frontend/src/hooks/useAudioStream.ts`)

Con Web Audio API nativa del navegador:
- `startRecording()`: `getUserMedia({audio: true})` → `AudioWorklet` para capturar PCM16 a 16000 Hz → convierte chunks a base64 → callback `onAudioChunk(base64: string)`
- `stopRecording()`: para la captura y cierra los tracks
- `playAudio(base64: string)`: decodifica base64 de PCM16 24000 Hz → reproduce con `AudioContext`
- Expone `{ isRecording, startRecording, stopRecording, playAudio }`

### Paso 3.4 — Hook de entrevista (`frontend/src/hooks/useInterview.ts`)

- Conecta WebSocket a `ws://localhost:8000/api/interview/session`
- Usa `useAudioStream` internamente
- Al recibir `{"type": "audio"}` del backend → llama `playAudio(data)`
- Al recibir `{"type": "user_transcript" | "ai_transcript"}` → actualiza `transcript` en estado
- Al recibir `{"type": "session_ended"}` → guarda `transcriptId` y cambia estado
- Expone: `{ start, end, transcript, isActive, status, transcriptId }`
- Tipos de status: `'idle' | 'connecting' | 'active' | 'ending' | 'done'`

### Paso 3.5 — Página Interview (`frontend/src/pages/Interview.tsx`)

- Botón "Iniciar entrevista" → llama `start()`
- Indicador de estado con colores: idle (gris) / conectando (amarillo) / activo (verde) / finalizando (azul)
- Círculo animado que pulsa mientras la IA habla (toggle al recibir `turn_complete`)
- Transcript con turnos diferenciados visualmente (usuario vs IA)
- Botón "Finalizar" con modal de confirmación → llama `end()` → al recibir `session_ended`, navega a `/review/:transcriptId`

### ✅ PRUEBA M3

Prueba manual completa (no hay prueba automatizable para audio real):
- [ ] Iniciar entrevista → navegador pide permiso de micrófono
- [ ] La IA saluda y hace la primera pregunta en español
- [ ] El usuario puede hablar y la IA responde con audio
- [ ] El transcript aparece en tiempo real diferenciando usuario e IA
- [ ] Finalizar → transcript en Supabase → redirección a `/review/:transcriptId`
- [ ] Sin errores en consola ni en el terminal del backend

```
git commit -m "feat: interview module with Gemini Live WebSocket proxy"
```

---

## M4 — MÓDULO DE GENERACIÓN DE POSTS

> Gemini 2.5 Pro analiza el transcript y genera N posts.
> N es variable: el modelo decide cuántos temas distintos hay en la entrevista.
> Cada post es UN objeto con los 3 idiomas — no son posts separados por idioma.

### Paso 4.1 — Servicio generador (`backend/services/post_generator.py`)

Implementa `async generate_posts(transcript_id: str, transcript_text: str) -> list[dict]`:

1. Llama a `rag.get_similar_transcripts(transcript_text, limit=3)` para contexto histórico
2. Formatea el contexto RAG como texto plano (fecha + primeros 300 chars de cada transcript similar)
3. Construye el prompt (ver abajo) y llama a Gemini 2.5 Pro con:
   - Modelo: `gemini-2.5-pro`
   - `response_mime_type`: `"application/json"`
   - `temperature`: 0.7
   - `max_output_tokens`: 16000
4. Parsea la respuesta JSON esperando el schema:
   ```json
   {
     "posts": [
       {
         "title": "título interno descriptivo",
         "topic": "tema central en una frase",
         "content_es": "post completo en español",
         "content_en": "full post in English",
         "content_zh": "完整的中文帖子"
       }
     ]
   }
   ```
5. Llama a `rag.save_posts(transcript_id, posts_list)` y devuelve los posts con sus UUIDs

Prompt del sistema para la generación:
```
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
- Exagerar logros

CONTEXTO DE ENTREVISTAS ANTERIORES (para coherencia de voz y evitar repetición):
{rag_context}

TRANSCRIPCIÓN A ANALIZAR:
{transcript}

Responde ÚNICAMENTE con el JSON válido, sin texto adicional ni markdown.
```

### Paso 4.2 — Router de posts (`backend/routers/posts.py`)

- `POST /api/posts/generate` — body: `{transcript_id: str, transcript_text: str}` → llama generador → devuelve lista de posts con UUIDs
- `GET /api/posts` — query params opcionales: `transcript_id`, `status` → lista posts
- `GET /api/posts/{post_id}` — un post por ID
- `PATCH /api/posts/{post_id}` — body: `{lang: "es"|"en"|"zh", content: str}` → actualiza contenido (edición inline)

### ✅ PRUEBA M4

Crea `backend/tests/test_post_generator.py`:
- `test_generates_at_least_one_post` — con transcript de ejemplo, verifica que se devuelve >= 1 post
- `test_each_post_has_three_languages` — todos los posts tienen `content_es`, `content_en`, `content_zh` no vacíos
- `test_no_content_exceeds_3000_chars` — ningún contenido supera 3000 caracteres
- `test_posts_saved_to_supabase` — los UUIDs devueltos existen en la tabla `posts`

```bash
cd backend && pytest tests/test_post_generator.py -v
```

Prueba manual:
- [ ] Llamar a `POST /api/posts/generate` con un transcript_id real de M2/M3
- [ ] Los posts aparecen en Supabase con `status: draft`
- [ ] Los 3 idiomas de cada post suenan naturales y no son traducciones literales
- [ ] Cada post tiene hashtags

```
git commit -m "feat: N-post generator with Gemini 2.5 Pro, trilingual per post"
```

---

## M5 — MÓDULO LINKEDIN

### Paso 5.1 — Setup manual (el usuario hace esto una sola vez)

El usuario debe:
1. Ir a https://www.linkedin.com/developers/apps → crear app
2. En Products → solicitar: "Share on LinkedIn" + "Sign In with LinkedIn using OpenID Connect"
3. En Auth → Authorized redirect URLs → añadir: `http://localhost:8000/api/linkedin/callback`
4. Copiar Client ID y Client Secret al `backend/.env`

### Paso 5.2 — Servicio publisher (`backend/services/linkedin_publisher.py`)

Implementa con `httpx`:

```python
LINKEDIN_PUBLISH_URL = "https://api.linkedin.com/v2/ugcPosts"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

async def exchange_code_for_token(code: str, redirect_uri: str, client_id: str, client_secret: str) -> dict:
    # POST a LINKEDIN_TOKEN_URL con grant_type=authorization_code
    # Devuelve {"access_token": str, "expires_in": int}

async def get_user_info(access_token: str) -> dict:
    # GET a LINKEDIN_USERINFO_URL
    # Devuelve {"sub": str, "name": str, "email": str}
    # El campo "sub" es el URN del usuario para publicar

async def publish_post(content: str, access_token: str, user_urn: str) -> str:
    # POST a LINKEDIN_PUBLISH_URL
    # Headers: Authorization Bearer, X-Restli-Protocol-Version: 2.0.0, Content-Type: application/json
    # Body: ver estructura en GUIDELINES.md
    # Devuelve el linkedin_post_id del header x-restli-id
    # Errores:
    #   401 → raise Exception("Token de LinkedIn expirado. Reconecta tu cuenta.")
    #   422 → raise Exception("Contenido inválido para LinkedIn. Verifica que no supere 3000 caracteres.")
    #   otros → raise Exception(f"Error de LinkedIn: {status_code}")
```

### Paso 5.3 — Router LinkedIn (`backend/routers/linkedin.py`)

Guarda el token y URN en un dict en memoria (uso personal, no necesita DB):
```python
linkedin_session = {"access_token": None, "user_urn": None, "name": None}
```

Endpoints:
- `GET /api/linkedin/auth` → redirige a la URL de autorización de LinkedIn con los scopes `openid email profile w_member_social`
- `GET /api/linkedin/callback` → intercambia code por token, obtiene URN, guarda en `linkedin_session`, redirige a `http://localhost:5173?linkedin_connected=true`
- `GET /api/linkedin/status` → devuelve `{"connected": bool, "name": str | null}`
- `POST /api/linkedin/publish` → body: `{"post_id": str, "lang": "es"|"en"|"zh"}` → obtiene post de Supabase, publica el contenido del idioma indicado, actualiza Supabase con el resultado

### ✅ PRUEBA M5

Crea `backend/tests/test_linkedin.py`:
- `test_publish_builds_correct_body` — mock de httpx, verifica que el body enviado a LinkedIn tiene la estructura correcta
- `test_publish_401_raises_clear_error` — simula 401, verifica mensaje de error legible
- `test_publish_422_raises_clear_error` — simula 422, verifica mensaje de error legible

Prueba manual:
- [ ] `http://localhost:8000/api/linkedin/auth` → redirige a LinkedIn → autorización → callback → redirige al frontend
- [ ] `GET /api/linkedin/status` → `{"connected": true, "name": "Tu Nombre"}`
- [ ] Publicar un post de prueba → aparece en LinkedIn
- [ ] El post en Supabase tiene `linkedin_post_id_es` y `published_at_es` no nulos

```
git commit -m "feat: LinkedIn OAuth and publishing module"
```

---

## M6 — FRONTEND COMPLETO

### Paso 6.1 — Tipos (`frontend/src/types/index.ts`)

```typescript
export interface Post {
  id: string;
  created_at: string;
  transcript_id: string;
  post_title: string;
  topic: string;
  content_es: string;
  content_en: string;
  content_zh: string;
  status: string;
  linkedin_post_id_es?: string;
  linkedin_post_id_en?: string;
  linkedin_post_id_zh?: string;
  published_at_es?: string;
  published_at_en?: string;
  published_at_zh?: string;
}

export type InterviewStatus = 'idle' | 'connecting' | 'active' | 'ending' | 'done';
export type Lang = 'es' | 'en' | 'zh';
```

### Paso 6.2 — Clientes API (`frontend/src/api/`)

- `posts.ts` — `generatePosts(transcriptId, transcriptText)`, `listPosts(transcriptId?)`, `getPost(id)`, `updatePostContent(id, lang, content)`
- `linkedin.ts` — `getStatus()`, `startOAuth()`, `publishPost(postId, lang)`

### Paso 6.3 — Layout

- `Sidebar.tsx` — navegación: Entrevista / Historial. Muestra badge "LinkedIn ✓" si está conectado.
- `Layout.tsx` — wrapper
- `App.tsx` — rutas: `/` → Interview, `/review/:transcriptId` → Review, `/history` → History

### Paso 6.4 — Página Interview (refactor final)

- Estado visual con colores claros
- Transcript dividido en burbujas: usuario (derecha) vs IA (izquierda)
- Botón "Finalizar" deshabilitado hasta tener al menos 1 turno completo

### Paso 6.5 — Página Review (`frontend/src/pages/Review.tsx`)

Esta es la página central. Debe implementar:

- Carga los posts para el `transcriptId` de la URL
- Polling cada 2s a `GET /api/posts?transcript_id=X` hasta que existan posts (con spinner "Gemini está generando tus posts...")
- Lista de tarjetas, una por post generado (N tarjetas)
- Cada tarjeta tiene:
  - Título/topic del post
  - Tabs: 🇪🇸 Español | 🇬🇧 English | 🇨🇳 中文
  - `textarea` editable con el contenido del tab activo
  - Auto-save al backend (debounce 1.5s, `PATCH /api/posts/{id}`)
  - Contador de caracteres con warning rojo si supera 3000
  - Botón "Publicar" por tab activo (llama a `POST /api/linkedin/publish` con el lang del tab)
  - Badge por idioma: "Borrador" / "Publicado ✓" con link al post de LinkedIn
- Modal de confirmación antes de publicar

### Paso 6.6 — Página History (`frontend/src/pages/History.tsx`)

- Lista todos los posts ordenados por `created_at` desc
- Columnas: fecha, topic, badges de idiomas publicados, link a LinkedIn
- Mini-preview del español (primeros 150 chars)

### ✅ PRUEBA M6

- [ ] La app carga sin errores
- [ ] Navegación entre páginas sin recargar
- [ ] El spinner de "generando" aparece y desaparece cuando cargan los posts
- [ ] La edición inline guarda (verificar en Supabase)
- [ ] El contador se pone rojo al superar 3000 chars
- [ ] El modal de confirmación aparece antes de publicar
- [ ] Los badges se actualizan tras publicar

```
git commit -m "feat: complete frontend Review, Interview, History pages"
```

---

## M7 — PRUEBA END-TO-END

### Checklist completo

**Preparación:**
- [ ] `cd backend && uvicorn main:app --reload` sin errores
- [ ] `cd frontend && npm run dev` sin errores
- [ ] LinkedIn conectado (`/api/linkedin/status` → `connected: true`)
- [ ] Supabase con tablas y función `match_transcripts` creadas

**Flujo principal:**
- [ ] Iniciar entrevista de 5+ minutos (5+ preguntas respondidas)
- [ ] La IA hace preguntas relevantes, profundiza, no repite
- [ ] Transcript en tiempo real diferencia usuario e IA
- [ ] Finalizar → redirige a Review
- [ ] Se generan N posts (más de 1 si la entrevista fue rica)
- [ ] Cada post tiene 3 idiomas distintos y naturales con hashtags
- [ ] Editar el español de un post → cambio guardado en Supabase
- [ ] Publicar el post en español → aparece en LinkedIn
- [ ] Badge del post cambia a "Publicado ✓" con link
- [ ] Historial muestra el post publicado
- [ ] Segunda entrevista: los posts generados NO repiten temas de la primera (RAG activo)

**Resiliencia:**
- [ ] Desconectar micrófono durante entrevista → error claro en UI, sin crash
- [ ] Intentar publicar contenido de más de 3000 chars → bloqueado en frontend y backend

```
git commit -m "test: full E2E validation complete"
git tag v1.0.0
```

---

## REGLAS ABSOLUTAS PARA COPILOT

1. Construye en el orden M1 → M2 → M3 → M4 → M5 → M6 → M7. Sin excepciones.
2. Una tarea a la vez por sesión. No combines módulos ni archivos.
3. Consulta `GUIDELINES.md` para cualquier detalle de API antes de implementar.
4. No instales dependencias fuera de las listadas en este documento.
5. Ejecuta las pruebas de cada módulo antes de empezar el siguiente.
6. Todo el Python usa type hints. Todo el TypeScript usa tipos explícitos, sin `any`.
7. Los secrets van en `.env`, nunca en el código.
8. Si algo no está en INSTRUCTIONS.md ni en GUIDELINES.md, pregunta antes de inventar.
