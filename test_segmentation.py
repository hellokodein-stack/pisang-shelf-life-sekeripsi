from ultralytics import YOLO

model = YOLO("models/banana_seg.pt")

results = model.predict(
    source="test_images/testambon.jpg",
    save=True,
    conf=0.25
)

print(results)