from fastapi import APIRouter, HTTPException, Query

from models.schemas import GeneratePostsRequest, UpdatePostContentRequest
from services import rag
from services.post_generator import generate_posts

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("/generate")
async def generate(body: GeneratePostsRequest):
    posts = await generate_posts(body.transcript_id, body.transcript_text)
    return {"posts": posts}


@router.get("")
def list_posts(
    transcript_id: str | None = Query(None),
    status: str | None = Query(None),
):
    return rag.get_posts(transcript_id=transcript_id, status=status)


@router.get("/{post_id}")
def get_post(post_id: str):
    try:
        return rag.get_post(post_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Post not found")


@router.patch("/{post_id}")
def update_post(post_id: str, body: UpdatePostContentRequest):
    if body.lang not in ("es", "en", "zh"):
        raise HTTPException(status_code=400, detail="lang must be es, en, or zh")
    rag.update_post_content(post_id, body.lang, body.content)
    return {"ok": True}
