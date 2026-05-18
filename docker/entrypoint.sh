#!/bin/bash
set -e

PORT="${1:-8000}"

echo "Starting AgStack PND server on port ${PORT}..."
exec uvicorn agstack_pnd.server.app:create_app --factory --host 0.0.0.0 --port "${PORT}"
