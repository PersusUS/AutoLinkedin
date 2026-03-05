import uuid

import pytest

from services.rag import (
    generate_embedding,
    get_posts,
    save_posts,
    save_transcript,
    get_similar_transcripts,
)


def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


class TestSaveAndRetrieveTranscript:
    def test_save_and_retrieve_transcript(self) -> None:
        """Save a transcript and verify UUID is valid + embedding was stored."""
        raw_text = (
            "Hoy hablamos sobre cómo construí mi primer producto SaaS. "
            "Empecé con una idea simple: automatizar reportes de marketing. "
            "En 3 meses tenía 50 clientes pagando."
        )
        transcript_id = save_transcript(raw_text, duration_seconds=300)

        assert transcript_id is not None
        assert _is_valid_uuid(transcript_id)

        # Verify embedding is not null by searching for the same text
        results = get_similar_transcripts(raw_text, limit=1)
        assert len(results) >= 1
        found = any(r["id"] == transcript_id for r in results)
        assert found, f"Transcript {transcript_id} not found in similarity search"


class TestSimilaritySearch:
    def test_similarity_search(self) -> None:
        """Save 2 distinct transcripts, search for one, verify results are ordered."""
        text_ai = (
            "La inteligencia artificial está transformando la industria del software. "
            "Los modelos de lenguaje permiten automatizar tareas complejas. "
            "GPT y Gemini son los más usados en producción."
        )
        text_cooking = (
            "Mi receta favorita de paella valenciana lleva azafrán, "
            "arroz bomba, judías verdes y garrofón. "
            "Se cocina a fuego fuerte durante 20 minutos."
        )

        id_ai = save_transcript(text_ai, duration_seconds=200)
        id_cooking = save_transcript(text_cooking, duration_seconds=180)

        # Search with an AI-related query — should rank the AI transcript higher
        query = "inteligencia artificial y modelos de lenguaje en software"
        results = get_similar_transcripts(query, limit=5)

        assert len(results) >= 1

        result_ids = [r["id"] for r in results]
        if id_ai in result_ids and id_cooking in result_ids:
            ai_idx = result_ids.index(id_ai)
            cooking_idx = result_ids.index(id_cooking)
            assert ai_idx < cooking_idx, "AI transcript should rank higher than cooking"

        # Verify results are sorted by similarity descending
        similarities = [r["similarity"] for r in results]
        assert similarities == sorted(similarities, reverse=True)


class TestSaveAndListPosts:
    def test_save_and_list_posts(self) -> None:
        """Save N posts and retrieve them filtering by transcript_id."""
        raw_text = (
            "Hablamos de liderazgo remoto y gestión de equipos distribuidos. "
            "También tocamos el tema de productividad personal con OKRs."
        )
        transcript_id = save_transcript(raw_text, duration_seconds=400)

        posts = [
            {
                "title": "Liderazgo remoto en 2026",
                "topic": "Liderazgo de equipos distribuidos",
                "content_es": "Liderar equipos remotos requiere confianza...",
                "content_en": "Leading remote teams requires trust...",
                "content_zh": "领导远程团队需要信任...",
            },
            {
                "title": "OKRs para productividad",
                "topic": "Productividad personal con OKRs",
                "content_es": "Los OKRs cambiaron mi forma de trabajar...",
                "content_en": "OKRs changed the way I work...",
                "content_zh": "OKR改变了我的工作方式...",
            },
        ]

        post_ids = save_posts(transcript_id, posts)

        assert len(post_ids) == 2
        assert all(_is_valid_uuid(pid) for pid in post_ids)

        # Retrieve by transcript_id
        retrieved = get_posts(transcript_id=transcript_id)
        assert len(retrieved) >= 2

        retrieved_ids = {p["id"] for p in retrieved}
        for pid in post_ids:
            assert pid in retrieved_ids

        # Verify all have draft status
        for p in retrieved:
            if p["id"] in post_ids:
                assert p["status"] == "draft"
                assert p["content_es"] != ""
                assert p["content_en"] != ""
                assert p["content_zh"] != ""
