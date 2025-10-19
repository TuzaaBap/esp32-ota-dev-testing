# ESP32 OTA / Dev Testing 🔧  
**Version:** v1.0.0 (Stable)

Password-protected OTA Web IDE for **MicroPython on ESP32 / ESP32-S3** boards.

[Web Interface Screenshot] <img width="1440" height="848" alt="image" src="https://github.com/user-attachments/assets/861f54c1-3301-43fc-9d54-465c09ee4f9a" />


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

## 🧠 Setup Instructions

### 1️⃣ Flash MicroPython
Install the latest MicroPython firmware for your ESP32 or ESP32-S3 using [Thonny IDE](https://thonny.org/) or `esptool.py`.

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
