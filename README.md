# ESP32 OTA / Dev Testing 🔧  


Password-protected OTA Web IDE for **MicroPython on ESP32 / ESP32-S3** boards.

[Web Interface Screenshot] <img width="1141" height="1340" alt="image" src="https://github.com/user-attachments/assets/f9b9758d-8794-4636-b5a4-3eb3d3a36eb6" />


---

## 🌐 Overview
This project allows you to **write, upload, and execute MicroPython code** directly from your browser — no serial connection needed.  
It includes:
- A minimal **web IDE** served directly from the ESP32-S3  
- **Username/password protection** for secure local access  
- File management (save, delete, run)  
- Real-time log output via web interface  
- Built-in hard reset  

---

## ⚙️ Features
 Save & Run code directly from browser  
 Run existing `.py` files stored on device  
 Delete unwanted files  
 Real-time serial log output on webpage  
 Basic authentication (default: `admin` / `admin`)  
 Works on ESP32 and XIAO ESP32-S3 boards 
 Shell which also you control more and get test script without saving on ROM on the device

---

### 1️⃣ Flash MicroPython Firmware

Before uploading any Python files (`boot.py`, `ota.py`, etc.), make sure your ESP32 or ESP32-S3 board is running **MicroPython firmware**.

You can flash it easily using **either Thonny IDE (recommended for beginners)** or **esptool.py (for command-line users)**.

---

#### 🧩 Option A — Flash Using Thonny IDE (Beginner Friendly)

1. **Download and Install Thonny**
   - [🔗 Thonny IDE Official Site](https://thonny.org)
   - Works on Windows, macOS, and Linux.

2. **Connect the ESP32 Board**
   - Plug your ESP32/ESP32-S3 into your computer using a USB cable.  
   - Make sure the cable supports *data transfer* (not just charging).

3. **Select Interpreter**
   - In Thonny, go to:  
     `Tools → Options → Interpreter`
   - Choose:  
     **Interpreter:** “MicroPython (ESP32)”  
     **Port:** the serial port where your board is connected.

4. **Install/Update MicroPython Firmware**
   - Click **“Install or update MicroPython”** in the same menu.
   - Thonny will automatically detect your board and list available firmware versions.
   - Select the **latest stable firmware** for your board (ESP32 or ESP32-S3).
   - Click **“Install”** and wait until you see *“Done!”*.
   - RePlug your ESP32/ESP32-S3 into your computer using a USB cable.
   - go to:  
     `Tools → Options → Interpreter`
    Choose:   
     **Port:** the serial port where your board is connected.
   - This to make sure that after installing the firmware , your machine communicate with esp 32.

5. **Verify**
   - After flashing, open Thonny’s **Shell** (bottom panel).
   - You should see something like:
     ```
     MicroPython v1.xx on 2025-xx-xx; ESP32 module with ESP32S3
     >>> 
     ```
   - You can now type:
     ```python
     import os
     os.listdir()
     ```
     to confirm your board is ready.

---
#### ⚙️ Option B — Flash Using `esptool.py` (Advanced CLI Method)

If you prefer command line or Thonny doesn’t detect the board:

1. **Install esptool**
   ```bash
   pip install esptool
2.	Download the Correct Firmware
	-	Go to MicroPython Downloads￼
	-	Download the .bin file for your specific ESP32/ESP32-S3 variant.
3.	Erase Existing Flash
    -    Replace /dev/ttyUSB0 with your board’s port:
    ```bash
    esptool.py --chip esp32 erase_flash
4.	Flash MicroPython
    ```bash
    esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 firmware.bin

5.	Verify Flash

   	-	Reconnect the board, open any serial terminal (Thonny, minicom, PuTTY).
	-	You should see the same MicroPython boot message as shown above.
---

### 2️⃣ Upload Required Files
Upload both of these files to your ESP device:
boot.py &
ota.py

You can use **Thonny**, **ampy**, or **WebREPL** to transfer these files.

---

### 3️⃣ Configure Wi-Fi  
Edit the following section in your `boot.py` file before uploading:  
```python
SSID = "Your_WiFi_SSID"
PASSWORD = "Your_WiFi_Password"
```

### 💡 Replace the SSID and PASSWORD with your local Wi-Fi credentials.
Once uploaded.

Your Thonny console will show something like:
Wi-Fi: STA IP: 192.168.1.14
HTTP server on 192.168.1.14 port 80

Use this IP address in your browser to access the Web IDE.

---

### 4️⃣ Change Login Credentials

Open ota.py in Thonny and locate:
```python
USER = "admin"
PASSWORD = "admin"
```

Change both fields to your desired username and password, then re-upload ota.py.
This secures your OTA Web IDE against unauthorized access.

---

### 5️⃣ Getting IP from Thonny IDE

After saving both files and restarting the ESP32:
	1.	Open Thonny IDE.
	2.	Connect to your ESP32 via MicroPython (USB).
	3.	Watch the Shell/console output — it will display your board’s assigned IP address.
	4.	Copy that IP and open it in Chrome/Brave/Firefox/anyotherbrower:
     http://<your-device-ip>

---

### 🧑‍💻 Using the Web Interface
	1.	Connect your ESP32 to the same Wi-Fi network.
	2.	Open the IP shown in Thonny (http://192.168.x.x).
	3.	Enter your login credentials.
	4.	Write or paste your MicroPython script.
	5.	Click Save & Run to execute immediately.
	6.	Watch the live logs on the same webpage.
	7.  If you update the script values just hard rest to ensure safe running.
  
---

###  License

### Apache License 2.0 TuzaaBap
#### Free for personal and educational use. Attribution appreciated.
---
