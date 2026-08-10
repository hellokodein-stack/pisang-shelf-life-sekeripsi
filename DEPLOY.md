# Panduan Deploy — Sistem Analisis Daya Simpan Pisang

> **Rekomendasi untuk sidang:** demo utama jalan **lokal dari laptop** (paling
> andal), deploy online ke **Railway** sebagai backup + untuk screenshot/laporan.
> Siapkan minimal H-2, karena build image (TensorFlow + YOLO) cukup besar.

---

## 1. Jalankan Lokal (untuk demo sidang)

Kebutuhan: **Python 3.11** (keras 3.15 butuh Python ≥ 3.11; TensorFlow 2.16 mendukung 3.9–3.12).

```bash
# dari folder project (web_skripsi)
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt   # butuh ~1-2 GB, tunggu sampai selesai

python app.py
```

Buka `http://127.0.0.1:10000` (atau set `PORT` kalau mau ganti port).

> Catatan: `run.sh` (gunicorn) tidak bisa dipakai di Windows — itu untuk server
> Linux (Railway/Render). Untuk demo lokal cukup `python app.py`.

---

## 2. Deploy ke Railway

### 2.1 Prasyarat

- Repo GitHub berisi project ini (file `Dockerfile`, `run.sh`, `railway.json`
  sudah tersedia di repo).
- Akun di [railway.com](https://railway.com) — ada **trial gratis $5 (30 hari,
  tanpa kartu kredit)**. Untuk sekali sidang, ini biasanya cukup.

### 2.2 Langkah deploy

1. **Push project ke GitHub** (kalau belum):
   ```bash
   git init
   git add -A
   git commit -m "init deploy"
   git remote add origin https://github.com/<username>/<repo>.git
   git push -u origin main
   ```

2. **Buka railway.com → New Project → Deploy from GitHub repo** → pilih repo
   project ini → klik *Deploy Now*.

3. **Tunggu build selesai** (10–20 menit untuk pertama kali — image
   TensorFlow + PyTorch besar). Jangan panik kalau lama, ini normal.

4. **Set RAM ke 1GB (PENTING!)** — `railway.json` tidak bisa mengatur resource;
   lakukan manual:
   - Buka service kamu → tab **Settings** → **Resources**.
   - **Memory** → set **1 GB** (default 512 MB bisa membuat TensorFlow kehabisan
     memori → service restart terus-menerus).

5. **Cek status deploy**:
   - Tab **Deployments** → tunggu sampai status *Healthy*.
   - `railway.json` sudah otomatis mengatur: builder Dockerfile, healthcheck
     `GET /healthz` (harus balas 200), timeout healthcheck 300 detik (cukup
     untuk muat model saat boot), dan restart otomatis kalau service crash.

6. **Buka URL** — Railway memberikan domain `https://<service>.up.railway.app`
   otomatis. Test: upload gambar pisang → hasil analisis tampil.

7. **Update berikutnya**: cukup `git push` — Railway auto-deploy ulang.

### 2.3 Konfigurasi yang sudah ada (tidak perlu diubah)

| File | Fungsi |
|---|---|
| `Dockerfile` | Base image, install TF/torch/opencv, healthcheck Docker, `CMD ./run.sh` |
| `run.sh` | Menjalankan gunicorn, baca `PORT` (di-set Railway), log ke stdout |
| `railway.json` | Builder Dockerfile, healthcheck `/healthz`, restart ON_FAILURE |
| `app.py` | Endpoint `/healthz` + seluruh aplikasi |

---

## 3. Alternatif: Render

`render.yaml` sudah tersedia (free plan). Caranya: dashboard Render →
**New Web Service** → connect repo → pilih **Docker**.

⚠️ Keterbatasan Render free untuk sidang:
- Instance **tidur setelah ~15 menit idle** → saat demo, request pertama bisa
  menunggu 30–60 detik (model dimuat ulang).
- RAM cuma **512 MB** → berisiko OOM. Kalau pakai Render, pilih plan berbayar
  (selalu aktif) dan test berulang kali.

---

## 4. Troubleshooting

| Gejala | Kemungkinan penyebab | Solusi |
|---|---|---|
| Deploy gagal / build lama | Image TF+torch besar | Wajar 10–20 menit; coba deploy ulang |
| Service restart terus | OOM (RAM 512 MB) | Settings → Resources → RAM **1 GB** |
| Healthcheck gagal | Model belum selesai dimuat | `healthcheckTimeout: 300` sudah di-set; tunggu, cek log |
| URL balas 502 | Service crash saat boot | Buka tab Logs, cari traceback, pastikan RAM cukup |
| Upload error "terlalu besar" | File > 10 MB | Gunakan foto < 10 MB |
| Gambar hasil hilang setelah beberapa hari | File upload dibersihkan otomatis (TTL 7 hari) | Wajar; history lama tampil placeholder |

Cek log: Railway → tab **Deployments** → klik deploy → tab **Logs**.

---

## 5. Checklist H-1 Sidang

- [ ] Demo lokal jalan: `python app.py` → upload 2–3 gambar uji → hasil tampil
- [ ] URL Railway bisa dibuka dari HP (test pakai data seluler, bukan cuma WiFi kampus)
- [ ] Screenshot halaman hasil (untuk slide/laporan) sudah disimpan
- [ ] Video demo singkat (30–60 detik) sebagai cadangan kalau internet gagal
- [ ] Gambar uji (`test_images/`) sudah disiapkan di laptop
