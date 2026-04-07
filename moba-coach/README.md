# moba-coach

A 3v3 MOBA draft coach + match simulator. You draft, write a game plan in
plain English, and a local LLM interprets it into simulation parameters. The
match runs through a deterministic engine and an LLM narrates the result.

## Prerequisites

- **Python 3.10+**
- **[Ollama](https://ollama.com)** running locally
- The `llama3.1:8b` model pulled:

  ```bash
  ollama pull llama3.1:8b
  ollama serve   # (usually auto-starts on install)
  ```

> The game still runs without Ollama — every LLM call has a deterministic
> fallback. The UI shows a warning banner when the LLM is unavailable.

## Setup

```bash
cd moba-coach
pip install -r requirements.txt
```

## Run

The simplest way:

```bash
./run.sh
```

This pings Ollama, starts the FastAPI server on `127.0.0.1:8000`, and opens
the browser. Equivalent manual commands:

```bash
python backend/main.py --host 127.0.0.1 --port 8000
# or
uvicorn backend.main:app --reload
```

### CLI flags

| Flag        | Effect                                                |
|-------------|-------------------------------------------------------|
| `--no-llm`  | Skip Ollama entirely; use deterministic fallback AI.  |
| `--log-llm` | Print every LLM prompt/response to stdout.            |
| `--reload`  | Hot-reload on code changes (dev).                     |

Equivalent env vars: `MOBACOACH_NO_LLM=1`, `MOBACOACH_LOG_LLM=1`,
`OLLAMA_BASE_URL`, `OLLAMA_MODEL`.

## Verify data files

```bash
python backend/champions.py
python backend/matchups.py
python backend/simulation.py
python backend/draft.py
```

## Architecture

```
┌──────────────────────┐
│  frontend/index.html │  vanilla HTML/CSS/JS, talks to FastAPI via fetch
└──────────┬───────────┘
           │ HTTP
┌──────────▼───────────┐
│  backend/main.py     │  FastAPI app, draft + match endpoints
└──┬────┬────┬─────┬───┘
   │    │    │     │
   │    │    │     └─► simulation.py   3-phase deterministic match engine
   │    │    └───────► coaching.py     CoachingInput model + baseline params
   │    └────────────► draft.py        DraftManager (bans, picks, roles)
   └─────────────────► llm.py          OllamaClient + every fallback
                       │
                       └─► champions.py / matchups.py   game data
```

### Request flow for one full match

1. `POST /draft/start` — creates `DraftManager`, picks a random enemy archetype.
2. `POST /draft/ban` → server runs player ban + calls LLM for enemy ban.
3. `POST /draft/pick` (×3) → after pick 1 the LLM picks 2 enemies; after pick 3 the LLM picks 1 more.
4. `POST /draft/roles` — player assigns roles, server auto-assigns enemy roles.
5. `POST /match/play` — single call that:
   - converts coaching input → baseline params (`coaching.py`)
   - asks the LLM to refine them (`llm.interpret_coaching`)
   - asks the LLM for an enemy strategy (`llm.enemy_strategy`)
   - runs `simulation.simulate_match`
   - asks the LLM to narrate the result (`llm.narrate_match`)
6. Frontend animates the SVG map and renders the scoreboard, KDA/CS table,
   gold chart, and narration.

## Endpoints

| Method | Path                | Notes                                          |
|--------|---------------------|------------------------------------------------|
| GET    | `/`                 | Serves the SPA.                                |
| GET    | `/health`           | Includes `llm_available`.                      |
| GET    | `/champions`        | Full champion data.                            |
| POST   | `/draft/start`      | New draft.                                     |
| GET    | `/draft/state`      | Current state.                                 |
| POST   | `/draft/ban`        | Player ban; auto-runs enemy ban.               |
| POST   | `/draft/pick`       | Player pick; auto-runs enemy picks when due.   |
| POST   | `/draft/roles`      | Lock in role assignments.                      |
| POST   | `/match/coaching`   | Interpret coaching only.                       |
| POST   | `/match/simulate`   | Run simulation with stored params.             |
| POST   | `/match/narrate`    | Narrate the last match.                        |
| POST   | `/match/play`       | One-shot: coach → simulate → narrate.          |

## Tests

```bash
python test_match.py             # full draft → match → narration
python backend/test_draft_api.py # draft endpoints round-trip
```
