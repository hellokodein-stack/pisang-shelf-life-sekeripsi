from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from PIL import Image, ImageOps
import os
import re
import threading
import time
from datetime import datetime

from predict import predict_image
from shelf_life import estimate_shelf_life

from analysis.segmentation import segment_banana
from analysis.pigment import calculate_pigment
from analysis.necrosis import calculate_necrosis

app = Flask(__name__)

# Model CNN (TensorFlow) dan YOLO dimuat sekali sebagai singleton di proses ini.
# gunicorn dijalankan dengan --threads 4, sehingga prediksi dari beberapa
# thread bisa tumpang tindih. predict() pada model tunggal (terutama YOLO)
# tidak thread-safe, jadi serialkan seluruh pipeline model dengan satu lock.
MODEL_LOCK = threading.Lock()

UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "static/uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# File upload/hasil analisis dihapus otomatis setelah TTL ini (detik) agar
# disk tidak penuh (Render free plan). Riwayat localStorage browser menyimpan
# URL gambar, jadi TTL sengaja panjang (default 7 hari) dan bisa disetel via
# env UPLOAD_TTL_SECONDS.
UPLOAD_TTL_SECONDS = int(os.environ.get("UPLOAD_TTL_SECONDS", 7 * 24 * 3600))

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def cleanup_old_uploads():
    """Hapus file upload/hasil analisis yang lebih tua dari TTL (best-effort).

    Dipanggil saat startup dan setiap ada request /predict. File yang baru
    dibuat tidak mungkin terhapus karena umurnya < TTL. .gitkeep dibiarkan.
    Kegagalan menghapus satu file tidak menggagalkan request.
    """
    cutoff = time.time() - UPLOAD_TTL_SECONDS
    try:
        for entry in os.scandir(UPLOAD_FOLDER):
            if not entry.is_file() or entry.name == ".gitkeep":
                continue
            try:
                if os.path.getmtime(entry.path) < cutoff:
                    os.remove(entry.path)
            except OSError:
                pass  # file sudah hilang / tidak bisa dihapus
    except OSError:
        pass


cleanup_old_uploads()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ===== Rekomendasi Penyimpanan =====
def get_rekomendasi(variety, stage):
    rekomendasi = []

    if stage <= 2:
        rekomendasi.append({
            "icon": "fa-temperature-low",
            "title": "Simpan di suhu 14-16°C",
            "desc": "Pisang mentah sebaiknya disimpan di suhu terkontrol untuk memperlambat pematangan."
        })
        rekomendasi.append({
            "icon": "fa-wind",
            "title": "Hindari etilen berlebih",
            "desc": "Jauhkan dari buah lain yang menghasilkan etilen untuk mencegah pematangan dini."
        })
    elif stage == 3:
        rekomendasi.append({
            "icon": "fa-temperature-half",
            "title": "Suhu ruang 20-22°C",
            "desc": "Biarkan pisang matang sempurna di suhu ruang terbuka."
        })
        rekomendasi.append({
            "icon": "fa-clock",
            "title": "Konsumsi dalam 3-5 hari",
            "desc": "Pisang matang pohon memiliki jendela konsumsi yang terbatas."
        })
    elif stage == 4:
        rekomendasi.append({
            "icon": "fa-snowflake",
            "title": "Simpan di kulkas jika perlu",
            "desc": "Penyimpanan dingin bisa memperlambat pematangan, namun kulit bisa menghitam."
        })
        rekomendasi.append({
            "icon": "fa-bolt",
            "title": "Segera konsumsi atau olah",
            "desc": "Pisang matang optimal sebaiknya segera dikonsumsi atau diolah."
        })
    else:
        rekomendasi.append({
            "icon": "fa-triangle-exclamation",
            "title": "Segera olah atau buang",
            "desc": "Pisang matang lanjut tidak layak dikonsumsi langsung, olah menjadi pisang goreng atau smoothie."
        })
        rekomendasi.append({
            "icon": "fa-box",
            "title": "Pisahkan dari buah lain",
            "desc": "Pisang matang lanjut mengeluarkan etilen tinggi yang mempercepat pematangan buah lain."
        })

    # Rekomendasi spesifik per varietas
    if variety == "raja":
        rekomendasi.append({
            "icon": "fa-utensils",
            "title": "Cocok untuk pisang goreng",
            "desc": "Pisang Raja sangat cocok diolah menjadi pisang goreng, kolak, atau getuk."
        })
    else:
        rekomendasi.append({
            "icon": "fa-blender",
            "title": "Cocok untuk smoothie",
            "desc": "Pisang Ambon sangat cocok untuk smoothie, es pisang, atau dikonsumsi langsung."
        })

    return rekomendasi


# ===== ROUTES =====

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/healthz")
def healthz():
    """Healthcheck endpoint untuk Render (healthCheckPath) dan Docker HEALTHCHECK.

    Ringan dan tidak menyentuh model, sehingga selalu responsif dalam 5 detik
    (batas waktu healthcheck Render) bahkan saat ada prediksi yang berjalan.
    """
    return jsonify({"status": "ok"})


@app.route("/predict", methods=["POST"])
def predict():
    # 1. Validasi file
    if "image" not in request.files:
        return jsonify({"success": False, "error": "Tidak ada gambar yang dikirim"}), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({"success": False, "error": "Nama file kosong"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Format file tidak didukung. Gunakan JPG, PNG, atau WEBP"}), 400

    # 2. Simpan file dengan timestamp (microseconds agar unik walau
    #    beberapa request dengan nama file sama tiba di detik yang sama)
    filename = secure_filename(file.filename)
    name, ext = os.path.splitext(filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{name}_{timestamp}{ext}"

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    # Foto kamera HP bisa sangat besar (2448-4096px, beberapa MB). Di
    # container kecil (mis. Railway 1GB) memprosesnya full-res bisa bikin
    # worker kehabisan memori / lambat sampai proxy timeout (502). CNN cuma
    # butuh 300x300 dan YOLO 640x640, jadi turunkan ke maks MAX_IMAGE_DIM
    # (default 1600px) — hasil analisis praktis identik, memori & waktu
    # jauh lebih kecil. EXIF orientation di-bake supaya CNN (PIL) dan YOLO
    # (cv2) melihat orientasi yang sama.
    try:
        img = ImageOps.exif_transpose(Image.open(filepath)).convert("RGB")
        w, h = img.size
        max_dim = int(os.environ.get("MAX_IMAGE_DIM", 1600))
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            img = img.resize(
                (max(1, int(w * scale)), max(1, int(h * scale))),
                Image.LANCZOS
            )
            img.save(filepath)
    except Exception as downscale_err:
        # Downscale bersifat best-effort — kalau gagal, lanjut full-res.
        print(f"WARN: downscale gambar gagal ({downscale_err})")

    # Bersihkan file lama sambil jalan agar disk tidak menumpuk
    cleanup_old_uploads()

    try:
        # 3-8. Pipeline model (prediksi CNN + segmentasi YOLO + analisis)
        with MODEL_LOCK:
            # 3. Prediksi — label format: "ambon_H5" atau "raja_H12"
            label, confidence, top3 = predict_image(filepath)

            print("=" * 50)
            print("LABEL :", label)
            print("CONFIDENCE :", confidence)

            # 4. Estimasi shelf life
            result = estimate_shelf_life(label)
            print(result)

            # 5. Extract info dari label
            variety = result["variety_lower"]       # "ambon" atau "raja"
            current_day = result["current_day"]      # 1-24
            stage = result["stage"]                  # 1-5
            remaining_days = result["remaining_days"]

            # 6. Kategori utama
            kategori_utama = "Matang" if stage >= 3 else "Mentah"

            # 7. Sub-kategori
            sub_kategori = result["sub_kategori"]

            # 8. Segmentasi YOLO (best-effort). Sebagian kecil foto
            #    (mis. beberapa foto dataset dari HP tertentu) tidak
            #    terdeteksi model YOLO. Kalau gagal, analisis utama
            #    (klasifikasi CNN + daya simpan + rekomendasi) tetap
            #    sukses dengan metrik pigmen/nekrosis estimasi berbasis
            #    stage — pola yang sama dengan tampilan riwayat (history).
            segmentasi_ok = True
            mask_area = 0
            segmented_path = None
            try:
                mask, segmented_img, area, segmented_path = segment_banana(filepath)
                pigmen_kuning = calculate_pigment(segmented_img, mask)
                necrosis_rate = calculate_necrosis(segmented_img, mask)
                mask_area = area
            except Exception as seg_err:
                print(f"WARN: segmentasi gagal ({seg_err}) — pakai estimasi stage")
                segmentasi_ok = False

            if not segmentasi_ok:
                # Estimasi metrik dari stage kematangan (sama dengan viewFromHistory)
                pigmen_map = [0, 8, 25, 68, 85, 95]
                necrosis_map = [0, 2, 5, 12, 18, 35]
                idx = min(stage, len(pigmen_map) - 1)
                pigmen_kuning = pigmen_map[idx]
                necrosis_rate = necrosis_map[idx]

        # 9. Estimasi simpan
        if remaining_days >= 2:
            estimasi_simpan = f"{remaining_days} Hari"
        elif remaining_days == 1:
            estimasi_simpan = "1 Hari"
        else:
            estimasi_simpan = "< 1 Hari"

        # 10. Rekomendasi
        rekomendasi = get_rekomendasi(variety, stage)

        # 11. Warna kategori untuk badge frontend
        if stage <= 2:
            warna_kategori = "hijau"
        elif stage <= 4:
            warna_kategori = "kuning"
        else:
            warna_kategori = "merah"

        # 12. Progress percentage (0-100% seberapa matang)
        progress_pct = min(100, round((current_day / result["max_shelf_life"]) * 100))

        # 13. URL gambar
        image_url = "/" + filepath.replace("\\", "/")

        return jsonify({
            "success": True,
            # Info dasar
            "label": label,
            "confidence": confidence,
            "top3_prediction": top3,
            "image_url": image_url,
            "segmented_image": ("/" + segmented_path.replace("\\", "/")) if segmented_path else None,
            "segmentasi_ok": segmentasi_ok,

            # Varietas & kematangan
            "variety": variety,
            "variety_display": result["variety"],  # "Ambon" atau "Raja"
            "current_day": current_day,
            "stage": stage,
            "kategori_utama": kategori_utama,
            "sub_kategori": sub_kategori,
            "warna_kategori": warna_kategori,
            # Metrik
            "pigmen_kuning": pigmen_kuning,
            "necrosis_rate": necrosis_rate,
            "mask_area": mask_area,
            "progress_pct": progress_pct,
            # Daya simpan
            "remaining_days": remaining_days,
            "max_shelf_life": result["max" \
            "_shelf_life"],
            "estimasi_simpan": estimasi_simpan,
            # Rekomendasi
            "rekomendasi": rekomendasi,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()

        if os.path.exists(filepath):
            os.remove(filepath)

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)