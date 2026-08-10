import json
import numpy as np
from pathlib import Path

# Keras 3 (dipakai oleh TensorFlow 2.16+) tidak lagi menyediakan
# tensorflow.keras.preprocessing.image; utilitas load_img/img_to_array
# pindah ke keras.utils.
from tensorflow.keras.models import load_model
from tensorflow.keras.utils import load_img, img_to_array
from tensorflow.keras.applications.efficientnet import preprocess_input

# ==========================
# PATH
# ==========================

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "models" / "efficientnetb0_model.keras"
CLASS_PATH = BASE_DIR / "models" / "class_indices.json"

# ==========================
# LOAD MODEL
# ==========================

print("MODEL PATH :", MODEL_PATH)
print("MODEL EXISTS :", MODEL_PATH.exists())

model = load_model(MODEL_PATH)

# ==========================
# LOAD CLASS
# ==========================

with open(CLASS_PATH, "r") as f:
    class_indices = json.load(f)

idx_to_class = {v: k for k, v in class_indices.items()}

# ==========================
# PREDICT
# ==========================

IMG_SIZE = (300, 300)


def predict_image(img_path):

    img = load_img(img_path, target_size=IMG_SIZE)

    img = img_to_array(img)

    img = np.expand_dims(img, axis=0)

    img = preprocess_input(img)

    # Prediksi
    prediction = model.predict(img, verbose=0)[0]

    print("\n===== PROBABILITAS CNN =====")

    for i, p in enumerate(prediction):
        print(idx_to_class[i], ":", round(float(p), 4))

    print("============================")

    # Top-3 prediction
    top3_idx = np.argsort(prediction)[-3:][::-1]

    top3 = []

    for idx in top3_idx:
        top3.append({
            "label": idx_to_class[idx],
            "confidence": round(float(prediction[idx]) * 100, 2)
        })

    predicted_class = top3[0]["label"]
    confidence = top3[0]["confidence"]

    return predicted_class, confidence, top3


# ==========================
# TEST
# ==========================

if __name__ == "__main__":

    label, confidence, top3 = predict_image("test_images/testambon.jpg")

    print("\nPrediksi :", label)
    print("Confidence :", confidence, "%")

    print("\nTop 3 Prediction")

    for item in top3:
        print(item)