"""
Database module - Quản lý SQLite database cho Smart Watering System
Lưu trữ: sensor readings, watering history
"""

import sqlite3
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'sensors.db')

def init_db():
    """
    Tạo database và tables nếu chưa tồn tại
    Tables:
    - sensor_readings: lưu dữ liệu cảm biến (moisture, temp, humidity)
    - watering_history: lưu lịch sử tưới nước
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table lưu sensor data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            soil_moisture REAL NOT NULL,
            temperature REAL NOT NULL,
            humidity REAL NOT NULL
        )
    ''')
    
    # Table lưu watering history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watering_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            action TEXT NOT NULL,
            source TEXT NOT NULL,
            duration INTEGER DEFAULT 10
        )
    ''')
    
    # Table lưu manual command (cho ESP32 poll)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            command TEXT NOT NULL,
            executed INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized at: {DB_PATH}")


def insert_sensor_data(moisture, temp, humidity):
    """
    Thêm sensor reading mới vào database
    Args:
        moisture: độ ẩm đất (0-100%)
        temp: nhiệt độ (°C)
        humidity: độ ẩm không khí (%)
    Returns:
        ID của record vừa tạo
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO sensor_readings (soil_moisture, temperature, humidity)
        VALUES (?, ?, ?)
    ''', (moisture, temp, humidity))
    
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return record_id


def get_history(hours=24):
    """
    Lấy sensor readings trong X giờ gần nhất
    Args:
        hours: số giờ cần lấy data (default 24h)
    Returns:
        List of dicts: [{timestamp, moisture, temp, humidity}, ...]
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Để access columns bằng tên
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT timestamp, soil_moisture, temperature, humidity
        FROM sensor_readings
        WHERE timestamp >= datetime('now', '-' || ? || ' hours')
        ORDER BY timestamp ASC
    ''', (hours,))
    
    rows = cursor.fetchall()
    conn.close()
    
    # Convert sang list of dicts
    history = []
    for row in rows:
        history.append({
            'timestamp': row['timestamp'],
            'moisture': row['soil_moisture'],
            'temperature': row['temperature'],
            'humidity': row['humidity']
        })
    
    return history


def get_latest_reading():
    """
    Lấy sensor reading mới nhất
    Returns:
        Dict: {timestamp, moisture, temp, humidity} hoặc None
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT timestamp, soil_moisture, temperature, humidity
        FROM sensor_readings
        ORDER BY timestamp DESC
        LIMIT 1
    ''')
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'timestamp': row['timestamp'],
            'moisture': row['soil_moisture'],
            'temperature': row['temperature'],
            'humidity': row['humidity']
        }
    return None


def insert_watering_event(action, source='auto'):
    """
    Log watering event vào database
    Args:
        action: 'on' hoặc 'off'
        source: 'auto' (AI) hoặc 'manual' (user control)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO watering_history (action, source)
        VALUES (?, ?)
    ''', (action, source))
    
    conn.commit()
    conn.close()


def insert_command(command):
    """
    Thêm manual command vào queue (để ESP32 poll)
    Args:
        command: 'on' hoặc 'off'
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO commands (command, executed)
        VALUES (?, 0)
    ''', (command,))
    
    conn.commit()
    conn.close()


def get_pending_command():
    """
    Lấy command chưa execute (cho ESP32 poll)
    Returns:
        Dict: {id, command} hoặc None
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, command
        FROM commands
        WHERE executed = 0
        ORDER BY timestamp ASC
        LIMIT 1
    ''')
    
    row = cursor.fetchone()
    
    if row:
        # Mark as executed
        cursor.execute('UPDATE commands SET executed = 1 WHERE id = ?', (row['id'],))
        conn.commit()
        conn.close()
        return {'id': row['id'], 'command': row['command']}
    
    conn.close()
    return None


# Test script - chạy file này trực tiếp để init database
if __name__ == '__main__':
    print("🔧 Initializing database...")
    init_db()
    
    print("\n🧪 Testing insert sensor data...")
    record_id = insert_sensor_data(45.5, 28.3, 65.2)
    print(f"✅ Inserted record ID: {record_id}")
    
    print("\n📊 Testing get latest reading...")
    latest = get_latest_reading()
    print(f"Latest reading: {latest}")
    
    print("\n📈 Testing get history...")
    history = get_history(hours=1)
    print(f"History count: {len(history)} records")
    
    print("\n✅ Database tests completed!")
