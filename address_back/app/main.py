from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.services.db import init_db
from app.services.redis_store import get_redis_status

app = FastAPI(title="Address Split API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    status = get_redis_status()
    if status["available"]:
        print(f"Redis connected: {status['host']}:{status['port']} DB {status['db']}")
    else:
        print(status["message"])
