# boot.py — Wi-Fi + start OTA (dark UI + logs + web shell)

import network, time

# <<< your Wi-Fi >>>
SSID = "Your_WiFi_SSID"                  #Replace SSID and PASSWORD with your Wi-Fi credentials.
PASSWORD = "Your_WiFi_Password"   

def connect_wifi(timeout_s=12):
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if not sta.isconnected():
        sta.connect(SSID, PASS)
        t0 = time.ticks_ms()
        while (not sta.isconnected()) and time.ticks_diff(time.ticks_ms(), t0) < timeout_s*1000:
            time.sleep(0.2)
    if sta.isconnected():
        return ("STA", sta.ifconfig()[0])

    # Fallback AP so you can still reach the page if STA fails
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="ESP32-OTA", password="esp32otapass")
    return ("AP", ap.ifconfig()[0])

mode, ip = connect_wifi()
print("Wi-Fi:", mode, "IP:", ip)

# Optional tiny heartbeat
try:
    from machine import Pin
    led = Pin("LED", Pin.OUT)
    for _ in range(2):
        led.on();  time.sleep(0.1)
        led.off(); time.sleep(0.1)
except:
    pass

import ota
print("Loaded OTA version:", getattr(ota, "__version__", "unknown"))
ota.start(ip=ip, mode=mode)
