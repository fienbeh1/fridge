#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")" && pwd)

echo "Iniciando Refrigerador..."
echo "Conectando a MongoDB en localhost:27017"

exec "$ROOT_DIR/venv/bin/python" -c "
from app import app
app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False)
"
