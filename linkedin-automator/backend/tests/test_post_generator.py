"""Tests for post_generator — M4.

Requires live Gemini API key and Supabase credentials in .env.
Run: pytest tests/test_post_generator.py -v
"""

import pytest
import pytest_asyncio

from services.post_generator import generate_posts
from services import rag

SAMPLE_TRANSCRIPT = (
    "Entrevistador: ¿Cuál ha sido tu mayor aprendizaje este año?\n"
    "Usuario: Este año aprendí que la consistencia supera al talento. "
    "Empecé a publicar en LinkedIn cada día durante 90 días. "
    "Al principio nadie interactuaba, pero al mes 2 empecé a recibir mensajes "
    "de reclutadores y founders. Conseguí 3 reuniones con inversores solo por "
    "un post donde conté cómo fracasé en mi primer startup.\n"
    "Entrevistador: ¿Qué pasó con esa primera startup?\n"
    "Usuario: La fundé en 2019 con dos amigos. Era una app de delivery para "
    "mascotas. Levantamos 50K de un ángel, pero no validamos el mercado. "
    "A los 8 meses nos quedamos sin dinero. Lo más duro fue decirle al equipo. "
    "Pero de ahí salió mi obsesión por validar antes de construir.\n"
    "Entrevistador: ¿Cómo aplicas eso hoy?\n"
    "Usuario: Ahora antes de escribir una línea de código hago 20 entrevistas "
    "con usuarios potenciales. En mi proyecto actual, un SaaS de automatización "
    "de reportes financieros, esas entrevistas me ahorraron 3 meses de desarrollo "
    "porque descubrí que el problema real era otro."
)


@pytest.fixture(scope="module")
def transcript_id():
    """Save a test transcript and return its ID."""
    tid = rag.save_transcript(SAMPLE_TRANSCRIPT, duration_seconds=180)
    return tid


@pytest_asyncio.fixture(scope="module")
async def generated_posts(transcript_id):
    """Generate posts once for the module."""
    return await generate_posts(transcript_id, SAMPLE_TRANSCRIPT)


class TestGeneratesAtLeastOnePost:
    def test_at_least_one(self, generated_posts):
        assert len(generated_posts) >= 1, "Should generate at least 1 post"


class TestEachPostHasThreeLanguages:
    def test_languages_present(self, generated_posts):
        for i, post in enumerate(generated_posts):
            assert post.get("content_es"), f"Post {i} missing content_es"
            assert post.get("content_en"), f"Post {i} missing content_en"
            assert post.get("content_zh"), f"Post {i} missing content_zh"


class TestNoContentExceeds3000Chars:
    def test_max_length(self, generated_posts):
        for i, post in enumerate(generated_posts):
            for lang in ("content_es", "content_en", "content_zh"):
                length = len(post.get(lang, ""))
                assert length <= 3000, (
                    f"Post {i} {lang} is {length} chars (max 3000)"
                )


class TestPostsSavedToSupabase:
    def test_exist_in_db(self, generated_posts):
        for post in generated_posts:
            pid = post["id"]
            db_post = rag.get_post(pid)
            assert db_post is not None, f"Post {pid} not found in Supabase"
            assert db_post["status"] == "draft"
