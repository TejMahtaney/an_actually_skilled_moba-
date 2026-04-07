#!/usr/bin/env bash
# moba-coach launcher
set -e

cd "$(dirname "$0")"

# 1. Check Ollama
if curl -s -o /dev/null -w "%{http_code}" http://localhost:11434/api/tags | grep -q "200"; then
  echo "[run.sh] Ollama is running ✓"
else
  echo "[run.sh] WARNING: Ollama not reachable at http://localhost:11434"
  echo "[run.sh] The game will fall back to deterministic AI."
  echo "[run.sh] To fix: 'ollama serve' in another terminal, then 'ollama pull llama3.1:8b'"
fi

# 2. Open browser (best-effort)
URL="http://localhost:8000"
( sleep 1.5
  if command -v xdg-open >/dev/null; then xdg-open "$URL"
  elif command -v open >/dev/null; then open "$URL"
  elif command -v start >/dev/null; then start "$URL"
  fi ) &

# 3. Start the server
exec python backend/main.py --host 127.0.0.1 --port 8000 "$@"
