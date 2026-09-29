"""
AI Model Training - Train RandomForest classifier để quyết định tưới nước
Input: soil_moisture, temperature, humidity
Output: should_water (0 = không tưới, 1 = cần tưới)
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
import pickle
import os

# Paths
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'data', 'model.pkl')
SCALER_PATH = os.path.join(os.path.dirname(__file__), 'data', 'scaler.pkl')


def generate_synthetic_data(n_samples=500):
    """
    Generate synthetic dataset để train model
    Logic:
    - soil_moisture < 30% và temp > 25°C → cần tưới (1)
    - soil_moisture > 60% → không cần tưới (0)
    - 30-60%: tùy thuộc temp và humidity
    """
    np.random.seed(42)
    
    data = []
    
    for _ in range(n_samples):
        # Random sensor values
        soil_moisture = np.random.uniform(10, 90)  # 10-90%
        temperature = np.random.uniform(20, 35)    # 20-35°C
        humidity = np.random.uniform(40, 90)       # 40-90%
        
        # Decision logic (giống rule-based expert system)
        if soil_moisture < 30:
            # Đất khô
            if temperature > 25:
                should_water = 1  # Khô + nóng → tưới
            else:
                should_water = 1 if np.random.rand() > 0.3 else 0  # 70% tưới
        elif soil_moisture > 60:
            # Đất ẩm
            should_water = 0  # Không cần tưới
        else:
            # Đất trung bình (30-60%)
            if temperature > 30 and humidity < 50:
                should_water = 1  # Nóng + khô không khí → tưới
            elif temperature < 23:
                should_water = 0  # Mát → không tưới
            else:
                # Random với probability
                prob = (60 - soil_moisture) / 30  # Càng khô càng cần tưới
                should_water = 1 if np.random.rand() < prob else 0
        
        data.append({
            'soil_moisture': soil_moisture,
            'temperature': temperature,
            'humidity': humidity,
            'should_water': should_water
        })
    
    df = pd.DataFrame(data)
    print(f"✅ Generated {n_samples} samples")
    print(f"   - Need watering: {df['should_water'].sum()} samples")
    print(f"   - No watering: {(1-df['should_water']).sum()} samples")
    
    return df


def train_model(df):
    """
    Train RandomForest classifier
    Args:
        df: DataFrame với columns [soil_moisture, temperature, humidity, should_water]
    Returns:
        model, scaler, accuracy
    """
    # Features và target
    X = df[['soil_moisture', 'temperature', 'humidity']].values
    y = df['should_water'].values
    
    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"\n📊 Dataset split:")
    print(f"   - Train: {len(X_train)} samples")
    print(f"   - Test: {len(X_test)} samples")
    
    # Standardize features (chuẩn hóa để model học tốt hơn)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train RandomForest
    print("\n🤖 Training RandomForest model...")
    model = RandomForestClassifier(
        n_estimators=100,      # 100 trees
        max_depth=10,          # Giới hạn depth tránh overfit
        random_state=42,
        n_jobs=-1              # Dùng tất cả CPU cores
    )
    
    model.fit(X_train_scaled, y_train)
    
    # Evaluate
    y_pred_train = model.predict(X_train_scaled)
    y_pred_test = model.predict(X_test_scaled)
    
    train_acc = accuracy_score(y_train, y_pred_train)
    test_acc = accuracy_score(y_test, y_pred_test)
    
    print(f"\n✅ Training completed!")
    print(f"   - Train accuracy: {train_acc*100:.2f}%")
    print(f"   - Test accuracy: {test_acc*100:.2f}%")
    
    print(f"\n📋 Classification Report:")
    print(classification_report(y_test, y_pred_test, 
                                target_names=['No water', 'Water']))
    
    # Feature importance
    feature_names = ['soil_moisture', 'temperature', 'humidity']
    importances = model.feature_importances_
    print(f"\n🔍 Feature Importance:")
    for name, importance in zip(feature_names, importances):
        print(f"   - {name}: {importance*100:.2f}%")
    
    return model, scaler, test_acc


def save_model(model, scaler):
    """
    Save model và scaler ra file .pkl
    """
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    
    with open(SCALER_PATH, 'wb') as f:
        pickle.dump(scaler, f)
    
    print(f"\n💾 Model saved to: {MODEL_PATH}")
    print(f"💾 Scaler saved to: {SCALER_PATH}")


def test_predictions(model, scaler):
    """
    Test model với vài examples
    """
    print("\n🧪 Testing predictions:")
    
    test_cases = [
        {'moisture': 25, 'temp': 30, 'humidity': 50, 'expected': 'Water'},
        {'moisture': 70, 'temp': 25, 'humidity': 70, 'expected': 'No water'},
        {'moisture': 45, 'temp': 28, 'humidity': 60, 'expected': '?'},
        {'moisture': 20, 'temp': 22, 'humidity': 80, 'expected': 'Water'},
    ]
    
    for case in test_cases:
        X = np.array([[case['moisture'], case['temp'], case['humidity']]])
        X_scaled = scaler.transform(X)
        prediction = model.predict(X_scaled)[0]
        confidence = model.predict_proba(X_scaled)[0]
        
        result = 'Water' if prediction == 1 else 'No water'
        conf_value = confidence[prediction] * 100
        
        print(f"   Moisture: {case['moisture']}%, Temp: {case['temp']}°C, "
              f"Humidity: {case['humidity']}%")
        print(f"   → Prediction: {result} (confidence: {conf_value:.1f}%)")
        print(f"   → Expected: {case['expected']}\n")


if __name__ == '__main__':
    print("🌱 Smart Watering AI - Model Training\n")
    print("="*50)
    
    # Step 1: Generate data
    print("\n[1/4] Generating synthetic dataset...")
    df = generate_synthetic_data(n_samples=500)
    
    # Step 2: Train model
    print("\n[2/4] Training model...")
    model, scaler, accuracy = train_model(df)
    
    # Step 3: Save model
    print("\n[3/4] Saving model...")
    save_model(model, scaler)
    
    # Step 4: Test predictions
    print("\n[4/4] Testing predictions...")
    test_predictions(model, scaler)
    
    print("\n" + "="*50)
    print("✅ Training completed successfully!")
    print(f"📊 Model accuracy: {accuracy*100:.2f}%")
    print("\n💡 Next steps:")
    print("   1. Run: python app.py")
    print("   2. Server sẽ tự động load model này")
