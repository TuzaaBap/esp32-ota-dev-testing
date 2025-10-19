# ESP32-S3 MicroPython — Accurate IST Web Clock (UTC math in browser)
# - NTP: time.google.com
# - LED: PWM "breathing" when Wi-Fi OK; fast blink when Wi-Fi down
# - Web: http://<board-ip>:8080/ shows correct IST regardless of client timezone

import network, time, ntptime, socket, sys, gc, math
from machine import Pin, PWM, WDT

# ==== Wi-Fi ====

SSID = "Your_WiFi_SSID"                  #Replace SSID and PASSWORD with your Wi-Fi credentials.
PASSWORD = "Your_WiFi_Password"

# ==== Time / server ====
IST_OFFSET_S = 5*3600 + 30*60
UNIX_EPOCH_OFFSET_S = 946_684_800   # MP on ESP32 uses 2000-01-01 epoch
HTTP_PORT = 8080                     # <- moved to avoid conflict with OTA UI (port 80)
NTP_HOST = "time.google.com"
NTP_RESYNC_MS = 3600_000             # 1h

# ==== LED ====
LED_PIN = 21
BREATH_PERIOD_MS = 3000
FAST_BLINK_MS = 120
LED_MAX_DUTY = 52000
pwm = PWM(Pin(LED_PIN), freq=1000)   # ctor without duty_u16 (better cross-build compat)
pwm.duty_u16(0)

# ==== Watchdog ====
wdt = WDT(timeout=4000)

# ==== HTML (uses UTC getters + IST offset; no double-offset) ====
HTML = b"""\
HTTP/1.1 200 OK\r
Content-Type: text/html; charset=utf-8\r
Cache-Control: no-store\r
Connection: close\r
\r
<!doctype html><html lang="en"><meta charset="utf-8">
<title>ESP32-S3 IST Clock</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#0b0f1a;color:#e6ecf5;margin:0;padding:24px}
.card{max-width:560px;margin:auto;background:#131a2a;border-radius:16px;padding:24px;box-shadow:0 10px 30px rgba(0,0,0,.35)}
h1{margin:0 0 8px;font-size:20px;font-weight:600;color:#9fb6ff}
.badge{display:inline-block;background:#2a3553;padding:2px 8px;border-radius:999px;margin-left:6px;font-size:12px}
#clock{font-size:48px;line-height:1.1;margin:6px 0 0}
#date{opacity:.85;margin-top:6px}
footer{opacity:.6;font-size:12px;margin-top:16px}
code{background:#0b1222;padding:2px 6px;border-radius:6px}
</style>
<div class="card">
  <h1>Indian Standard Time (IST) <span class="badge" id="wifi">Wi-Fi?</span></h1>
  <div id="clock">--:--:--</div>
  <div id="date">--/--/----</div>
  <footer>Source: <code>time.google.com</code> via ESP32-S3</footer>
</div>
<script>
const IST_MS = (5*3600 + 30*60)*1000; // +5:30 in ms
let delta = 0; // (ESP unix ms) - Date.now()

const pad=n=>n.toString().padStart(2,'0');
function draw(){
  // Use UTC fields so adding IST_MS doesn't get shifted again by local timezone
  const d = new Date(Date.now() + delta + IST_MS);
  const h=pad(d.getUTCHours()), m=pad(d.getUTCMinutes()), s=pad(d.getUTCSeconds());
  const y=d.getUTCFullYear(), mo=pad(d.getUTCMonth()+1), da=pad(d.getUTCDate());
  clock.textContent = `${h}:${m}:${s}`;
  date.textContent  = `${da}/${mo}/${y}`; // DD/MM/YYYY
}
async function start(){
  try{
    const r = await fetch('/epoch'); // {epoch_ms: <unix_ms_utc_from_board>}
    const j = await r.json();
    delta = j.epoch_ms - Date.now();
    wifi.textContent = "Wi-Fi: OK";
  }catch(e){
    delta = 0;
    wifi.textContent = "Wi-Fi: OFF";
  }
  draw(); setInterval(draw, 1000);
}
start();
</script></html>
"""

# ==== helpers ====
sta = network.WLAN(network.STA_IF)
def wifi_connected():
    try:
        return sta.isconnected()
    except:
        return False

def wifi_connect(timeout_ms=15000):
    if not sta.active():
        sta.active(True)
    if not sta.isconnected():
        sta.connect(SSID, PASS)
        t0 = time.ticks_ms()
        while (not sta.isconnected()) and time.ticks_diff(time.ticks_ms(), t0) < timeout_ms:
            time.sleep_ms(100); wdt.feed()
    return sta.isconnected()

def ntp_sync():
    try:
        ntptime.host = NTP_HOST
        ntptime.settime()  # sets RTC to UTC (2000-epoch)
        return True
    except Exception:
        return False

def unix_epoch_ms_now():
    # Convert MP 2000-epoch seconds to Unix ms
    return int((time.time() + UNIX_EPOCH_OFFSET_S) * 1000)

_last_toggle = 0
def led_update(now_ms, wifi_ok):
    global _last_toggle
    if wifi_ok:
        # cosine breathing 0..1
        phase = (now_ms % BREATH_PERIOD_MS) / BREATH_PERIOD_MS
        val = 0.5 * (1.0 - math.cos(2*math.pi*phase))
        pwm.duty_u16(int(val * LED_MAX_DUTY))
    else:
        if time.ticks_diff(now_ms, _last_toggle) >= FAST_BLINK_MS:
            _last_toggle = now_ms
            pwm.duty_u16(0 if pwm.duty_u16() > 0 else LED_MAX_DUTY)

def http_json_epoch(epoch_ms: int) -> bytes:
    body = b'{"epoch_ms":' + str(epoch_ms).encode() + b'}'
    hdr  = (b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Cache-Control: no-store\r\n"
            b"Connection: close\r\n\r\n")
    return hdr + body

# ==== HTTP server ====
def serve(ip="0.0.0.0", port=HTTP_PORT):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((ip, port))
    s.listen(2)
    s.settimeout(0.2)
    try:
        print(f"[HTTP] http://{sta.ifconfig()[0]}:{port}/")
    except:
        print(f"[HTTP] listening on :{port}")

    last_ntp = time.ticks_ms()
    last_reconn_try = time.ticks_ms()

    while True:
        now = time.ticks_ms()
        ok = wifi_connected()

        led_update(now, ok)
        wdt.feed()

        if not ok and time.ticks_diff(now, last_reconn_try) >= 3000:
            wifi_connect(3000)
            last_reconn_try = now

        if ok and time.ticks_diff(now, last_ntp) >= NTP_RESYNC_MS:
            ntp_sync()
            last_ntp = now

        try:
            conn, addr = s.accept()
        except OSError:
            time.sleep_ms(10)
            continue

        try:
            conn.settimeout(1)
            req = conn.recv(512)
            path = b"/"
            if req:
                try:
                    first = req.split(b"\r\n",1)[0]
                    parts = first.split()
                    if len(parts) >= 2:
                        path = parts[1]
                except Exception:
                    pass

            if path == b"/" or path.startswith(b"/index"):
                conn.sendall(HTML)
            elif path.startswith(b"/epoch"):
                conn.sendall(http_json_epoch(unix_epoch_ms_now()))
            else:
                conn.sendall(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\nNot found")
        except Exception:
            pass
        finally:
            try: conn.close()
            except: pass

        gc.collect()

# ==== boot (for standalone run via OTA runner) ====
print("\n[BOOT] IST Web Clock (NTP via time.google.com) + LED breathing/fast-blink")
if wifi_connect():
    print("[Wi-Fi] OK:", sta.ifconfig())
    print("[NTP]", "OK" if ntp_sync() else "FAIL")
else:
    print("[Wi-Fi] FAIL — will serve and auto-reconnect")

try:
    serve()
except KeyboardInterrupt:
    print("\n[STOP] user")
except Exception as e:
    sys.print_exception(e)
    time.sleep(1)
    import machine
    machine.reset()
