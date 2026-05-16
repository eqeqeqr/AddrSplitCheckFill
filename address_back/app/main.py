from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes import router
from app.services.db import init_db
from app.services.redis_store import get_redis_status


def _get_static_dir() -> Path:
    import sys
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / "static"
    return Path(__file__).parent.parent / "static"


app = FastAPI(title="Address Split API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

static_dir = _get_static_dir()
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        file_path = static_dir / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(static_dir / "index.html"))


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    status = get_redis_status()
    if status["available"]:
        print(f"Redis connected: {status['host']}:{status['port']} DB {status['db']}")
    else:
        print(status["message"])
