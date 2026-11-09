"""
Web API for Spotify Sound Companion.

Wraps the existing services (Spotify, LRCLIB lyrics, Gemini) in a small REST
API for the React frontend, and serves the built frontend in production.
Each feature area lives in its own router under api/routes/.

Run with:  python -m api
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import ai, auth, library, lyrics, player, search
from core.config import BASE_DIR


FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

# Frontend dev server origins (Vite). Only local addresses are allowed.
DEV_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

app = FastAPI(title="Spotify Sound Companion API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=DEV_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

for module in (auth, player, library, search, lyrics, ai):
    app.include_router(module.router)
app.include_router(library.liked_router)


# ---------------------------------------------------------------------------
# Built frontend (production). In development, Vite serves it instead.
# ---------------------------------------------------------------------------

if (FRONTEND_DIST / "index.html").exists():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="assets",
    )

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")

        file = (FRONTEND_DIST / path).resolve()

        if (
            path
            and file.is_file()
            and FRONTEND_DIST.resolve() in file.parents
        ):
            return FileResponse(file)

        # Client-side routes (/library, ...) are handled by React Router
        return FileResponse(FRONTEND_DIST / "index.html")
