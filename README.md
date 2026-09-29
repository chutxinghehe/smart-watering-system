# 🌱 Smart Watering System

IoT Smart Watering System with AI - ESP32 + Flask + Machine Learning

## ✨ Features

- 🤖 **AI Decision Making**: RandomForest model predicts when to water
- 📊 **Real-time Monitoring**: Dashboard displays soil moisture, temperature, humidity
- 🎮 **Manual Control**: Control water pump via web interface
- 📈 **History Chart**: 24-hour data visualization
- 📱 **Responsive**: Works on PC, tablet, and mobile
- ☁️ **Cloud-ready**: Deploy to Render.com for worldwide access

## 🏗️ Architecture

```
ESP32 (Sensors + Pump) ──WiFi──→ Flask Server (AI Model) ──HTTP──→ Web Dashboard
                                        ↓
                                   SQLite DB
```

## 🔧 Hardware

- ESP32 Dev Board
- Capacitive Soil Moisture Sensor
- DHT22 Temperature/Humidity Sensor
- 5V Relay Module
- Mini Water Pump 5V

## 🚀 Quick Deploy to Render

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

### 2. Deploy on Render

1. Go to https://render.com
2. Sign up with GitHub
3. New + → Web Service
4. Connect your repository
5. Configure:
   - **Name**: `smart-watering`
   - **Region**: `Singapore`
   - **Build Command**: `pip install -r server/requirements.txt && python server/train_model.py`
   - **Start Command**: `cd server && gunicorn app:app --bind 0.0.0.0:$PORT`
   - **Instance**: Free
6. Create Web Service

### 3. Update ESP32 Code

Replace in `esp32_firmware/smart_watering/smart_watering.ino`:

```cpp
const char* SERVER_URL = "https://your-app.onrender.com";
```

Then update API calls to use SERVER_URL instead of SERVER_IP.

## 📱 Local Development

### Install Dependencies

```bash
pip install -r server/requirements.txt
```

### Train AI Model

```bash
python server/train_model.py
```

### Run Server

```bash
python server/app.py
```

Dashboard: http://localhost:5000

### Flash ESP32

1. Open `esp32_firmware/smart_watering/smart_watering.ino` in Arduino IDE
2. Update Wi-Fi credentials and server URL
3. Upload to ESP32

## 📊 API Endpoints

- `GET /` - Web dashboard
- `POST /api/sensor-data` - Receive sensor data from ESP32
- `GET /api/current` - Get latest sensor readings
- `GET /api/history?hours=24` - Get historical data
- `POST /api/control` - Manual pump control
- `GET /api/command` - ESP32 polls for manual commands
- `GET /api/status` - Health check

## 🛠️ Tech Stack

**Backend:**
- Python 3.11+
- Flask (REST API)
- scikit-learn (AI model)
- pandas, numpy (data processing)
- SQLite (database)

**Frontend:**
- HTML5, CSS3, JavaScript
- Chart.js (data visualization)

**Hardware:**
- ESP32 (Wi-Fi microcontroller)
- Arduino C++ (firmware)

## 📄 License

MIT License

## 🤝 Contributing

Pull requests are welcome!

## 📧 Contact

For questions or support, please open an issue.
