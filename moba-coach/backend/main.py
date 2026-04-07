"""FastAPI entry point for moba-coach backend."""
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

try:
    from .champions import CHAMPIONS
    from .config import OLLAMA_BASE_URL, OLLAMA_MODEL
    from .draft import DraftError, DraftManager
except ImportError:
    from champions import CHAMPIONS
    from config import OLLAMA_BASE_URL, OLLAMA_MODEL
    from draft import DraftError, DraftManager

app = FastAPI(title="moba-coach", version="0.1.0")

# Single in-memory draft for now
_current_draft: Optional[DraftManager] = None


def _draft() -> DraftManager:
    if _current_draft is None:
        raise HTTPException(400, "No active draft. POST /draft/start first.")
    return _current_draft


class BanRequest(BaseModel):
    champion_id: str


class PickRequest(BaseModel):
    champion_id: str


class RolesRequest(BaseModel):
    assignments: Dict[str, str]


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


# ---------------------------------------------------------------------------
# Draft endpoints
# ---------------------------------------------------------------------------

@app.post("/draft/start")
def draft_start():
    global _current_draft
    _current_draft = DraftManager()
    return _current_draft.get_draft_state()


@app.get("/draft/state")
def draft_state():
    return _draft().get_draft_state()


@app.post("/draft/ban")
async def draft_ban(req: BanRequest):
    d = _draft()
    try:
        d.player_ban(req.champion_id)
        enemy = await d.enemy_ban()
    except DraftError as e:
        raise HTTPException(400, str(e))
    state = d.get_draft_state()
    state["enemy_action"] = {"type": "ban", "champion_id": enemy}
    return state


@app.post("/draft/pick")
async def draft_pick(req: PickRequest):
    d = _draft()
    try:
        d.player_pick(req.champion_id)
    except DraftError as e:
        raise HTTPException(400, str(e))

    enemy_action = None
    # Trigger enemy turn(s) automatically when it's their turn
    if d.step in (3, 5):
        try:
            picks = await d.enemy_pick()
            enemy_action = {"type": "pick", "champion_ids": picks}
        except DraftError as e:
            raise HTTPException(500, str(e))

    state = d.get_draft_state()
    if enemy_action:
        state["enemy_action"] = enemy_action
    return state


@app.post("/draft/roles")
def draft_roles(req: RolesRequest):
    d = _draft()
    try:
        d.assign_roles(req.assignments)
    except DraftError as e:
        raise HTTPException(400, str(e))
    state = d.get_draft_state()
    state["enemy_role_assignments"] = d.auto_assign_enemy_roles()
    return state
