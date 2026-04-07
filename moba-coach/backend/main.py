"""FastAPI entry point for moba-coach backend."""
from typing import Dict, Optional

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

try:
    from .champions import CHAMPIONS
    from .coaching import CoachingInput, coaching_to_params, params_to_sim_params
    from .config import OLLAMA_BASE_URL, OLLAMA_MODEL
    from .draft import DraftError, DraftManager
    from .llm import OllamaClient
    from .simulation import simulate_match
except ImportError:
    from champions import CHAMPIONS
    from coaching import CoachingInput, coaching_to_params, params_to_sim_params
    from config import OLLAMA_BASE_URL, OLLAMA_MODEL
    from draft import DraftError, DraftManager
    from llm import OllamaClient
    from simulation import simulate_match

app = FastAPI(title="moba-coach", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if _FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIR)), name="static")


@app.get("/", include_in_schema=False)
def index():
    index_path = _FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    raise HTTPException(404, "frontend/index.html not found")


# Single in-memory draft for now
_current_draft: Optional[DraftManager] = None
_llm = OllamaClient()
_last_match: Optional[dict] = None


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


def _team_lists(d: DraftManager):
    blue = [{"champion_id": cid, "role": role}
            for cid, role in d.role_assignments.items()]
    enemy_roles = d.auto_assign_enemy_roles()
    red = [{"champion_id": cid, "role": role}
           for cid, role in enemy_roles.items()]
    return blue, red


def _result_to_dict(result) -> dict:
    out = result.model_dump()
    for key in ("blue_kills", "red_kills", "gold_diff_timeline",
                "towers_destroyed", "wyrm_secured_by", "key_events",
                "player_performances", "mvp"):
        if key in result.__dict__:
            out[key] = result.__dict__[key]
    return out


# ---------------------------------------------------------------------------
# Match endpoints
# ---------------------------------------------------------------------------

class MatchCoachingRequest(BaseModel):
    coaching: CoachingInput


class NarrateRequest(BaseModel):
    coaching: Optional[CoachingInput] = None


_pending_blue_params: Optional[dict] = None
_pending_red_params: Optional[dict] = None


@app.post("/match/coaching")
async def match_coaching(req: MatchCoachingRequest):
    global _pending_blue_params, _pending_red_params
    d = _draft()
    if not d.is_complete():
        raise HTTPException(400, "Draft not complete")
    blue, red = _team_lists(d)

    baseline = coaching_to_params(req.coaching)
    interpreted = await _llm.interpret_coaching(
        req.coaching.model_dump(), blue, red)
    llm_ok = "unavailable" not in interpreted.get("analysis", "").lower()
    if llm_ok:
        blue_params = {**baseline, **{k: v for k, v in interpreted.items()
                                      if k in baseline}}
    else:
        blue_params = baseline
    enemy = await _llm.enemy_strategy(red, blue, d.archetype)

    _pending_blue_params = blue_params
    _pending_red_params = enemy

    return {
        "blue_params": blue_params,
        "red_params": enemy,
        "llm_analysis": interpreted.get("analysis", ""),
        "baseline": baseline,
    }


@app.post("/match/simulate")
def match_simulate():
    global _last_match
    d = _draft()
    if not d.is_complete():
        raise HTTPException(400, "Draft not complete")
    if _pending_blue_params is None or _pending_red_params is None:
        raise HTTPException(400, "Submit /match/coaching first")
    blue, red = _team_lists(d)
    result = simulate_match(
        blue, red,
        params_to_sim_params(_pending_blue_params),
        params_to_sim_params(_pending_red_params),
    )
    _last_match = _result_to_dict(result)
    return _last_match


@app.post("/match/narrate")
async def match_narrate(req: NarrateRequest):
    if _last_match is None:
        raise HTTPException(400, "No match to narrate")
    d = _draft()
    blue, red = _team_lists(d)
    coaching = req.coaching.model_dump() if req.coaching else {}
    text = await _llm.narrate_match(_last_match, blue, red, coaching)
    return {"narration": text}


@app.post("/match/play")
async def match_play(req: MatchCoachingRequest):
    global _last_match, _pending_blue_params, _pending_red_params
    d = _draft()
    if not d.is_complete():
        raise HTTPException(400, "Draft not complete")
    blue, red = _team_lists(d)

    baseline = coaching_to_params(req.coaching)
    interpreted = await _llm.interpret_coaching(
        req.coaching.model_dump(), blue, red)
    llm_ok = "unavailable" not in interpreted.get("analysis", "").lower()
    if llm_ok:
        blue_params = {**baseline, **{k: v for k, v in interpreted.items()
                                      if k in baseline}}
    else:
        blue_params = baseline
    red_params = await _llm.enemy_strategy(red, blue, d.archetype)
    _pending_blue_params = blue_params
    _pending_red_params = red_params

    result = simulate_match(
        blue, red,
        params_to_sim_params(blue_params),
        params_to_sim_params(red_params),
    )
    result_dict = _result_to_dict(result)
    _last_match = result_dict

    narration = await _llm.narrate_match(
        result_dict, blue, red, req.coaching.model_dump())

    return {
        "sim_params": blue_params,
        "enemy_params": red_params,
        "match_result": result_dict,
        "narration": narration,
        "llm_analysis": interpreted.get("analysis", ""),
    }


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
