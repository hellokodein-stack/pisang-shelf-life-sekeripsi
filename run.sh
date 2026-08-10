#!/usr/bin/env bash
# Production launcher untuk Render (Docker) — dijalankan oleh CMD di Dockerfile.
#
# - PORT di-set otomatis oleh Render; fallback ke 10000 (sama seperti app.py).
# - workers=1: model TensorFlow + YOLO dimuat sekali per proses (hemat memori
#   di plan kecil) dan MODEL_LOCK di app.py hanya melindungi satu proses.
# - threads=4: request bersamaan (healthcheck, file statis) tetap dilayani
#   tanpa memuat model ganda.
# - --timeout 300: prediksi CNN + segmentasi YOLO bisa berjalan lama.
# - --graceful-timeout sedikit di atas --timeout agar request yang sedang
#   berjalan selesai dulu saat Render me-restart/deploy (SIGTERM).
# - Log akses & error ke stdout/stderr supaya tertangkap log Render.
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-10000}"

exec gunicorn app:app \
    --bind "0.0.0.0:${PORT}" \
    --workers 1 \
    --threads 4 \
    --timeout 300 \
    --graceful-timeout 330 \
    --access-logfile - \
    --error-logfile - \
    --capture-output
