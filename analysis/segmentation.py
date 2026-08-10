import os
from pathlib import Path
from unittest import result

import cv2
import numpy as np
from ultralytics import YOLO

# ==========================================================
# Load YOLOv8 Segmentation Model
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "banana_seg.pt"

model = YOLO(str(MODEL_PATH))


# ==========================================================
# Segment Banana
# ==========================================================

def segment_banana(image_path):
    """
    Segmentasi pisang menggunakan YOLOv8 Segmentation.

    Returns
    -------
    mask : ndarray
        Mask biner (0 / 255)

    segmented : ndarray
        Hasil gambar yang sudah dimasking

    area : int
        Luas area pisang (pixel)

    output_path : str
        Lokasi file hasil segmentasi
    """

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(f"Gagal membaca gambar: {image_path}")

    h, w = image.shape[:2]

    # conf=0.1: model hasil training memberi confidence ~0.18 pada foto
    # pisang yang jelas (mis. test_images/testambon.jpg), jadi threshold
    # 0.25 terlalu tinggi dan membuat request gagal dengan
    # "Pisang tidak terdeteksi." (500). 0.1 masih menyaring deteksi
    # noise tanpa menolak foto pisang yang valid.
    results = model.predict(
        source=image_path,
        conf=0.1,
        verbose=False
    )

    if len(results) == 0:
        raise ValueError("YOLO tidak menghasilkan prediksi.")

    result = results[0]

    print("=" * 50)
    print("DEBUG SEGMENTASI")
    print("Boxes :", result.boxes)
    print("Masks :", result.masks)
    print("=" * 50)

    # Simpan hasil visualisasi YOLO.
    # Nama file dibuat unik per request (dari nama file upload yang sudah
    # ditimestamp) agar request bersamaan tidak saling menimpa hasilnya.
    stem = os.path.splitext(os.path.basename(image_path))[0]

    annotated = result.plot()

    yolo_output = os.path.join(
        "static",
        "uploads",
        f"{stem}_yolo_result.jpg"
    )

    cv2.imwrite(yolo_output, annotated)

    if result.masks is None or len(result.masks.data) == 0:
        raise ValueError("Pisang tidak terdeteksi.")

    masks = result.masks.data.cpu().numpy()
    confidences = result.boxes.conf.cpu().numpy()

    print("Confidence tiap objek:", confidences)
    print("Mask yang dipilih:", np.argmax(confidences))

    best_index = np.argmax(confidences)

    best_mask = masks[best_index]

    best_mask = cv2.resize(
        best_mask,
        (w, h),
        interpolation=cv2.INTER_NEAREST
    )

    best_mask = (best_mask > 0.5).astype(np.uint8)

    if best_mask is None:
        raise ValueError("Mask tidak ditemukan.")

    mask = (best_mask * 255).astype(np.uint8)

    segmented = cv2.bitwise_and(
        image,
        image,
        mask=mask
    )

    area = int(np.count_nonzero(mask))

    output_path = os.path.join(
        "static",
        "uploads",
        f"{stem}_segmented_result.png"
    )

    cv2.imwrite(output_path, segmented)

    return mask, segmented, area, output_path