"""
Flask REST API Server - Smart Watering System
Backend server nhận data từ ESP32, chạy AI model, serve dashboard
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pickle
import numpy as np
import os
from datetime import datetime

# Import database functions
from database import (
    init_db, insert_sensor_data, get_history, 
    get_latest_reading, insert_watering_event,
    insert_command, get_pending_command
)

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS để web dashboard call được API

# Paths
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'data', 'model.pkl')
SCALER_PATH = os.path.join(os.path.dirname(__file__), 'data', 'scaler.pkl')

# Load AI model khi server start
model = None
scaler = None

def load_model():
    """Load trained model và scaler"""
    global model, scaler
    
    try:
        with open(MODEL_PATH, 'rb') as f:
            model = pickle.load(f)
        
        with open(SCALER_PATH, 'rb') as f:
            scaler = pickle.load(f)
        
        print("✅ AI Model loaded successfully!")
        return True
    
    except FileNotFoundError:
        print("⚠️  Model not found! Please run train_model.py first")
        print("   Server will run without AI (manual mode only)")
        return False


def predict_watering(moisture, temp, humidity):
    """
    Chạy AI model để quyết định có cần tưới không
    Args:
        moisture: độ ẩm đất (0-100%)
        temp: nhiệt độ (°C)
        humidity: độ ẩm không khí (%)
    Returns:
        dict: {should_water: bool, confidence: float}
    """
    if model is None or scaler is None:
        # Fallback to rule-based nếu model chưa load
        should_water = moisture < 30
        return {'should_water': should_water, 'confidence': 1.0}
    
    # Prepare input
    X = np.array([[moisture, temp, humidity]])
    X_scaled = scaler.transform(X)
    
    # Predict
    prediction = model.predict(X_scaled)[0]
    confidence = model.predict_proba(X_scaled)[0]
    
    return {
        'should_water': bool(prediction == 1),
        'confidence': float(confidence[prediction])
    }


# ============= API ENDPOINTS =============

@app.route('/')
def index():
    """Serve dashboard HTML"""
    return send_from_directory('static', 'index.html')


@app.route('/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    """
    Nhận sensor data từ ESP32
    Expected JSON: {moisture, temperature, humidity}
    Returns: {should_water, confidence}
    """
    try:
        data = request.get_json()
        
        # Validate input
        if not all(k in data for k in ['moisture', 'temperature', 'humidity']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        moisture = float(data['moisture'])
        temp = float(data['temperature'])
        humidity = float(data['humidity'])
        
        # Save to database
        insert_sensor_data(moisture, temp, humidity)
        
        # Run AI prediction
        result = predict_watering(moisture, temp, humidity)
        
        # Log if AI suggests watering
        if result['should_water']:
            insert_watering_event('suggested', 'auto')
        
        print(f"📊 Sensor: M={moisture:.1f}% T={temp:.1f}°C H={humidity:.1f}% "
              f"→ Water: {result['should_water']}")
        
        return jsonify(result), 200
    
    except Exception as e:
        print(f"❌ Error in /api/sensor-data: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/current', methods=['GET'])
def get_current():
    """
    Lấy sensor reading mới nhất (cho dashboard)
    Returns: {timestamp, moisture, temperature, humidity}
    """
    try:
        latest = get_latest_reading()
        
        if latest is None:
            return jsonify({'error': 'No data available'}), 404
        
        return jsonify(latest), 200
    
    except Exception as e:
        print(f"❌ Error in /api/current: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/history', methods=['GET'])
def get_history_data():
    """
    Lấy sensor history (cho chart)
    Query param: hours (default 24)
    Returns: [{timestamp, moisture, temperature, humidity}, ...]
    """
    try:
        hours = int(request.args.get('hours', 24))
        history = get_history(hours=hours)
        
        return jsonify(history), 200
    
    except Exception as e:
        print(f"❌ Error in /api/history: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/control', methods=['POST'])
def manual_control():
    """
    Nhận manual control command từ dashboard
    Expected JSON: {action: "on" or "off"}
    """
    try:
        data = request.get_json()
        action = data.get('action', '').lower()
        
        if action not in ['on', 'off']:
            return jsonify({'error': 'Invalid action'}), 400
        
        # Save command to queue (ESP32 sẽ poll)
        insert_command(action)
        
        # Log watering event
        insert_watering_event(action, 'manual')
        
        print(f"🎮 Manual control: {action.upper()}")
        
        return jsonify({'status': 'success', 'action': action}), 200
    
    except Exception as e:
        print(f"❌ Error in /api/control: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/command', methods=['GET'])
def get_command():
    """
    ESP32 poll endpoint để lấy manual command
    Returns: {command: "on" or "off"} hoặc {command: null}
    """
    try:
        cmd = get_pending_command()
        
        if cmd:
            return jsonify({'command': cmd['command']}), 200
        else:
            return jsonify({'command': None}), 200
    
    except Exception as e:
        print(f"❌ Error in /api/command: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    """
    Health check endpoint
    Returns: server status và model info
    """
    return jsonify({
        'status': 'running',
        'model_loaded': model is not None,
        'timestamp': datetime.now().isoformat()
    }), 200


# ============= MAIN =============

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🌱 Smart Watering System - Flask Server")
    print("="*60 + "\n")
    
    # Initialize database
    print("🔧 Initializing database...")
    init_db()
    
    # Load AI model
    print("🤖 Loading AI model...")
    load_model()
    
    print("\n" + "="*60)
    print("🚀 Server starting...")
    print("📍 Dashboard: http://localhost:5000")
    print("📍 API Docs: http://localhost:5000/api/status")
    print("="*60 + "\n")
    
    # Run Flask server
    app.run(
        host='0.0.0.0',  # Listen trên tất cả network interfaces
        port=5000,
        debug=True        # Enable debug mode (auto-reload khi code thay đổi)
    )
