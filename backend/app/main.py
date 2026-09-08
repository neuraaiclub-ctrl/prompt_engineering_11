from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.api import auth, users, teams, hackathons, audit, cases, challenges, executions, submissions, judging, leaderboard, arena

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    lifespan=lifespan
)

# CORS Middleware Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API V1 Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(teams.router, prefix=settings.API_V1_STR)
app.include_router(hackathons.hackathon_router, prefix=settings.API_V1_STR)
app.include_router(hackathons.round_router, prefix=settings.API_V1_STR)
app.include_router(cases.router, prefix=settings.API_V1_STR)
app.include_router(challenges.router, prefix=settings.API_V1_STR)
app.include_router(executions.router, prefix=settings.API_V1_STR)
app.include_router(submissions.router, prefix=settings.API_V1_STR)
app.include_router(judging.router, prefix=settings.API_V1_STR)
app.include_router(leaderboard.router, prefix=settings.API_V1_STR)
app.include_router(audit.router, prefix=settings.API_V1_STR)
app.include_router(arena.router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "status": "online",
        "system": settings.PROJECT_NAME,
        "docs": f"{settings.API_V1_STR}/docs"
    }
