#!/usr/bin/env bash
# Levanta el servicio con gunicorn para simular un entorno WSGI local.
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")" && pwd)
exec "$ROOT_DIR/venv/bin/gunicorn" -w 4 -b 0.0.0.0:8000 app:app
