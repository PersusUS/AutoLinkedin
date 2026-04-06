# AutoLinkedIn - Generador de Posts IA

Este proyecto permite realizar entrevistas por voz potenciadas por IA (Gemini Live) y convertirlas automaticamente en publicaciones para LinkedIn, incluyendo soporte multi-idioma. Esta divido en un modelo RAG desde el Backend (FastAPI + Supabase) y un cliente web interactivo en Frontend (React + Vite).

---

## IMPORTANTE: SEGURIDAD DE CREDENCIALES
**NUNCA**, bajo ninguna circunstancia, se deben subir al repositorio las credenciales o archivos `.env`. 

Asegurate de que el archivo `.gitignore` contenga la regla `.env` y `venv/` antes de hacer el `git push`. Si clonas el proyecto en otra maquina, deberas recrear tus variables creando un archivo `.env` manualmente dentro de la carpeta `backend/`. 

Variables requeridas en el archivo `backend/.env`:
```env
GEMINI_API_KEY="tu_api_key_de_gemini"
SUPABASE_URL="tu_url_de_supabase"
SUPABASE_SERVICE_KEY="tu_key_admin_de_supabase"
LINKEDIN_CLIENT_ID="tu_client_id"
LINKEDIN_CLIENT_SECRET="tu_client_secret"
# Opcional, si no lo pones por defecto usara este:
# LINKEDIN_REDIRECT_URI="http://localhost:8000/api/linkedin/callback"
```

---

## Como ejecutar el proyecto en modo local

Para usar la aplicación en tu computadora localmente, debes ejecutar dos servidores al mismo tiempo en terminales distintas:

### 1. Iniciar el Backend (Terminal 1)
```bash
cd backend

# Opcional pero recomendado: Crear e Iniciar tu entorno virtual de Python
python -m venv venv
# Si usas Windows:
.\venv\Scripts\activate
# Si usas Mac/Linux:
# source venv/bin/activate

# Instala las librerías necesarias
pip install -r requirements.txt

# Iniciar el servidor local (levantará en el puerto 8000)
uvicorn main:app --reload --port 8000
```

### 2. Iniciar el Frontend (Terminal 2)
```bash
cd frontend

# Instala las dependencias web
npm install

# Inicias el servidor local
npm run dev
```

Una vez que ambos comandos estén corriendo, podrás acceder a la aplicación desde tu navegador ingresando a la URL: `http://localhost:5173`.