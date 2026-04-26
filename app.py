import os
import io
import base64
from flask import Flask, request, jsonify, render_template
from utils.khmer_mapping import traffic_signs_kh

app = Flask(__name__)

# ── Load YOLO model ──────────────────────────────────────────────────────────
model = None
try:
    import importlib
    ultralytics = importlib.import_module("ultralytics")
    YOLO = ultralytics.YOLO
    MODEL_PATH = os.environ.get("MODEL_PATH", "model/best.pt")
    if os.path.exists(MODEL_PATH):
        model = YOLO(MODEL_PATH)
        print(f"✅ Model loaded: {MODEL_PATH}")
    else:
        print(f"⚠️  Model not found at '{MODEL_PATH}'. Running in DEMO mode.")
except ImportError:
    print("⚠️  ultralytics not installed. Running in DEMO mode.")


def run_inference(image_bytes: bytes) -> list[dict]:
    """Run YOLO inference and return list of detections."""
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    if model is None:
        # DEMO: return a fake result so the UI can be tested
        import random
        sign = random.choice(list(traffic_signs_kh.keys()))
        return [{
            "sign_en": sign,
            "sign_kh": traffic_signs_kh[sign],
            "confidence": round(random.uniform(0.72, 0.98), 4),
            "bbox": [60, 60, 220, 220],
        }]

    results = model(img)
    detections = []
    for r in results:
        if r.boxes is None:
            continue
        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf   = float(box.conf[0])
            label  = r.names[cls_id].upper()
            khmer  = traffic_signs_kh.get(label, label)
            xyxy   = box.xyxy[0].tolist()
            detections.append({
                "sign_en":    label,
                "sign_kh":    khmer,
                "confidence": round(conf, 4),
                "bbox":       [int(x) for x in xyxy],
            })
    return detections


# ── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/detect", methods=["POST"])
def detect():
    try:
        data = request.get_json(force=True)
        if not data or "image" not in data:
            return jsonify({"success": False, "error": "No image provided"}), 400

        image_data = data["image"]
        if "," in image_data:
            image_data = image_data.split(",", 1)[1]

        image_bytes = base64.b64decode(image_data)
        detections  = run_inference(image_bytes)

        return jsonify({
            "success":    True,
            "detections": detections,
            "demo_mode":  model is None,
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)