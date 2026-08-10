FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p static/uploads \
    && chmod +x run.sh

ENV PORT=10000

# Healthcheck: /healthz di app.py. Tidak butuh curl — pakai urllib bawaan
# Python. start-period 120s memberi waktu muat model TF + YOLO saat boot.
# Render (paid plan) memakai healthCheckPath di render.yaml untuk hal yang sama.
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD ["python", "-c", "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','10000')+'/healthz',timeout=5)"]

CMD ["./run.sh"]
