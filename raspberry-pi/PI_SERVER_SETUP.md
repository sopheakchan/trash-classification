# Raspberry Pi Server Setup Guide

## What is This?
This is a **lightweight Flask API** that runs on your Raspberry Pi. It handles:
- 📷 **USB Camera** (Logitech) - captures images
- 🔧 **Motor Control** - activates motors based on classification

**Laptop** handles all the heavy AI work!

---

## Architecture Flow

```
Web Browser
    ↓ (Click "PI CAMERA" button)
Laptop Flask (app.py)
    ↓ (HTTP request)
Raspberry Pi (pi_server.py)
    → Captures image from Logitech camera
    → Sends base64 image back to laptop
Laptop Flask
    → Runs AI classification
    → Sends prediction to Pi
Raspberry Pi
    → Activates correct motor (Can or Plastic)
    → Returns success
Web Browser
    ← Shows result & updates counts
```

---

## Setup Steps

### 1. Transfer Files to Raspberry Pi

**Option A: Using Git (Recommended)**
```bash
# On Raspberry Pi terminal
cd ~
git clone <your-repo-url>
cd trash-classification/raspberry-pi
```

**Option B: Copy Files Manually**
- Copy the entire `raspberry-pi/` folder to your Pi
- Use USB drive, network share, or SCP

### 2. Install Dependencies on Pi

```bash
cd ~/trash-classification/raspberry-pi
pip3 install -r requirements-server.txt
```

**What gets installed:**
- `opencv-python` - For USB camera
- `flask` - Web API server
- `flask-cors` - Allow laptop to connect
- `requests` - (Not used in server, but included for consistency)
- `RPi.GPIO` - Motor control
- `numpy` - Image processing

**Note:** NO TensorFlow needed on Pi! It's lightweight!

### 3. Hardware Setup

#### Camera:
- Plug Logitech USB camera into any USB port on Pi
- Camera will be auto-detected (tries indices 0, 1, 2)

#### Motors:
- **Can Motor:**
  - Connect to GPIO Pin 17
  - Runs for 1.0 second (45° rotation)
  
- **Plastic Motor:**
  - Connect to GPIO Pin 27
  - Runs for 2.0 seconds (90° rotation)

**Important:** Motors need external power supply! Don't power them directly from GPIO (only use GPIO for signal).

### 4. Find Your Raspberry Pi's IP Address

On Pi terminal:
```bash
hostname -I
```

Example output: `192.168.1.101`

**Write this down!** You'll need it for the web UI.

### 5. Start the Pi Server

```bash
cd ~/trash-classification/raspberry-pi
python3 pi_server.py
```

You should see:
```
🍓 Starting Raspberry Pi Flask Server...
📷 USB Camera (Logitech) will be auto-detected
🔧 Motors: Can=Pin17, Plastic=Pin27
⏱️  Timing: Can=1.0s, Plastic=2.0s

🌐 API Endpoints:
   GET  /api/status  - Health check
   GET  /api/capture - Capture image from camera
   POST /api/motor   - Activate motor
   GET  /api/test    - Test camera + GPIO

 * Running on http://0.0.0.0:5001
```

**Keep this running!** Don't close this terminal.

---

## On Your Laptop

### 1. Start Laptop Flask Server

```bash
cd C:\Users\chans\Documents\Sopheak\Rupp\IOT\trash-classification
env\Scripts\activate
python app.py
```

Should see:
```
🚀 Starting Trash Classification Flask App...
 * Running on http://0.0.0.0:5000
```

### 2. Open Web Browser

Go to: `http://localhost:5000`

### 3. Configure Pi IP in Web UI

In the web page, you'll see a text input labeled "Pi IP:"
- Enter your Pi's IP address (e.g., `192.168.1.101`)
- This is the IP you found in Step 4 above

### 4. Test the System

1. Click **START** - starts session
2. Click **🎆 PI CAMERA** - captures from Pi, classifies, activates motor!
3. Watch the counts update
4. Click **STOP** - ends session

**Alternative:** Click **LAPTOP CAMERA** to test with your laptop's camera (no motor, just AI)

---

## Testing & Troubleshooting

### Test Pi Server Directly

**From your laptop browser**, go to:
```
http://192.168.1.101:5001/api/status
```
(Replace `192.168.1.101` with your Pi's actual IP)

Should see:
```json
{
  "status": "online",
  "message": "Raspberry Pi server is ready",
  "camera_available": true,
  "gpio_initialized": false
}
```

### Test Camera

```
http://192.168.1.101:5001/api/test
```

Should see:
```json
{
  "status": "success",
  "message": "Camera and GPIO ready",
  "camera_shape": [480, 640, 3]
}
```

### Common Issues

**"Cannot connect to Raspberry Pi"**
- ✅ Check both devices on same WiFi
- ✅ Check Pi IP is correct in web UI
- ✅ Check `pi_server.py` is running on Pi
- ✅ Try `ping 192.168.1.101` from laptop

**"Camera not available"**
- ✅ Check USB camera is plugged in
- ✅ Run `ls /dev/video*` on Pi - should see `/dev/video0`
- ✅ Check camera works: `python3 -c "import cv2; print(cv2.VideoCapture(0).isOpened())"`

**"Motor error"**
- ✅ Check GPIO pins are correct (17 and 27)
- ✅ Check motors have external power
- ✅ Run `sudo python3 pi_server.py` if permission error

**Firewall blocking connection**
- On Pi: `sudo ufw allow 5001`
- On laptop: Windows Firewall → Allow port 5000

---

## API Endpoints Reference

### GET /api/status
Health check - verify server is running

**Response:**
```json
{
  "status": "online",
  "message": "Raspberry Pi server is ready"
}
```

### GET /api/capture
Capture image from USB camera, return as base64

**Response:**
```json
{
  "status": "success",
  "image": "base64_encoded_jpeg_data..."
}
```

### POST /api/motor
Activate motor based on classification

**Request:**
```json
{
  "prediction": "can"  // or "plastic"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Can motor activated for 1.0s (45°)",
  "prediction": "can"
}
```

### GET /api/test
Test camera and GPIO initialization

**Response:**
```json
{
  "status": "success",
  "message": "Camera and GPIO ready",
  "camera_shape": [480, 640, 3],
  "gpio_initialized": true
}
```

---

## Configuration

Edit these values in `pi_server.py` if needed:

```python
MOTOR_CAN_PIN = 17          # GPIO pin for Can motor
MOTOR_PLASTIC_PIN = 27      # GPIO pin for Plastic motor
MOTOR_TIME_CAN = 1.0        # Can motor duration (seconds)
MOTOR_TIME_PLASTIC = 2.0    # Plastic motor duration (seconds)
```

Port: Default is **5001** (line 245)

---

## Running on Boot (Optional)

To auto-start Pi server when Pi boots:

1. Create systemd service:
```bash
sudo nano /etc/systemd/system/pi-trash-classifier.service
```

2. Add this content:
```ini
[Unit]
Description=Trash Classifier Pi Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/trash-classification/raspberry-pi
ExecStart=/usr/bin/python3 /home/pi/trash-classification/raspberry-pi/pi_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

3. Enable and start:
```bash
sudo systemctl enable pi-trash-classifier
sudo systemctl start pi-trash-classifier
```

4. Check status:
```bash
sudo systemctl status pi-trash-classifier
```

---

## Next Steps

✅ Pi server running
✅ Laptop Flask running  
✅ Web UI configured with Pi IP
✅ Camera and motors tested

**Now you're ready to classify trash with the vending machine!**

Click "PI CAMERA" in the web UI and watch the magic happen! 🎉
