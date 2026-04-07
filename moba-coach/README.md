# moba-coach

A 3v3 MOBA draft coach powered by a local LLM (via Ollama).

## Structure

```
moba-coach/
├── backend/      FastAPI + game data
├── frontend/     (TBD)
└── requirements.txt
```

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn backend.main:app --reload
```

Health check: <http://localhost:8000/health>

## Verify data

```bash
python backend/champions.py
python backend/matchups.py
```

## Config

Environment variables:
- `OLLAMA_BASE_URL` (default `http://localhost:11434`)
- `OLLAMA_MODEL` (default `llama3.1:8b`)
