from ultralytics import YOLO
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from PIL import Image, ImageDraw, ImageFont
import os
import json
import requests
from datetime import datetime, date
import sqlite3

app = Flask(__name__)
socketio = SocketIO(app)

UPLOAD_FOLDER = 'static/backlog'
RESULT_FOLDER = 'static/results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

BACKLOG_SIZE = 10

INSECT_CATEGORIES = {
    'rice_planthopper': 'harmful', 'rice_leaf_roller': 'harmful', 'chilo_suppressalis': 'harmful', 'armyworm': 'harmful',
    'bollworm': 'harmful', 'meadow_borer': 'harmful', 'spodoptera_litura': 'harmful', 'spodoptera_exigua': 'harmful',
    'stem_borer': 'harmful', 'plutella_xylostella': 'harmful', 'spodoptera_cabbage': 'harmful', 'scotogramma_trifolii_rottemberg': 'harmful',
    'holotrichia_oblita': 'harmful', 'holotrichia_parallela': 'harmful', 'anomala_corpulenta': 'harmful', 'gryllotalpa_orientalis': 'harmful',
    'agriotes_fuscicollis_miwa': 'harmful', 'melahotus': 'harmful',
    'athetis_lepigone': 'caution', 'yellow_tiger': 'caution', 'land_tiger': 'caution', 'eight_character_tiger': 'caution', 'nematode_trench': 'caution',
    'little_gecko': 'safe'
}
def get_insect_category(insect_name):
    return INSECT_CATEGORIES.get(insect_name.lower(), 'caution')

def init_db():
    conn = sqlite3.connect('insect_analytics.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS detections
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT,
                  insect_name TEXT,
                  category TEXT,
                  confidence REAL,
                  image_filename TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()
init_db()

def save_detection(insect_name, category, confidence, image_filename):
    conn = sqlite3.connect('insect_analytics.db')
    c = conn.cursor()
    today = date.today().isoformat()
    c.execute("INSERT INTO detections (date, insect_name, category, confidence, image_filename) VALUES (?, ?, ?, ?, ?)",
              (today, insect_name, category, confidence, image_filename))
    conn.commit()
    conn.close()

def get_daily_analytics():
    conn = sqlite3.connect('insect_analytics.db')
    c = conn.cursor()
    c.execute("""
        SELECT date, insect_name, category
        FROM detections
        WHERE date >= date('now', '-7 days')
        ORDER BY date ASC
    """)
    results = c.fetchall()
    conn.close()

    dates = sorted(list({r[0] for r in results}))
    insect_set = set()
    insect_category = {}
    for _, insect, category in results:
        insect_set.add(insect)
        insect_category[insect] = category

    insects = sorted(list(insect_set))
    datasets = []
    color_map = {'harmful': 'rgba(220,53,69,0.8)', 'safe': 'rgba(40,167,69,0.8)', 'caution': 'rgba(255,193,7,0.8)'}
    for insect in insects:
        data = []
        for d in dates:
            found = any(r[0] == d and r[1] == insect for r in results)
            data.append(1 if found else 0)
        datasets.append({
            'label': insect,
            'data': data,
            'backgroundColor': color_map.get(insect_category[insect], 'rgba(108,117,125,0.8)'),
            'insect_name': insect
        })
    def sort_key(ds):
        cat = insect_category.get(ds['label'], 'caution')
        return {'harmful': 0, 'caution': 1, 'safe': 2}.get(cat, 3)
    datasets.sort(key=sort_key)

    chart_data = {
        'labels': [datetime.fromisoformat(d).strftime('%d/%m') for d in dates],
        'datasets': datasets
    }
    return chart_data

@app.route('/')
def index():
    backlog_images = sorted(os.listdir(UPLOAD_FOLDER))
    result_images = sorted(os.listdir(RESULT_FOLDER))
    analytics_data = get_daily_analytics()
    predictions = get_predictions_for_results(result_images)
    return render_template(
        'index.html',
        backlog_images=backlog_images,
        result_images=result_images,
        analytics_data=analytics_data,
        predictions=predictions
    )

@app.route('/upload_image', methods=['POST'])
def upload_image():
    img_data = request.data
    img_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
    img_path = os.path.join(UPLOAD_FOLDER, img_filename)
    with open(img_path, 'wb') as f:
        f.write(img_data)
    print(f"Received image: {img_filename}")

    analyze_backlog()
    # Notifie tous les clients qu'une nouvelle image est arrivée
    socketio.emit('new_image')
    return jsonify({"status": "ok", "filename": img_filename})

def analyze_backlog():
    backlog_images = sorted(os.listdir(UPLOAD_FOLDER))
    for img_filename in backlog_images:
        img_path = os.path.join(UPLOAD_FOLDER, img_filename)
        results = model(img_path)
        predictions = []
        img = Image.open(img_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 18)
        except:
            font = None
        found_detection = False
        for r in results:
            for box in r.boxes:
                found_detection = True
                cls_idx = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                name = r.names[cls_idx]
                category = get_insect_category(name)
                xyxy = box.xyxy[0].cpu().numpy()
                bbox = xyxy.tolist()
                predictions.append({
                    "name": name,
                    "confidence": round(conf, 3),
                    "category": category,
                    "bbox": bbox
                })
                color_map = {'harmful': (220, 53, 69), 'safe': (40, 167, 69), 'caution': (255, 193, 7)}
                color = color_map.get(category, (108, 117, 125))
                draw.rectangle([xyxy[0], xyxy[1], xyxy[2], xyxy[3]], outline=color, width=3)
                label = f"{name} {conf:.2f} ({category})"
                text_position = (xyxy[0], xyxy[1] - 25)
                if font:
                    text_bbox = draw.textbbox(text_position, label, font=font)
                    draw.rectangle(text_bbox, fill=(0,0,0,180))
                    draw.text(text_position, label, fill=(255,255,255), font=font)
                else:
                    draw.text((xyxy[0], xyxy[1] - 20), label, fill=(255,255,255))
                save_detection(name, category, conf, img_filename)
        if found_detection:
            result_path = os.path.join(RESULT_FOLDER, f"result_{img_filename}")
            img.save(result_path)
        img.close()
        os.remove(img_path)

def cleanup_results_folder():
    result_images = sorted(os.listdir(RESULT_FOLDER), key=lambda x: os.path.getctime(os.path.join(RESULT_FOLDER, x)))
    while len(result_images) > 15:
        oldest = result_images.pop(0)
        os.remove(os.path.join(RESULT_FOLDER, oldest))

cleanup_results_folder()

def get_predictions_for_results(result_images):
    conn = sqlite3.connect('insect_analytics.db')
    c = conn.cursor()
    predictions = {}
    for img in result_images:
        original_img = img.replace("result_", "")
        c.execute("SELECT insect_name, category, confidence FROM detections WHERE image_filename = ?", (original_img,))
        preds = [{
            "name": row[0],
            "category": row[1],
            "confidence": row[2]
        } for row in c.fetchall()]
        predictions[img] = preds
    conn.close()
    return predictions

@app.route('/delete_all', methods=['POST'])
def delete_all():
    for f in os.listdir(UPLOAD_FOLDER):
        os.remove(os.path.join(UPLOAD_FOLDER, f))
    for f in os.listdir(RESULT_FOLDER):
        os.remove(os.path.join(RESULT_FOLDER, f))
    return ('', 204)

@app.route('/live_updates')
def live_updates():
    backlog_images = sorted(os.listdir(UPLOAD_FOLDER))
    result_images = sorted(os.listdir(RESULT_FOLDER))
    predictions = get_predictions_for_results(result_images)
    analytics_data = get_daily_analytics()
    return jsonify({
        "backlog_images": backlog_images,
        "result_images": result_images,
        "predictions": predictions,
        "analytics_data": analytics_data
    })

@app.route('/stop_esp32', methods=['POST'])
def stop_esp32():
    esp32_url = 'http://10.10.54.41/stop'  # Nouvelle IP de l'ESP32
    try:
        resp = requests.post(esp32_url, timeout=2)
        return jsonify({"status": "sent", "esp32_response": resp.text})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/resume_esp32', methods=['POST'])
def resume_esp32():
    esp32_url = 'http://10.10.54.41/resume'  # Nouvelle IP de l'ESP32
    try:
        resp = requests.post(esp32_url, timeout=2)
        return jsonify({"status": "sent", "esp32_response": resp.text})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

model = YOLO("weights/hub/xA1Da5C419YousVyoZHM/best.pt")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)