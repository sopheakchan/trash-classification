from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import tensorflow as tf
import cv2
import numpy as np
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# Global variables
session_data = {
    'can_count': 0,
    'plastic_count': 0,
    'is_active': False
}

# Load TFLite model
MODEL_PATH = 'models/ai-model-fp32.tflite'
PICTURE_FOLDER = 'Picture'

# Ensure Picture folder exists
os.makedirs(PICTURE_FOLDER, exist_ok=True)

# Initialize TFLite interpreter
interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()

# Get input and output details
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Class names
CLASS_NAMES = ['Can', 'Plastic']

# Camera object (will be initialized when needed)
camera = None

def initialize_camera():
    """Initialize the camera"""
    global camera
    if camera is None or not camera.isOpened():
        # Try multiple camera indices
        for cam_idx in [1, 0, 2]:  # Try Logitech first (1), then default (0), then (2)
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
        
        # If we get here, no camera worked
        camera = None
        print("    No working camera found!")
    return camera

def release_camera():
    """Release the camera"""
    global camera
    if camera is not None and camera.isOpened():
        camera.release()
        camera = None

def predict_image_tflite(image_array):
    """
    Predict using TFLite model
    image_array: numpy array of shape (224, 224, 3) in [0, 255] range
    """
    # Prepare image for model - NO normalization! Model has preprocessing built-in
    img_array = image_array.astype("float32")
    img_array = np.expand_dims(img_array, axis=0)
    
    # Set input tensor
    interpreter.set_tensor(input_details[0]['index'], img_array)
    
    # Run inference
    interpreter.invoke()
    
    # Get output - single probability value p = P(Plastic | image)
    output_data = interpreter.get_tensor(output_details[0]['index'])
    p = float(output_data[0][0])
    
    # Interpret: p >= 0.5 means Plastic, p < 0.5 means Can
    if p >= 0.5:
        predicted_class = CLASS_NAMES[1]  # Plastic
        confidence = p
    else:
        predicted_class = CLASS_NAMES[0]  # Can
        confidence = 1 - p
    
    return predicted_class, confidence

@app.route('/')
def index():
    """Serve the main UI"""
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_session():
    """Start a new classification session"""
    global session_data
    session_data = {
        'can_count': 0,
        'plastic_count': 0,
        'is_active': True
    }
    return jsonify({
        'status': 'success',
        'message': 'Session started',
        'data': session_data
    })

@app.route('/capture', methods=['POST'])
def capture_and_predict():
    """Capture image from camera and predict"""
    global session_data
    
    if not session_data['is_active']:
        return jsonify({
            'status': 'error',
            'message': 'Session not active. Please start first.'
        }), 400
    
    try:
        print(" Starting capture...")
        
        # Initialize camera
        print(" Initializing camera...")
        cam = initialize_camera()
        
        if not cam.isOpened():
            print(" Camera failed to open")
            return jsonify({
                'status': 'error',
                'message': 'Failed to open camera'
            }), 500
        
        print(" Camera opened successfully")
        
        # Capture image
        print(" Capturing frame...")
        ret, frame = cam.read()
        
        if not ret:
            print(" Failed to capture frame")
            return jsonify({
                'status': 'error',
                'message': 'Failed to capture image'
            }), 500
        
        print(f" Frame captured: {frame.shape}")
        
        # Save original image (overwrite each time)
        image_filename = "detected.jpg"
        image_path = os.path.join(PICTURE_FOLDER, image_filename)
        cv2.imwrite(image_path, frame)
        print(f" Image saved to: {image_path}")
        
        # Preprocess for prediction
        print(" Preprocessing image...")
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, (224, 224))
        
        # Predict
        print(" Running prediction...")
        predicted_class, confidence = predict_image_tflite(img_resized)
        print(f" Prediction: {predicted_class} ({confidence*100:.2f}%)")
        
        # Update counts
        if predicted_class == 'Can':
            session_data['can_count'] += 1
        else:
            session_data['plastic_count'] += 1
        
        return jsonify({
            'status': 'success',
            'prediction': predicted_class,
            'confidence': round(confidence * 100, 2),
            'can_count': session_data['can_count'],
            'plastic_count': session_data['plastic_count'],
            'image_saved': image_filename
        })
        
    except Exception as e:
        print(f" ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/stop', methods=['POST'])
def stop_session():
    """Stop the session and return final scores"""
    global session_data
    session_data['is_active'] = False
    release_camera()
    
    final_scores = {
        'can_count': session_data['can_count'],
        'plastic_count': session_data['plastic_count']
    }
    
    return jsonify({
        'status': 'success',
        'message': 'Session stopped',
        'final_scores': final_scores
    })

@app.route('/get_scores', methods=['GET'])
def get_scores():
    """Get current scores"""
    return jsonify({
        'can_count': session_data['can_count'],
        'plastic_count': session_data['plastic_count'],
        'is_active': session_data['is_active']
    })

# ===== API ENDPOINTS FOR RASPBERRY PI =====

@app.route('/api/status', methods=['GET'])
def api_status():
    """Check if server is online - Raspberry Pi uses this to test connection"""
    return jsonify({
        'status': 'online',
        'session_active': session_data['is_active'],
        'can_count': session_data['can_count'],
        'plastic_count': session_data['plastic_count'],
        'message': 'Laptop server is ready'
    })

@app.route('/capture_from_pi', methods=['POST'])
def capture_from_pi():
    """
    NEW ENDPOINT: Web UI calls this to use Pi camera!
    Orchestrates: Pi camera capture → Laptop AI → Pi motor control
    
    Flow:
    1. Call Pi's /api/capture to get image
    2. Classify image on laptop
    3. Call Pi's /api/motor to activate motor
    4. Return result to web UI
    """
    global session_data
    import requests
    
    if not session_data['is_active']:
        return jsonify({
            'status': 'error',
            'message': 'Session not active. Please start first.'
        }), 400
    
    try:
        # Get Pi IP from request or use default
        data = request.get_json() or {}
        pi_ip = data.get('pi_ip', '192.168.1.101')  # Default Pi IP
        pi_url = f"http://{pi_ip}:5001"
        
        print(f"🍓 Requesting image from Pi at {pi_url}")
        
        # Step 1: Request image from Raspberry Pi
        capture_response = requests.get(
            f"{pi_url}/api/capture",
            timeout=10
        )
        
        if capture_response.status_code != 200:
            return jsonify({
                'status': 'error',
                'message': f'Pi camera failed: {capture_response.text}'
            }), 500
        
        capture_data = capture_response.json()
        
        if capture_data['status'] != 'success':
            return jsonify({
                'status': 'error',
                'message': f"Pi error: {capture_data.get('message', 'Unknown')}"
            }), 500
        
        image_b64 = capture_data['image']
        print("   ✅ Received image from Pi")
        
        # Step 2: Decode and classify image (SAME as /api/classify endpoint!)
        import base64
        image_bytes = base64.b64decode(image_b64)
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({
                'status': 'error',
                'message': 'Failed to decode image from Pi'
            }), 500
        
        # Save image
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        image_filename = f"pi_ui_{timestamp}.jpg"
        image_path = os.path.join(PICTURE_FOLDER, image_filename)
        cv2.imwrite(image_path, frame)
        print(f"   💾 Saved: {image_filename}")
        
        # Preprocess and classify
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, (224, 224))
        predicted_class, confidence = predict_image_tflite(img_resized)
        
        # Update counts
        if predicted_class == 'Can':
            session_data['can_count'] += 1
        else:
            session_data['plastic_count'] += 1
        
        print(f"   🤖 Prediction: {predicted_class} ({confidence*100:.2f}%)")
        print(f"   📊 Counts - Can: {session_data['can_count']}, Plastic: {session_data['plastic_count']}")
        
        # Step 3: Tell Pi to activate motor
        motor_response = requests.post(
            f"{pi_url}/api/motor",
            json={'prediction': predicted_class.lower()},
            timeout=5
        )
        
        motor_message = "Motor request sent"
        if motor_response.status_code == 200:
            motor_data = motor_response.json()
            motor_message = motor_data.get('message', 'Motor activated')
            print(f"   🔧 {motor_message}")
        else:
            print(f"   ⚠️ Motor activation failed: {motor_response.text}")
        
        # Step 4: Return result to web UI
        return jsonify({
            'status': 'success',
            'prediction': predicted_class,
            'confidence': round(confidence * 100, 2),
            'can_count': session_data['can_count'],
            'plastic_count': session_data['plastic_count'],
            'image_saved': image_filename,
            'motor_status': motor_message,
            'source': 'raspberry_pi'
        })
        
    except requests.exceptions.Timeout:
        return jsonify({
            'status': 'error',
            'message': 'Timeout connecting to Raspberry Pi. Check network and Pi IP.'
        }), 500
    except requests.exceptions.ConnectionError:
        return jsonify({
            'status': 'error',
            'message': 'Cannot connect to Raspberry Pi. Check if pi_server.py is running.'
        }), 500
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/api/classify', methods=['POST'])
def api_classify():
    """
    Receive image from Raspberry Pi and return classification
    Raspberry Pi sends: {"image": "base64_encoded_jpeg"}
    Returns: {"status": "success", "prediction": "can"/"plastic", "confidence": 95.2}
    """
    global session_data
    
    try:
        # Get JSON data from Raspberry Pi
        data = request.get_json()
        
        if not data or 'image' not in data:
            return jsonify({
                'status': 'error',
                'message': 'No image data provided. Expected {"image": "base64..."}'
            }), 400
        
        print("📡 Received image from Raspberry Pi")
        
        # Decode base64 image
        import base64
        image_b64 = data['image']
        image_bytes = base64.b64decode(image_b64)
        
        # Convert bytes to numpy array (same as laptop camera capture!)
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({
                'status': 'error',
                'message': 'Failed to decode image'
            }), 400
        
        # Save image for logging
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        image_filename = f"pi_capture_{timestamp}.jpg"
        image_path = os.path.join(PICTURE_FOLDER, image_filename)
        cv2.imwrite(image_path, frame)
        print(f"   💾 Saved: {image_filename}")
        
        # Preprocess (EXACTLY same as /capture endpoint!)
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, (224, 224))
        
        # Run AI model
        predicted_class, confidence = predict_image_tflite(img_resized)
        
        # Update counts
        if predicted_class == 'Can':
            session_data['can_count'] += 1
        else:
            session_data['plastic_count'] += 1
        
        print(f"   🤖 Prediction: {predicted_class} ({confidence*100:.2f}%)")
        print(f"   📊 Counts - Can: {session_data['can_count']}, Plastic: {session_data['plastic_count']}")
        
        # Return result to Raspberry Pi
        return jsonify({
            'status': 'success',
            'prediction': predicted_class.lower(),  # 'can' or 'plastic'
            'confidence': round(confidence * 100, 2),
            'can_count': session_data['can_count'],
            'plastic_count': session_data['plastic_count'],
            'timestamp': timestamp
        })
        
    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }), 500

if __name__ == '__main__':
    print("🚀 Starting Trash Classification Flask App...")
    print(f"📷 Camera will save images to: {os.path.abspath(PICTURE_FOLDER)}")
    print(f"🤖 Model loaded from: {MODEL_PATH}")
    app.run(host='0.0.0.0', port=5000, debug=True)
