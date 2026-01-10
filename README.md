# Trash Classification - Can vs Plastic

A deep learning model to classify trash images into **Can** or **Plastic** categories using MobileNetV2. This project includes both a full Keras model for development and a lightweight TFLite model optimized for Raspberry Pi deployment.

## Project Overview

This project uses transfer learning with MobileNetV2 to classify trash items. The model was trained on a balanced dataset.

**Key Features:**
- Binary classification (Can vs Plastic)
- MobileNetV2 backbone with transfer learning
- Data augmentation for balanced training
- Both Keras and TFLite model formats
- Ready for Raspberry Pi deployment

## Requirements

- Python 3.8 or higher
- TensorFlow 2.x
- OpenCV
- NumPy, Pandas, Matplotlib, Seaborn
- scikit-learn

## Getting Started

### Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd trash-classification
```

### Step 2: Create a Virtual Environment

It's highly recommended to use a virtual environment to avoid dependency conflicts.

**On Windows:**
```bash
python -m venv env
env\Scripts\activate
```

**On Mac/Linux:**
```bash
python3 -m venv env
source env/bin/activate
```

### Step 3: Install Dependencies

Once your virtual environment is activated, install all required packages:

```bash
pip install -r requirements.txt
```

This will install:
- tensorflow
- numpy
- matplotlib
- opencv-python

### Step 4: Download the Model

Make sure you have the trained models in the `models/` folder:
- `models/ai-model-fp32.tflite` - Lightweight TFLite model for Raspberry Pi

## Using the Model

### Quick Inference with Jupyter Notebook

Open the inference notebook:

```bash
jupyter notebook inference.ipynb
```

Run the cells to:
1. Load the model
2. Test predictions on sample images
3. TFLite model outputs


### Prediction Function (TFLite Model for Raspberry Pi)

```python
import tensorflow as tf
import cv2
import numpy as np

interpreter = tf.lite.Interpreter(model_path="models/ai-model-fp32.tflite")
interpreter.allocate_tensors()

def predict_image_tflite(interpreter, img_path, class_names):
    img = cv2.imread(img_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_resized = cv2.resize(img_rgb, (224, 224))
    
    img_array = img_resized.astype("float32")
    img_array = np.expand_dims(img_array, axis=0)
    
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    interpreter.set_tensor(input_details[0]['index'], img_array)
    interpreter.invoke()
    
    output_data = interpreter.get_tensor(output_details[0]['index'])
    p = float(output_data[0][0])
    
    if p >= 0.5:
        return class_names[1], p * 100
    else:
        return class_names[0], (1-p) * 100
```

## Deploying to Raspberry Pi

### Requirements for Raspberry Pi

```bash
pip install tensorflow-lite opencv-python-headless numpy
```

### Transfer the Model

Copy the TFLite model to your Raspberry Pi:

```bash
scp models/ai-model-fp32.tflite pi@<raspberry-pi-ip>:~/trash-classifier/
```

### Running on Raspberry Pi

Use the TFLite prediction function shown above. The TFLite model is:
- **Smaller file size** (optimized for embedded devices)
- **Faster inference** (designed for edge computing)
- **Same accuracy** as the full Keras model


### Class Order

The class names must match the training order:
```python
class_names = ['Can', 'Plastic']  # Alphabetical order from folder names
```

- Index 0 = Can
- Index 1 = Plastic

The model outputs a single probability value `p` representing **P(Plastic)**.

## Project Structure

```
trash-classification/
├── inference.ipynb           # Inference notebook with examples
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── models/
│   ├── ai-model.keras        # Full Keras model
│   └── ai-model-fp32.tflite  # TFLite model for Raspberry Pi
├── env/                      # Virtual environment (gitignored)
└── test_images/              # Sample images for testing
    ├── AluCan61.jpg
    ├── Plastic1.jpg
    └── ...
```

## Model Details

- **Architecture:** MobileNetV2 (pretrained on ImageNet)
- **Input Size:** 224x224x3
- **Output:** Single sigmoid neuron (binary classification)
- **Training Strategy:**
  - Stage 1: Freeze base model, train classifier head (10 epochs)
  - Stage 2: Fine-tune last 50 layers (10 epochs)
- **Data Augmentation:** Flips, rotations, brightness/contrast adjustments