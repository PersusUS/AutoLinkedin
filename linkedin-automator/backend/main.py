from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import interview, posts, linkedin

app = FastAPI(title="LinkedIn Post Automator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interview.router, prefix="/api")
app.include_router(posts.router, prefix="/api")
app.include_router(linkedin.router, prefix="/api")
