from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import os
import re
from datetime import datetime

from predict import predict_image
from shelf_life import estimate_shelf_life

from analysis.segmentation import segment_banana
from analysis.pigment import calculate_pigment
from analysis.necrosis import calculate_necrosis

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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

    # 2. Simpan file dengan timestamp
    filename = secure_filename(file.filename)
    name, ext = os.path.splitext(filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{timestamp}{ext}"

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
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
        current_day = result["current_day"]      # 1-17
        stage = result["stage"]                  # 1-5
        remaining_days = result["remaining_days"]

        # 6. Kategori utama
        kategori_utama = "Matang" if stage >= 3 else "Mentah"

        # 7. Sub-kategori
        sub_kategori = result["sub_kategori"]

        # 8. Segmentasi YOLO
        mask, segmented_img, area, segmented_path = segment_banana(filepath)

        # Analisis Pigmentasi
        pigmen_kuning = calculate_pigment(
            segmented_img,
            mask
        )

        # Analisis Nekrosis
        necrosis_rate = calculate_necrosis(
            segmented_img,
            mask
        )

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
        image_url = f"/{filepath}"

        return jsonify({
            "success": True,
            # Info dasar
            "label": label,
            "confidence": confidence,
            "top3_prediction": top3,
            "image_url": image_url,
            "segmented_image": "/" + segmented_path.replace("\\", "/"),

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
            "mask_area": area,
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