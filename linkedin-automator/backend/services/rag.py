import logging
from datetime import datetime, timezone

from google import genai
from google.genai import types
from supabase import create_client, Client

from config import settings

logger = logging.getLogger(__name__)

_gemini_client: genai.Client | None = None
_supabase_client: Client | None = None


def _get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=settings.gemini_api_key)
    return _gemini_client


def _get_supabase_client() -> Client:
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_service_key,
        )
    return _supabase_client


def generate_embedding(text: str) -> list[float]:
    """Generate a 768-dimension embedding using gemini-embedding-001."""
    client = _get_gemini_client()
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=768),
    )
    return response.embeddings[0].values


def save_transcript(raw_text: str, duration_seconds: int) -> str:
    """Save transcript with embedding to Supabase. Returns the UUID."""
    embedding = generate_embedding(raw_text)
    supabase = _get_supabase_client()
    data = {
        "raw_text": raw_text,
        "duration_seconds": duration_seconds,
        "embedding": embedding,
        "metadata": {"date": datetime.now(timezone.utc).isoformat()},
    }
    result = supabase.table("transcripts").insert(data).execute()
    transcript_id: str = result.data[0]["id"]
    logger.info("Saved transcript %s", transcript_id)
    return transcript_id


def get_similar_transcripts(query: str, limit: int = 5) -> list[dict]:
    """Search for similar transcripts using pgvector cosine similarity."""
    query_embedding = generate_embedding(query)
    supabase = _get_supabase_client()
    result = supabase.rpc("match_transcripts", {
        "query_embedding": query_embedding,
        "match_threshold": 0.7,
        "match_count": limit,
    }).execute()
    return result.data


def save_posts(transcript_id: str, posts: list[dict]) -> list[str]:
    """Save N posts to Supabase. Returns list of UUIDs."""
    supabase = _get_supabase_client()
    posts_to_insert = [
        {
            "transcript_id": transcript_id,
            "post_title": post["title"],
            "topic": post["topic"],
            "content_es": post["content_es"],
            "content_en": post["content_en"],
            "content_zh": post["content_zh"],
            "status": "draft",
        }
        for post in posts
    ]
    result = supabase.table("posts").insert(posts_to_insert).execute()
    post_ids: list[str] = [row["id"] for row in result.data]
    logger.info("Saved %d posts for transcript %s", len(post_ids), transcript_id)
    return post_ids


def get_posts(
    transcript_id: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """List posts with optional filters."""
    supabase = _get_supabase_client()
    query = supabase.table("posts").select("*").order("created_at", desc=True)
    if transcript_id is not None:
        query = query.eq("transcript_id", transcript_id)
    if status is not None:
        query = query.eq("status", status)
    result = query.execute()
    return result.data


def get_post(post_id: str) -> dict:
    """Get a single post by ID."""
    supabase = _get_supabase_client()
    result = supabase.table("posts").select("*").eq("id", post_id).single().execute()
    return result.data


def update_post_content(post_id: str, lang: str, content: str) -> None:
    """Update the content of a specific language for a post (inline editing)."""
    column = f"content_{lang}"
    supabase = _get_supabase_client()
    supabase.table("posts").update({column: content}).eq("id", post_id).execute()
    logger.info("Updated %s for post %s", column, post_id)


def update_post_published(post_id: str, lang: str, linkedin_post_id: str) -> None:
    """Mark a specific language of a post as published on LinkedIn."""
    supabase = _get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("posts").update({
        f"linkedin_post_id_{lang}": linkedin_post_id,
        f"published_at_{lang}": now,
    }).eq("id", post_id).execute()
    logger.info("Published %s for post %s → %s", lang, post_id, linkedin_post_id)
