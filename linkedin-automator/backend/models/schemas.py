from pydantic import BaseModel


class GeneratePostsRequest(BaseModel):
    transcript_id: str
    transcript_text: str


class UpdatePostContentRequest(BaseModel):
    lang: str
    content: str


class PublishRequest(BaseModel):
    post_id: str
    lang: str


class LinkedInStatus(BaseModel):
    connected: bool
    name: str | None = None
