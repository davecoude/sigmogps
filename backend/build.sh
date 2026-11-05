#!/usr/bin/env bash
# Build de Render. Instala desde el lockfile, aplica migraciones y siembra.
set -o errexit
set -o pipefail

echo "--- instalando dependencias desde el lockfile ---"
python -m pip install --upgrade pip
pip install -r requirements.lock.txt
pip install -e . --no-deps

echo "--- aplicando migraciones ---"
alembic upgrade head

echo "--- sembrando roles, permisos y Admin ---"
python seed.py

echo "--- build completo ---"
