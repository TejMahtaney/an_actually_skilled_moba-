"""FastAPI entry point for moba-coach backend."""
from fastapi import FastAPI

try:
    from .champions import CHAMPIONS
    from .config import OLLAMA_BASE_URL, OLLAMA_MODEL
except ImportError:
    from champions import CHAMPIONS
    from config import OLLAMA_BASE_URL, OLLAMA_MODEL

app = FastAPI(title="moba-coach", version="0.1.0")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "champions": len(CHAMPIONS),
        "ollama_url": OLLAMA_BASE_URL,
        "model": OLLAMA_MODEL,
    }


@app.get("/champions")
def list_champions():
    return {cid: c.model_dump() for cid, c in CHAMPIONS.items()}
