# 🎯 COMPLETE SETUP GUIDE - Laptop + Raspberry Pi

## 📋 **WHAT GOES WHERE?**

### 💻 **LAPTOP - Keep EVERYTHING**

```
C:\Users\chans\Documents\Sopheak\Rupp\IOT\trash-classification\
├── app.py ✅ KEEP - Flask server + AI model
├── templates/index.html ✅ KEEP - Web UI  
├── models/ai-model-fp32.tflite ✅ KEEP - AI model
├── requirements.txt ✅ KEEP - Laptop dependencies
├── Picture/ ✅ KEEP - Saves images
├── env/ ✅ KEEP - Virtual environment
└── raspberry-pi/ ⚠️ DON'T RUN (for Pi only)
```

### 🔧 **RASPBERRY PI - Clone only raspberry-pi/ folder**

```
~/trash-classification/raspberry-pi/
├── pi_controller.py ✅ Main script
├── config.py ✅ Configuration (EDIT THIS!)
├── requirements.txt ✅ Lightweight deps
└── README.md ✅ Pi setup guide
```

---

## ⚡ **3-STEP SETUP**

### **STEP 1: LAPTOP** (5 minutes) ✅

#### 1.1 Find Your Laptop IP

```powershell
ipconfig

# Look for:
Wireless LAN adapter Wi-Fi:
   IPv4 Address. . . . . . . : 192.168.1.XXX
                               ↑ WRITE THIS DOWN!
```

**Example:** `192.168.1.150` (yours will be different!)

#### 1.2 Run Flask Server

```powershell
# Navigate to project
cd C:\Users\chans\Documents\Sopheak\Rupp\IOT\trash-classification

# Activate virtual environment
env\Scripts\activate

# Run Flask
python app.py

# Should see:
# 🚀 Starting Trash Classification Flask App...
# * Running on http://0.0.0.0:5000
```

✅ **Keep Flask running!**

#### 1.3 Test Web UI

```
Open browser: http://localhost:5000
Click START → Click CAPTURE
Should work with your laptop camera!
```

---

### **STEP 2: RASPBERRY PI** (10 minutes) 🔧

#### 2.1 Transfer Files

```bash
# Clone entire repo
cd ~
git clone https://github.com/YOUR_USERNAME/trash-classification.git
cd trash-classification/raspberry-pi
```

#### 2.2 Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate

# Install
pip install -r requirements.txt
```

**If errors:**
```bash
sudo apt update
sudo apt install python3-opencv python3-rpi.gpio
```

#### 2.3 Configure Laptop IP

```bash
nano config.py

# Change this line:
LAPTOP_IP = '192.168.1.100'  # ⚠️ Use YOUR laptop IP from Step 1.1!

# Example:
LAPTOP_IP = '192.168.1.150'

# Save: Ctrl+X, Y, Enter
```

#### 2.4 Plug in Logitech USB Camera

```bash
# Check if detected
ls /dev/video*

# Should show: /dev/video0 or /dev/video1
```

#### 2.5 Test Connection

```bash
# Make sure laptop Flask is running!
python pi_controller.py test

# Expected:
# ✅ SUCCESS: Raspberry Pi can communicate with laptop!
#    Laptop API: http://192.168.1.150:5000
```

---

### **STEP 3: TEST TOGETHER** (2 minutes) 🎉

#### On Raspberry Pi:

```bash
python pi_controller.py once
```

**Expected flow:**

```
📷 Setting up USB camera...
   Trying camera index 0...
   ✅ Camera 0 works!
📸 Capturing image...
   Frame captured: (480, 640, 3)
✅ Image encoded (85432 bytes)
📡 Sending to laptop: http://192.168.1.150:5000/api/classify
✅ Laptop response received

🤖 PREDICTION: PLASTIC
   Confidence: 95.2%
   Total counts - Can: 0, Plastic: 1
🔄 Activating plastic motor...
   Motor running for 2.0 seconds (90°)
✅ Plastic motor completed

✅ CLASSIFICATION COMPLETE!
```

#### On Laptop Browser:

Web UI updates automatically:
```
Can: 0    Plastic: 1 ← Updated!
```

---

## 🔄 **HOW IT WORKS - COMPLETE FLOW**

```
┌──────────────────────────────────────────────────────────────┐
│  STEP 1: USER CLICKS "CAPTURE" ON WEB UI                     │
│  Browser → Laptop Flask                                      │
└────────────┬─────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 2: RASPBERRY PI CAPTURES IMAGE                         │
│  - Logitech USB camera captures photo                        │
│  - cv2.VideoCapture(0).read()                               │
│  - Encode to JPEG → base64 string                           │
└────────────┬─────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 3: PI SENDS TO LAPTOP VIA WIFI                         │
│  POST http://192.168.1.150:5000/api/classify                │
│  Body: {"image": "base64_encoded_jpeg_string..."}            │
└────────────┬─────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 4: LAPTOP PROCESSES (AI)                               │
│  1. Decode base64 → numpy array                              │
│  2. Preprocess: BGR→RGB, resize to 224x224                  │
│  3. Run TFLite model (heavy AI processing!)                  │
│  4. Get prediction: "plastic" with 95.2% confidence          │
│  5. Increment plastic_count                                  │
└────────────┬─────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 5: LAPTOP RETURNS RESULT TO PI                         │
│  Response: {                                                 │
│    "status": "success",                                      │
│    "prediction": "plastic",                                  │
│    "confidence": 95.2,                                       │
│    "can_count": 0,                                           │
│    "plastic_count": 1                                        │
│  }                                                           │
└────────────┬─────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 6: RASPBERRY PI ACTIVATES MOTOR                        │
│  - Prediction = "plastic"                                    │
│  - Turn on GPIO pin 27 (Plastic motor)                      │
│  - Motor runs for 2.0 seconds (90° rotation)                │
│  - Item drops into plastic bin                              │
│  - Turn off motor, turn off LED                             │
└────────────┬─────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 7: LAPTOP UPDATES WEB UI                               │
│  - Session data updated (plastic_count = 1)                  │
│  - Browser refreshes automatically                           │
└────────────┬─────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 8: USER SEES RESULT                                    │
│  Web UI displays: Can: 0    Plastic: 1                      │
│  Ready for next item!                                        │
└──────────────────────────────────────────────────────────────┘
```

**Total time: ~200-300ms** ⚡

---

## 🔌 **HARDWARE SETUP (Raspberry Pi)**

### GPIO Wiring

```
Raspberry Pi GPIO Pins:
                    3V3  (1) (2)  5V
                  GPIO2  (3) (4)  5V
                  GPIO3  (5) (6)  GND ← Ground for motors
                  GPIO4  (7) (8)  GPIO14
                    GND  (9) (10) GPIO15
   CAN MOTOR → GPIO17 (11) (12) GPIO18
PLASTIC MOTOR → GPIO27 (13) (14) GND
                GPIO22 (15) (16) GPIO23 ← CAN LED
                   3V3 (17) (18) GPIO24 ← PLASTIC LED
                GPIO10 (19) (20) GND
```

**Connections:**

| Component | GPIO Pin | Physical Pin | Notes |
|-----------|----------|--------------|-------|
| Can Motor | GPIO 17 | Pin 11 | Runs 1.0 sec (45°) |
| Plastic Motor | GPIO 27 | Pin 13 | Runs 2.0 sec (90°) |
| Can LED | GPIO 23 | Pin 16 | Indicator |
| Plastic LED | GPIO 24 | Pin 18 | Indicator |
| Ground | GND | Pin 6, 9, 14 | Common ground |

**⚠️ Important:** Motors need external power supply! Don't power from Pi's 5V.

---

## 📡 **NETWORK REQUIREMENTS**

### Must Have:
- ✅ Both devices on **same WiFi network**
- ✅ Laptop IP address configured on Pi
- ✅ Port 5000 accessible

### Test Network:

**From Raspberry Pi:**
```bash
# Can you ping laptop?
ping 192.168.1.150

# Can you reach API?
curl http://192.168.1.150:5000/api/status

# Should return:
# {"status":"online","message":"Laptop server is ready",...}
```

---

## 🎮 **USAGE MODES**

### Mode 1: Web UI (Recommended)

```
1. Open browser on phone/laptop/tablet
   URL: http://YOUR_LAPTOP_IP:5000
   Example: http://192.168.1.150:5000

2. Click "START" button
3. Click "CAPTURE" button
4. Raspberry Pi captures → classifies → moves motor
5. Web UI updates counts automatically!
```

### Mode 2: Pi Script (Testing)

```bash
# Single classification
python pi_controller.py once

# Continuous (every 3 seconds)
python pi_controller.py continuous 3

# Test connection only
python pi_controller.py test
```

---

## ⚙️ **CONFIGURATION**

### Raspberry Pi: config.py

```python
# ⚠️ MUST CHANGE!
LAPTOP_IP = '192.168.1.150'  # Your laptop's IP

# GPIO Pins (change if wiring different)
MOTOR_CAN_PIN = 17
MOTOR_PLASTIC_PIN = 27

# Motor Timing (adjust for your motors)
MOTOR_TIME_CAN = 1.0       # Seconds for 45° rotation
MOTOR_TIME_PLASTIC = 2.0   # Seconds for 90° rotation

# Camera
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
```

---

## 🐛 **TROUBLESHOOTING**

### ❌ "Cannot connect to laptop"

**Check:**
```bash
# 1. Ping laptop
ping 192.168.1.150

# 2. Test API
curl http://192.168.1.150:5000/api/status

# 3. Check same WiFi
iwconfig  # On Pi
ipconfig  # On laptop
```

**Fix:**
1. ✅ Flask running on laptop?
2. ✅ Laptop IP correct in config.py?
3. ✅ Both on same WiFi?
4. ✅ Windows firewall blocking?

### ❌ "Camera not found"

```bash
# Check USB connection
lsusb | grep -i camera

# Check video devices
ls -l /dev/video*

# Test camera
python3 -c "import cv2; cam = cv2.VideoCapture(0); print(cam.isOpened())"
```

### ❌ "Motor not moving"

1. Check wiring (correct GPIO pins?)
2. Motors have external power?
3. Increase time in config.py
4. Test GPIO manually:
```python
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)
GPIO.output(17, GPIO.HIGH)  # Should turn on
```

---

## 📝 **WHAT TO GIT PUSH**

```bash
git add .
git commit -m "Complete split architecture with USB camera"
git push origin main
```

**Includes:**
- ✅ app.py (with API endpoints)
- ✅ raspberry-pi/ folder (all files)
- ✅ templates/index.html
- ✅ Documentation

**Excludes (.gitignore):**
- ❌ env/ (virtual environment)
- ❌ __pycache__/
- ❌ Picture/ (images)

---

## ✅ **PRE-DEMO CHECKLIST**

### Laptop:
- [ ] Flask running: `python app.py`
- [ ] Know your IP: `ipconfig`
- [ ] Web UI loads: `http://localhost:5000`

### Raspberry Pi:
- [ ] Files copied
- [ ] Dependencies installed
- [ ] Laptop IP in config.py
- [ ] USB camera plugged in
- [ ] Connection test passes
- [ ] Motors wired with external power

### Test:
- [ ] Run `python pi_controller.py once`
- [ ] Web UI updates
- [ ] Motor moves
- [ ] SUCCESS! 🎉

---

## 📊 **SUMMARY**

| Device | Role | What Runs | Size |
|--------|------|-----------|------|
| **Laptop** | Brain | Flask + TFLite AI + Web UI | ~500MB |
| **Raspberry Pi** | Hands & Eyes | Camera + Motors | ~50MB |

**Communication:**
- WiFi (same network)
- HTTP API (JSON)
- Base64 image encoding

**Latency:** ~200-300ms per classification ⚡

---

**🚀 Ready to sort trash! Let's go!**
