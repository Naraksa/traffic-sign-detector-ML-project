import io
import base64
import traceback
from flask import Flask, request, jsonify, render_template
from PIL import Image
from utils.khmer_mapping import traffic_signs_kh, lookup

app   = Flask(__name__)
model = None


# ── Model Loading ─────────────────────────────────────────────────────────────
def load_model():
    global model
    try:
        from ultralytics import YOLO
        model = YOLO("model/best.pt")   # adjust path if needed

        print("=" * 65)
        print("✅  Model loaded. Verifying class → Khmer mapping:")
        all_ok = True
        for idx, name in model.names.items():
            en, kh = lookup(name)
            matched = kh != en   # if they differ, lookup found a Khmer string
            status  = "✅" if matched else "⚠️  NO KHMER MATCH"
            if not matched:
                all_ok = False
            print(f"   [{idx:>2}] '{name}'  →  {en}  |  {kh}  {status}")
        if all_ok:
            print("   All classes matched successfully.")
        else:
            print("   ⚠️  Some classes have no Khmer mapping — check khmer_mapping.py")
        print("=" * 65)

    except Exception as e:
        print(f"⚠️  Model failed to load, running in demo mode: {e}")
        traceback.print_exc()
        model = None


load_model()


# ── Inference ─────────────────────────────────────────────────────────────────
def run_inference(image_bytes: bytes) -> list:
    if model is None:
        return get_demo_detections()

    try:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h    = pil_img.size

        all_boxes = []

        # ── Pass 1: full image at 640
        all_boxes += _predict(pil_img, conf=0.20)

        # ── Pass 2: full image upscaled to 1280 (catches small signs)
        large = pil_img.resize((min(w * 2, 1920), min(h * 2, 1920)), Image.LANCZOS)
        all_boxes += _predict(large, conf=0.20, scale=0.5)

        # ── Pass 3: tile the image into quadrants (catches edge signs)
        tiles = [
            (0,   0,   w//2, h//2),
            (w//2, 0,  w,    h//2),
            (0,   h//2, w//2, h),
            (w//2, h//2, w,   h),
        ]
        for (x1, y1, x2, y2) in tiles:
            tile = pil_img.crop((x1, y1, x2, y2))
            boxes = _predict(tile, conf=0.20)
            # Offset bboxes back to full-image coordinates
            for b in boxes:
                b["bbox"] = [
                    b["bbox"][0] + x1,
                    b["bbox"][1] + y1,
                    b["bbox"][2] + x1,
                    b["bbox"][3] + y1,
                ]
            all_boxes += boxes

        # ── Deduplicate overlapping boxes (simple IoU NMS)
        detections = nms_dedupe(all_boxes, iou_thresh=0.4)

        print(f"[inference] {len(detections)} detection(s) after NMS")
        for d in detections:
            print(f"  '{d['class_raw']}' conf={d['confidence']:.3f} bbox={d['bbox']}")

        return detections

    except Exception as e:
        traceback.print_exc()
        return []


def _predict(pil_img, conf=0.20, scale=1.0) -> list:
    """Run model on one image, return list of detection dicts."""
    results = model.predict(
        source=pil_img,
        conf=conf,
        iou=0.45,
        imgsz=640,
        device="cpu",
        verbose=False,
    )
    out = []
    for r in results:
        if r.boxes is None:
            continue
        for box in r.boxes:
            cls_id    = int(box.cls[0])
            conf_val  = float(box.conf[0])
            x1,y1,x2,y2 = box.xyxy[0].tolist()
            class_raw = model.names.get(cls_id, f"class_{cls_id}")
            en, kh    = lookup(class_raw)
            out.append({
                "sign_en":    en,
                "sign_kh":    kh,
                "confidence": round(conf_val, 4),
                "bbox":       [round(v * scale, 1) for v in [x1, y1, x2, y2]],
                "class_id":   cls_id,
                "class_raw":  class_raw,
            })
    return out


def nms_dedupe(detections: list, iou_thresh=0.4) -> list:
    """Remove duplicate boxes from multi-scale passes using IoU."""
    if not detections:
        return []

    # Sort by confidence descending
    dets = sorted(detections, key=lambda d: d["confidence"], reverse=True)
    kept = []

    while dets:
        best = dets.pop(0)
        kept.append(best)
        dets = [d for d in dets if _iou(best["bbox"], d["bbox"]) < iou_thresh]

    return kept


def _iou(a, b) -> float:
    """Intersection over Union for two [x1,y1,x2,y2] boxes."""
    ix1 = max(a[0], b[0]); iy1 = max(a[1], b[1])
    ix2 = min(a[2], b[2]); iy2 = min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    area_a = (a[2]-a[0]) * (a[3]-a[1])
    area_b = (b[2]-b[0]) * (b[3]-b[1])
    return inter / (area_a + area_b - inter)

# ── Demo Detections (model not loaded) ────────────────────────────────────────
def get_demo_detections():
    return [
        {
            "sign_en":    "Stop",
            "sign_kh":    "ឈប់",
            "confidence": 0.91,
            "bbox":       [120.0, 80.0, 280.0, 240.0],
            "class_id":   0,
            "class_raw":  "STOP",
        },
        {
            "sign_en":    "No Entry",
            "sign_kh":    "ហាមចូល",
            "confidence": 0.76,
            "bbox":       [300.0, 100.0, 460.0, 260.0],
            "class_id":   1,
            "class_raw":  "NO ENTRY",
        },
    ]


# ── Routes ────────────────────────────────────────────────────────────────────
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
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/debug")
def debug():
    """Visit /debug in browser to verify model classes and mapping."""
    if model is None:
        return jsonify({"status": "demo_mode", "model": None})

    mapping_check = {}
    for idx, name in model.names.items():
        en, kh = lookup(name)
        mapping_check[idx] = {
            "raw":     name,
            "english": en,
            "khmer":   kh,
            "matched": kh != en,
        }

    return jsonify({
        "status":        "loaded",
        "total_classes": len(model.names),
        "mapping":       mapping_check,
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)