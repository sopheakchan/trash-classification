from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import tensorflow as tf
import cv2
import numpy as np
import os
import requests # For talking to Next.js
import qrcode   # For generating QR codes
import time
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
# REPLACE THIS with your actual computer's local IP address (e.g., http://192.168.1.5:3000)
# Do NOT use 'localhost' if the Pi and Next.js are on different devices.
NEXTJS_API_URL = os.getenv("NEXTJS_API_URL")
SECRET_KEY = os.getenv("SECRET_KEY")

# Global variables
session_data = {
    'can_count': 0,
    'plastic_count': 0,
    'is_active': False
}

# Load Model
MODEL_PATH = 'models/ai-model-fp32.tflite'
PICTURE_FOLDER = 'static' # Changed to static so HTML can see the images
os.makedirs(PICTURE_FOLDER, exist_ok=True)

print("Loading Model...")
interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
CLASS_NAMES = ['Can', 'Plastic']

# Global Camera Object
camera = None

def get_camera():
    """Get the global camera instance, or open it if closed"""
    global camera
    if camera is None or not camera.isOpened():
        # Try indices 0, 1, 2
        for i in range(3):
            temp_cam = cv2.VideoCapture(i)
            if temp_cam.isOpened():
                camera = temp_cam
                # Set lower resolution for faster processing
                camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                # Warm up camera
                for _ in range(10): camera.read()
                print(f"✅ Camera opened on index {i}")
                return camera
    return camera

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_session():
    """Start session AND open camera to be ready"""
    global session_data
    session_data = { 'can_count': 0, 'plastic_count': 0, 'is_active': True }
    
    # Pre-warm the camera so the first capture is fast
    cam = get_camera()
    if not cam:
        return jsonify({'status': 'error', 'message': 'Camera not found'}), 500

    return jsonify({'status': 'success', 'message': 'Session started'})

@app.route('/capture', methods=['POST'])
def capture_and_predict():
    if not session_data['is_active']:
        return jsonify({'status': 'error', 'message': 'Session not active'}), 400
    
    try:
        cam = get_camera()
        if not cam: return jsonify({'status': 'error', 'message': 'Camera failed'}), 500
        
        # FIX LAG: Clear the buffer!
        # Cameras buffer ~5 frames. If we read just once, we get an old frame.
        # We read 5 times quickly to get to the "current" moment.
        for _ in range(5): 
            cam.read()
            
        ret, frame = cam.read()
        if not ret: return jsonify({'status': 'error', 'message': 'Capture failed'}), 500

        # Save for debugging/display
        img_path = os.path.join(PICTURE_FOLDER, "detected.jpg")
        cv2.imwrite(img_path, frame)

        # Preprocess & Predict
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, (224, 224))
        input_data = np.expand_dims(img_resized.astype("float32"), axis=0)
        
        interpreter.set_tensor(input_details[0]['index'], input_data)
        interpreter.invoke()
        output_data = interpreter.get_tensor(output_details[0]['index'])
        
        # Logic: Assuming output is [P(Plastic)]
        p = float(output_data[0][0])
        if p >= 0.5:
            predicted_class = 'Plastic'
            confidence = p
            session_data['plastic_count'] += 1
        else:
            predicted_class = 'Can'
            confidence = 1 - p
            session_data['can_count'] += 1

        return jsonify({
            'status': 'success',
            'prediction': predicted_class,
            'confidence': round(confidence * 100, 2),
            'can_count': session_data['can_count'],
            'plastic_count': session_data['plastic_count'],
            'image_url': f'/static/detected.jpg?t={time.time()}' # Prevent caching
        })

    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/finish', methods=['POST'])
def finish_session():
    """Send data to Next.js, get URL, generate QR"""
    global session_data, camera
    
    if session_data['can_count'] == 0 and session_data['plastic_count'] == 0:
        return jsonify({'status': 'error', 'message': 'No items recycled yet!'})

    try:
        # 1. Talk to Next.js Backend
        payload = {
            "plastic": session_data['plastic_count'],
            "cans": session_data['can_count'],
            "binId": "PI_BIN_001",
            "secretKey": SECRET_KEY
        }
        
        # Send Request (Timeout ensures we don't hang forever)
        response = requests.post(NEXTJS_API_URL, json=payload, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            qr_url = data.get('qrUrl') # This is the link: http://site/claim/xyz...
            
            # 2. Generate QR Code Image
            qr = qrcode.make(qr_url)
            qr_path = os.path.join(PICTURE_FOLDER, "qr_code.png")
            qr.save(qr_path)
            
            # 3. Stop local session
            session_data['is_active'] = False
            if camera: camera.release() # Release camera now
            
            return jsonify({
                'status': 'success',
                'qr_image_url': f'/static/qr_code.png?t={time.time()}',
                'claim_url': qr_url
            })
        else:
            return jsonify({'status': 'error', 'message': 'Backend rejected transaction'}), 500

    except Exception as e:
        print(f"Network Error: {e}")
        # FALLBACK: If internet fails, just show the counts so user can take a photo
        return jsonify({'status': 'error', 'message': 'Could not connect to server. Check internet.'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)