# save as test_model.py and run: python test_model.py
from ultralytics import YOLO
from PIL import Image
import requests, io

# Load your model
model = YOLO("model/best.pt")   # adjust path if needed

print("Classes:", model.names)
print("imgsz override:", model.overrides.get("imgsz"))

# Download a known traffic sign test image
url = "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f9/STOP_sign.jpg/320px-STOP_sign.jpg"
img = Image.open(io.BytesIO(requests.get(url).content)).convert("RGB")

# Try with very low confidence to see if model detects ANYTHING
results = model.predict(source=img, conf=0.01, iou=0.45, imgsz=640, device="cpu", verbose=True)

print(f"\nDetections at conf=0.01: {len(results[0].boxes)}")
for box in results[0].boxes:
    cls_id = int(box.cls[0])
    print(f"  [{cls_id}] {model.names[cls_id]}  conf={float(box.conf[0]):.3f}")