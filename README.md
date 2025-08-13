# InsectDetect Pro

**AI-Powered Insect Detection & Safety Classification**

## Overview

InsectDetect Pro is a real-time insect detection and analytics platform using an ESP32-CAM for image capture and a Flask server for AI-based analysis. Images are sent wirelessly from the ESP32 to the server, analyzed using a YOLO model, and results are displayed instantly on a modern dashboard. The system classifies insects as harmful, caution, or safe, and provides weekly analytics.

## Features

- **Wireless Image Capture:** ESP32-CAM captures and uploads images to the server.
- **Real-Time Analysis:** Images are analyzed using a YOLO model (Ultralytics).
- **Dynamic Dashboard:** Results and analytics are updated instantly via WebSocket (Flask-SocketIO + socket.io).
- **Safety Classification:** Insects are categorized as harmful, caution, or safe.
- **Weekly Analytics:** Chart.js visualizes detection trends for the last 7 days.
- **Batch Processing:** Images are processed in batches for efficiency.
- **Image Zoom & Details:** Click images to zoom and view detection details.
- **ESP32 Control:** Stop/resume camera remotely from the dashboard.
- **Delete All:** Remove all images and results with one click.

## Project Structure

```
Stage_Recherche/
│
├── server.py                # Flask backend, YOLO analysis, WebSocket events
├── ESP-32.c                 # ESP32-CAM firmware for image capture/upload
├── templates/
│   └── index.html           # Main dashboard UI
├── static/
│   ├── backlog/             # Uploaded images awaiting analysis
│   ├── results/             # Analyzed images with bounding boxes
│   └── ...                  # Other static assets
├── insect_analytics.db      # SQLite database for detection history
├── weights/                 # YOLO model weights
└── ...                      # Other scripts and folders
```

## Setup Instructions

### 1. ESP32-CAM Firmware

- Flash `ESP-32.c` to your ESP32-CAM.
- Update WiFi credentials (`ssid`, `password`) and server URL (`serverUrl`) as needed.
- The ESP32 will:
  - Capture images every 10 seconds.
  - Upload images to the Flask server.
  - Buffer failed uploads and retry when WiFi is available.
  - Respond to `/stop` and `/resume` HTTP endpoints for remote control.

### 2. Python Server

#### Requirements

- Python 3.8+
- Install dependencies:
  ```bash
  pip install flask flask-socketio ultralytics pillow requests
  ```

#### Model Weights

- Place your YOLO model weights in the `weights/` directory.
- Update the path in `server.py` if needed:
  ```python
  model = YOLO("weights/hub/xA1Da5C419YousVyoZHM/best.pt")
  ```

#### Running the Server

```bash
python server.py
```
- The server will start on `http://0.0.0.0:5000`.
- Images are saved in `static/backlog/` and results in `static/results/`.
- Detection history is stored in `insect_analytics.db`.

## Changing the ESP32 IP Address

If your ESP32-CAM receives a new IP address on your network, you must update the Flask server so it can communicate with the camera for remote control (Stop/Resume).

**To change the ESP32 IP address:**

1. **Find the new IP address of your ESP32-CAM.**
   - You can view it in the Serial Monitor after boot, or check your router’s DHCP client list.

2. **Update the IP address in `server.py`:**
   - Locate the following routes:
     ```python
     @app.route('/stop_esp32', methods=['POST'])
     def stop_esp32():
         esp32_url = 'http://<ESP32_IP>/stop'
         # ...
     
     @app.route('/resume_esp32', methods=['POST'])
     def resume_esp32():
         esp32_url = 'http://<ESP32_IP>/resume'
         # ...
     ```
   - Replace `<ESP32_IP>` with your new ESP32 address (e.g. `10.10.54.41`):
     ```python
     esp32_url = 'http://10.10.54.41/stop'
     esp32_url = 'http://10.10.54.41/resume'
     ```

3. **Restart your Flask server** to apply the change.

---

**Note:**  
If your ESP32 IP changes frequently, consider using a static IP or mDNS for
### 3. Dashboard

- Open `http://<server-ip>:5000` in your browser.
- Features:
  - View backlog and analyzed images.
  - Click images to zoom and see detection details.
  - Weekly analytics chart.
  - Stop/resume ESP32 camera.
  - Delete all images.

## How It Works

1. **Image Upload:** ESP32 sends images to `/upload_image` (binary POST).
2. **Analysis:** Flask server analyzes images with YOLO, draws bounding boxes, saves results.
3. **Database:** Detection info is stored in SQLite for analytics.
4. **Real-Time Updates:** When a new image arrives, the server emits a WebSocket event. The dashboard updates instantly.
5. **Analytics:** Chart.js displays detection trends for the last 7 days.

## API Endpoints

- `POST /upload_image` — Upload image (binary).
- `GET /live_updates` — Get current images, results, predictions, analytics (JSON).
- `POST /delete_all` — Delete all images/results.
- `POST /stop_esp32` — Stop ESP32 camera.
- `POST /resume_esp32` — Resume ESP32 camera.

## Customization

- **Detection Categories:** Edit `INSECT_CATEGORIES` in `server.py` to change classification.
- **Model:** Replace YOLO weights for different insect datasets.
- **UI:** Modify `templates/index.html` for custom dashboard features.

## Troubleshooting

- **ESP32 Not Uploading:** Check WiFi credentials and server URL.
- **Model Errors:** Ensure YOLO weights are compatible and path is correct.
- **WebSocket Issues:** Make sure Flask-SocketIO is installed and not blocked by firewall.
- **Database:** If analytics are missing, check `insect_analytics.db` for data.

## Credits

- YOLO by Ultralytics
- Flask & Flask-SocketIO
- Chart.js
- ESP32-CAM

---


