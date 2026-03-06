import secrets
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from config import settings
from models.schemas import LinkedInStatus, PublishRequest
from services import rag
from services.linkedin_publisher import (
    exchange_code_for_token,
    get_user_info,
    publish_post,
)

router = APIRouter(prefix="/linkedin", tags=["linkedin"])

linkedin_session: dict = {"access_token": None, "user_urn": None, "name": None}
_oauth_state: str = ""


@router.get("/auth")
def auth():
    """Redirect to LinkedIn OAuth authorization page."""
    global _oauth_state
    _oauth_state = secrets.token_urlsafe(32)
    params = urlencode({
        "response_type": "code",
        "client_id": settings.linkedin_client_id,
        "redirect_uri": settings.linkedin_redirect_uri,
        "scope": "openid email profile w_member_social",
        "state": _oauth_state,
    })
    return RedirectResponse(f"https://www.linkedin.com/oauth/v2/authorization?{params}")


@router.get("/callback")
async def callback(code: str, state: str):
    """OAuth callback — exchange code for token, get user info, redirect to frontend."""
    if state != _oauth_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    token_data = await exchange_code_for_token(
        code=code,
        redirect_uri=settings.linkedin_redirect_uri,
        client_id=settings.linkedin_client_id,
        client_secret=settings.linkedin_client_secret,
    )
    user_info = await get_user_info(token_data["access_token"])

    linkedin_session["access_token"] = token_data["access_token"]
    linkedin_session["user_urn"] = user_info["sub"]
    linkedin_session["name"] = user_info["name"]

    return RedirectResponse("http://localhost:5173?linkedin_connected=true")


@router.get("/status", response_model=LinkedInStatus)
def status():
    """Check if LinkedIn is connected."""
    return LinkedInStatus(
        connected=linkedin_session["access_token"] is not None,
        name=linkedin_session["name"],
    )


@router.post("/publish")
async def publish(body: PublishRequest):
    """Publish a post to LinkedIn for a specific language."""
    if linkedin_session["access_token"] is None:
        raise HTTPException(status_code=401, detail="LinkedIn not connected. Go to /api/linkedin/auth first.")
    if body.lang not in ("es", "en", "zh"):
        raise HTTPException(status_code=400, detail="lang must be es, en, or zh")

    post = rag.get_post(body.post_id)
    content = post.get(f"content_{body.lang}", "")
    if not content:
        raise HTTPException(status_code=400, detail=f"No content for lang={body.lang}")

    linkedin_post_id = await publish_post(
        content=content,
        access_token=linkedin_session["access_token"],
        user_urn=linkedin_session["user_urn"],
    )

    rag.update_post_published(body.post_id, body.lang, linkedin_post_id)

    return {
        "ok": True,
        "linkedin_post_id": linkedin_post_id,
        "lang": body.lang,
    }
