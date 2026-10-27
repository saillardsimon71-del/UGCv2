"""Point d'entrée : API + UI statique (si buildée) dans un seul process."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import jobs
from .api import router
from .config import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    jobs.start()
    yield


app = FastAPI(title="Studio UGC v2", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.get("/api/health")
def health():
    return {"ok": True, "studio": "UGCv2"}


_static = get_settings().static_dir
if _static.is_dir():
    app.mount("/", StaticFiles(directory=str(_static), html=True), name="ui")


if __name__ == "__main__":
    import uvicorn
    s = get_settings()
    uvicorn.run("backend.app.main:app", host=s.host, port=s.port)
