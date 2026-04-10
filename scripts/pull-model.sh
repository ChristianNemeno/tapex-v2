#!/usr/bin/env bash
# Pull the configured model into the Ollama container.
# Run once after `docker compose up -d`:
#   bash scripts/pull-model.sh
set -euo pipefail

MODEL="${MODEL_NAME:-gemma4:e4b}"
echo "Pulling model: $MODEL"
docker compose exec ollama ollama pull "$MODEL"
echo "Done. Model $MODEL is ready."
