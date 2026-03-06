import logging

import httpx

logger = logging.getLogger(__name__)

LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
LINKEDIN_PUBLISH_URL = "https://api.linkedin.com/v2/ugcPosts"


async def exchange_code_for_token(
    code: str, redirect_uri: str, client_id: str, client_secret: str
) -> dict:
    """Exchange OAuth authorization code for access token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            LINKEDIN_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        data = response.json()
        logger.info("LinkedIn token obtained, expires_in=%s", data.get("expires_in"))
        return {"access_token": data["access_token"], "expires_in": data["expires_in"]}


async def get_user_info(access_token: str) -> dict:
    """Get LinkedIn user info. Returns {sub, name, email}."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            LINKEDIN_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        info = response.json()
        return {
            "sub": info["sub"],
            "name": info.get("name", ""),
            "email": info.get("email", ""),
        }


async def publish_post(content: str, access_token: str, user_urn: str) -> str:
    """Publish a post to LinkedIn. Returns the linkedin_post_id."""
    post_body = {
        "author": f"urn:li:person:{user_urn}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            LINKEDIN_PUBLISH_URL,
            json=post_body,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
        )

    if response.status_code == 201:
        linkedin_post_id = response.headers.get("x-restli-id", "")
        logger.info("Published to LinkedIn: %s", linkedin_post_id)
        return linkedin_post_id

    if response.status_code == 401:
        raise Exception("Token de LinkedIn expirado. Reconecta tu cuenta.")
    if response.status_code == 422:
        raise Exception(
            "Contenido inválido para LinkedIn. Verifica que no supere 3000 caracteres."
        )
    raise Exception(f"Error de LinkedIn API: {response.status_code} — {response.text}")
