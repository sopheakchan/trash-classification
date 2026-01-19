"""
Raspberry Pi Flask Server
Lightweight Flask API running on Pi - handles camera and motors only
Laptop calls this API to trigger capture and motor control
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import cv2
import base64
import numpy as np
import RPi.GPIO as GPIO
import time

app = Flask(__name__)
CORS(app)

# ===== CONFIGURATION =====
MOTOR_CAN_PIN = 17      # GPIO pin for Can motor
MOTOR_PLASTIC_PIN = 27  # GPIO pin for Plastic motor
MOTOR_TIME_CAN = 1.0    # Can motor run time (seconds) - 45 degrees
MOTOR_TIME_PLASTIC = 2.0  # Plastic motor run time (seconds) - 90 degrees

# ===== GLOBAL STATE =====
camera = None
gpio_initialized = False

def initialize_gpio():
    """Initialize GPIO pins for motors"""
    global gpio_initialized
    if not gpio_initialized:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(MOTOR_CAN_PIN, GPIO.OUT)
        GPIO.setup(MOTOR_PLASTIC_PIN, GPIO.OUT)
        # Make sure motors are off
        GPIO.output(MOTOR_CAN_PIN, GPIO.LOW)
        GPIO.output(MOTOR_PLASTIC_PIN, GPIO.LOW)
        gpio_initialized = True
        print("✅ GPIO initialized")

def initialize_camera():
    """Initialize USB camera (Logitech)"""
    global camera
    if camera is None or not camera.isOpened():
        # Try multiple camera indices
        for cam_idx in [0, 1, 2]:
            print(f"   Trying camera index {cam_idx}...")
            camera = cv2.VideoCapture(cam_idx)
            if camera.isOpened():
                # Test if we can actually read a frame
                ret, test_frame = camera.read()
                if ret:
                    print(f"   ✅ Camera {cam_idx} works!")
                    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    return camera
                else:
                    camera.release()
            else:
                camera.release()
        
        camera = None
        print("    ❌ No working camera found!")
    return camera

def release_camera():
    """Release camera resource"""
    global camera
    if camera is not None and camera.isOpened():
        camera.release()
        camera = None

def activate_motor(prediction):
    """
    Activate motor based on prediction
    prediction: 'can' or 'plastic'
    """
    try:
        initialize_gpio()
        
        if prediction.lower() == 'can':
            print(f"🔧 Activating CAN motor (Pin {MOTOR_CAN_PIN}) for {MOTOR_TIME_CAN}s")
            GPIO.output(MOTOR_CAN_PIN, GPIO.HIGH)
            time.sleep(MOTOR_TIME_CAN)
            GPIO.output(MOTOR_CAN_PIN, GPIO.LOW)
            return f"Can motor activated for {MOTOR_TIME_CAN}s (45°)"
            
        elif prediction.lower() == 'plastic':
            print(f"🔧 Activating PLASTIC motor (Pin {MOTOR_PLASTIC_PIN}) for {MOTOR_TIME_PLASTIC}s")
            GPIO.output(MOTOR_PLASTIC_PIN, GPIO.HIGH)
            time.sleep(MOTOR_TIME_PLASTIC)
            GPIO.output(MOTOR_PLASTIC_PIN, GPIO.LOW)
            return f"Plastic motor activated for {MOTOR_TIME_PLASTIC}s (90°)"
            
        else:
            return f"Unknown prediction: {prediction}"
            
    except Exception as e:
        print(f"❌ Motor error: {str(e)}")
        return f"Motor error: {str(e)}"

# ===== API ENDPOINTS =====

@app.route('/api/status', methods=['GET'])
def status():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'message': 'Raspberry Pi server is ready',
        'camera_available': camera is not None and camera.isOpened(),
        'gpio_initialized': gpio_initialized
    })

@app.route('/api/capture', methods=['GET'])
def capture():
    """
    Capture image from USB camera and return as base64
    Returns: {"status": "success", "image": "base64_encoded_jpeg"}
    """
    try:
        print("📷 Capture request received")
        
        # Initialize camera
        cam = initialize_camera()
        
        if cam is None or not cam.isOpened():
            return jsonify({
                'status': 'error',
                'message': 'Camera not available'
            }), 500
        
        # Capture frame
        ret, frame = cam.read()
        
        if not ret:
            return jsonify({
                'status': 'error',
                'message': 'Failed to capture image'
            }), 500
        
        print(f"   ✅ Captured frame: {frame.shape}")
        
        # Encode to JPEG
        ret_encode, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        if not ret_encode:
            return jsonify({
                'status': 'error',
                'message': 'Failed to encode image'
            }), 500
        
        # Convert to base64
        image_b64 = base64.b64encode(buffer).decode('utf-8')
        
        print(f"   📦 Encoded to base64 ({len(image_b64)} chars)")
        
        return jsonify({
            'status': 'success',
            'image': image_b64
        })
        
    except Exception as e:
        print(f"❌ Capture error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/motor', methods=['POST'])
def motor():
    """
    Activate motor based on classification
    Expects: {"prediction": "can" or "plastic"}
    Returns: {"status": "success", "message": "Motor activated"}
    """
    try:
        data = request.get_json()
        
        if not data or 'prediction' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing prediction. Expected {"prediction": "can"/"plastic"}'
            }), 400
        
        prediction = data['prediction']
        print(f"🎯 Motor request: {prediction}")
        
        result = activate_motor(prediction)
        
        return jsonify({
            'status': 'success',
            'message': result,
            'prediction': prediction
        })
        
    except Exception as e:
        print(f"❌ Motor endpoint error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/test', methods=['GET'])
def test():
    """
    Full test: capture + motor test (no classification)
    For testing camera and motors work
    """
    try:
        # Test camera
        cam = initialize_camera()
        if cam is None:
            return jsonify({
                'status': 'error',
                'message': 'Camera test failed'
            }), 500
        
        ret, frame = cam.read()
        if not ret:
            return jsonify({
                'status': 'error',
                'message': 'Camera capture failed'
            }), 500
        
        # Test GPIO
        initialize_gpio()
        
        return jsonify({
            'status': 'success',
            'message': 'Camera and GPIO ready',
            'camera_shape': list(frame.shape),
            'gpio_initialized': gpio_initialized
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Cleanup on shutdown
@app.teardown_appcontext
def cleanup(error):
    """Cleanup resources when app shuts down"""
    release_camera()
    if gpio_initialized:
        GPIO.cleanup()

if __name__ == '__main__':
    print("🍓 Starting Raspberry Pi Flask Server...")
    print(f"📷 USB Camera (Logitech) will be auto-detected")
    print(f"🔧 Motors: Can=Pin{MOTOR_CAN_PIN}, Plastic=Pin{MOTOR_PLASTIC_PIN}")
    print(f"⏱️  Timing: Can={MOTOR_TIME_CAN}s, Plastic={MOTOR_TIME_PLASTIC}s")
    print()
    print("🌐 API Endpoints:")
    print("   GET  /api/status  - Health check")
    print("   GET  /api/capture - Capture image from camera")
    print("   POST /api/motor   - Activate motor")
    print("   GET  /api/test    - Test camera + GPIO")
    print()
    
    # Run on all interfaces so laptop can access it
    app.run(host='0.0.0.0', port=5001, debug=True)
