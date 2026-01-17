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

if __name__ == '__main__':
    print("🚀 Starting Trash Classification Flask App...")
    print(f"📷 Camera will save images to: {os.path.abspath(PICTURE_FOLDER)}")
    print(f"🤖 Model loaded from: {MODEL_PATH}")
    app.run(host='0.0.0.0', port=5000, debug=True)
